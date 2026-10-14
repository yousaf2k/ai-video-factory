"""
GeminiWeb Video Subprocess Helper — standalone Playwright script for video generation.

This script is invoked as a subprocess by generate_video_geminiweb().
Running Playwright in a fresh, isolated Python process avoids all asyncio
event-loop conflicts with FastAPI/Uvicorn on Windows.

Usage:
    python -m core.geminiweb_video_subprocess <image_path> <motion_prompt> <output_path>

Exit code 0 and prints the output path on success, exit code 1 on failure.
"""
import sys
import os
import time
import base64
from pathlib import Path
from typing import Optional

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
from core.logger_config import get_logger

logger = get_logger(__name__)


def _create_browser_context(playwright_instance, profile_dir=None):
    """Create a persistent browser context with the configured browser."""
    chrome_profile = profile_dir or getattr(config, 'GEMINIWEB_CHROME_PROFILE', None)
    os.makedirs(chrome_profile, exist_ok=True)
    
    browser_type_name = getattr(config, 'PLAYWRIGHT_BROWSER', 'chromium').lower()
    channel = getattr(config, 'PLAYWRIGHT_CHANNEL', 'chrome')
    
    # Map browser type name to playwright browser type object
    if browser_type_name == "firefox":
        browser_type = playwright_instance.firefox
        channel = None # Firefox doesn't use channels in Playwright
    elif browser_type_name == "webkit":
        browser_type = playwright_instance.webkit
        channel = None # Webkit doesn't use channels in Playwright
    else:
        browser_type = playwright_instance.chromium
        # Only allow recognized channels for chromium to avoid "browserType.launch: channel 'xxx' is not supported"
        valid_chromium_channels = ["chrome", "chrome-beta", "chrome-dev", "chrome-canary", "msedge", "msedge-beta", "msedge-dev", "msedge-canary"]
        if channel not in valid_chromium_channels:
            channel = None

    logger.info(f"Using browser: {browser_type_name}, channel: {channel}, profile: {chrome_profile}")

    try:
        if browser_type_name == "chromium":
            launch_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-session-crashed-bubble',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-features=OptimizationGuideModelExecution,OptimizationGuideOnDeviceModel',
            ]
        else:
            launch_args = []
            
        context = browser_type.launch_persistent_context(
            user_data_dir=chrome_profile,
            headless=False,
            channel=channel,
            args=launch_args,
            viewport={'width': 1280, 'height': 900},
            ignore_default_args=['--enable-automation'],
            accept_downloads=True,
        )
        return context
    except Exception as e:
        logger.error(f"Failed to launch browser {browser_type_name}: {e}")
        raise


def _get_chat_registry_path() -> str:
    """Path of the project-title -> chat-URL registry (survives runs)."""
    return os.path.join(getattr(config, 'OUTPUT_DIR', 'output'), 'gemini_chat_registry.json')


# ── Per-project chat-creation lock ──────────────────────────────────────────
# On the FIRST run for a project the chat URL is only registered after
# generation finishes, so two parallel workers would each create their own
# chat (duplicates). The lock serializes chat creation per project: the first
# worker creates + registers, the others wait (polling the registry) and then
# join the same chat. Different projects use different lock files and never
# block each other. The lock is held from acquisition until registration (the
# whole generation), and is stolen if stale (crashed worker).
_HELD_CHAT_LOCK: Optional[str] = None
_CHAT_LOCK_DEPTH = 0
_CHAT_LOCK_STALE_SECONDS = 900  # steal after 15 min (covers video generation)


def _chat_lock_path(project_title: str) -> str:
    safe = ''.join(c if c.isalnum() or c in '._-' else '_' for c in project_title)[:80]
    return os.path.join(getattr(config, 'OUTPUT_DIR', 'output'), f'chat_lock_{safe}.lock')


def _lock_holder_dead(lock_path: str) -> bool:
    """True if the lock file's holder PID is no longer running.

    Windows-safe: os.kill(pid, 0) would *terminate* processes on Windows, so
    use OpenProcess + WaitForSingleObject(0) instead. Unreadable files fall
    back to the age-based staleness check (False)."""
    try:
        with open(lock_path, encoding='utf-8') as f:
            pid = int(f.read().split()[0])
    except Exception:
        return False
    if pid <= 0:
        return True
    if os.name != 'nt':
        try:
            os.kill(pid, 0)
            return False
        except OSError:
            return True
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x00100000
        h = k32.OpenProcess(SYNCHRONIZE, False, pid)
        if not h:
            # ERROR_ACCESS_DENIED means the process exists but is protected.
            return k32.GetLastError() != 5
        res = k32.WaitForSingleObject(h, 0)  # 0 = exited, 258 = still running
        k32.CloseHandle(h)
        return res != 0x102
    except Exception:
        return False


def _acquire_chat_lock(project_title: str) -> str:
    """Acquire the per-project generation lock (waits while another worker's
    generation is in flight; re-entrant for the same process).

    2026-10: this lock covers WHOLE generations. Overlapping generations in
    one conversation trigger Gemini's image-swap bug (one response's image is
    dropped and replaced by the other exchange's picture), so a waiter must
    not proceed while the lock file exists - even if the chat is already in
    the registry (the old 'registered' short-circuit did exactly that and
    defeated serialization for every existing project).

    Returns 'acquired' (lock held; release via _release_chat_lock) or
    'timeout' (caller proceeds best-effort).
    """
    global _HELD_CHAT_LOCK, _CHAT_LOCK_DEPTH
    timeout = int(getattr(config, 'GEMINIWEB_CHAT_LOCK_TIMEOUT', 600))
    deadline = time.time() + timeout
    lock_path = _chat_lock_path(project_title)

    while True:
        if _HELD_CHAT_LOCK == project_title:
            _CHAT_LOCK_DEPTH += 1
            return 'acquired'
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()} {time.time()}".encode())
            os.close(fd)
            _HELD_CHAT_LOCK = project_title
            _CHAT_LOCK_DEPTH = 0
            logger.info(f"Acquired chat generation lock for '{project_title}'")
            return 'acquired'
        except FileExistsError:
            # Steal a stale lock: the holder process is dead (its finally
            # never ran), or the file is older than the staleness backstop.
            try:
                if _lock_holder_dead(lock_path) or (
                        time.time() - os.path.getmtime(lock_path) > _CHAT_LOCK_STALE_SECONDS):
                    logger.warning(f"Stealing stale chat lock (dead holder): {lock_path}")
                    os.remove(lock_path)
                    continue
            except OSError:
                pass
        except OSError as e:
            logger.debug(f"Chat lock open failed: {e}")
            return 'timeout'
        if time.time() >= deadline:
            logger.warning(f"Chat lock wait timed out for '{project_title}' after {timeout}s")
            return 'timeout'
        time.sleep(3)


def _release_chat_lock(project_title: str) -> None:
    """Release the per-project generation lock (re-entrancy aware)."""
    global _HELD_CHAT_LOCK, _CHAT_LOCK_DEPTH
    if _HELD_CHAT_LOCK != project_title:
        return
    if _CHAT_LOCK_DEPTH > 0:
        # Inner scope (e.g. _ensure_project_chat) released its share; the
        # whole-generation lock stays held by the outer run().
        _CHAT_LOCK_DEPTH -= 1
        return
    try:
        os.remove(_chat_lock_path(project_title))
    except OSError:
        pass
    _HELD_CHAT_LOCK = None
    logger.info(f"Released chat generation lock for '{project_title}'")


def _registry_get_chat_url(project_title: str):
    """Return the stored chat URL for project_title, if any."""
    try:
        import json
        path = _get_chat_registry_path()
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            url = data.get(project_title)
            if url and '/app/' in url:
                return url
    except Exception as e:
        logger.debug(f"Chat registry read failed: {e}")
    return None


def _registry_set_chat_url(project_title: str, chat_url: str) -> None:
    """Store chat_url under project_title (locked, atomic read-modify-write)."""
    try:
        from core import json_atomic
        path = _get_chat_registry_path()
        if chat_url and '/app/' in chat_url:
            def _set(data):
                if not isinstance(data, dict):
                    data = {}
                data[project_title] = chat_url.split('?')[0]
                return data

            os.makedirs(os.path.dirname(path), exist_ok=True)
            json_atomic.update_json(path, _set, default={})
            logger.info(f"Registered project chat: '{project_title}' -> {chat_url}")
    except Exception as e:
        logger.debug(f"Chat registry write failed: {e}")


def _open_project_chat_by_url(page, chat_url: str) -> bool:
    """Navigate to a known chat URL and verify the conversation actually loaded."""
    try:
        page.goto(chat_url, wait_until='domcontentloaded', timeout=30000)
        time.sleep(5)
        # The conversation-actions menu only exists inside a real conversation
        # (a deleted chat redirects to /app without it).
        if page.query_selector('button[aria-label="Open menu for conversation actions."], message-content'):
            return True
        logger.debug(f"Chat URL did not load a conversation: {chat_url}")
    except Exception as e:
        logger.debug(f"Failed to open chat URL {chat_url}: {e}")
    return False


def _ensure_project_chat(page, project_title: str) -> bool:
    """
    Ensure we are in a chat named after the project_title.
    1. Open the chat URL saved in the registry (exact, no UI searching).
    2. Fall back to searching the sidebar Recents.
    3. Otherwise stay in the new chat and return False — run() renames the
       chat to project_title after generation and registers its URL.
    """
    if not project_title:
        return False

    logger.info(f"Ensuring Gemini chat for project: '{project_title}'")
    try:
        # 1. Registry: direct navigation, immune to sidebar render timing.
        saved_url = _registry_get_chat_url(project_title)
        if saved_url and _open_project_chat_by_url(page, saved_url):
            logger.info(f"Opened registered project chat for '{project_title}'")
            return True
        if saved_url:
            logger.info(f"Registered chat for '{project_title}' is gone; falling back to sidebar search")

        # 2. Sidebar Recents.
        sidebar_selectors = [
            f'a[aria-label*="{project_title}"]',
            f'div[role="button"]:has-text("{project_title}")',
            f'a:has-text("{project_title}")',
        ]
        try:
            page.wait_for_selector('a[aria-label][href*="/app/"]', timeout=8000, state='visible')
        except Exception:
            pass

        for sel in sidebar_selectors:
            try:
                chat_links = page.query_selector_all(sel)
                for chat_link in reversed(chat_links):
                    try:
                        if not chat_link.is_visible():
                            continue
                        logger.info(f"Found existing chat: '{project_title}'. Clicking...")
                        chat_link.click()
                        time.sleep(5)
                        _registry_set_chat_url(project_title, page.url)
                        return True
                    except Exception:
                        continue
            except Exception:
                continue

        logger.info(f"No existing chat found for '{project_title}'. Serializing chat creation...")
        # 3. First run for this project: serialize so parallel workers don't
        # each create their own chat. While waiting we poll the registry; once
        # the first worker registers, we join its chat instead.
        lock_status = _acquire_chat_lock(project_title)
        try:
            if lock_status == 'registered':
                saved_url = _registry_get_chat_url(project_title)
                if saved_url and _open_project_chat_by_url(page, saved_url):
                    logger.info(f"Joined project chat registered by a parallel worker for '{project_title}'")
                    return True
            if project_title and _registry_get_chat_url(project_title) and lock_status == 'acquired':
                # Double-check: a worker may have registered between lock
                # acquisition and this check.
                saved_url = _registry_get_chat_url(project_title)
                if saved_url and _open_project_chat_by_url(page, saved_url):
                    return True

            logger.info(f"Using current/new chat; it will be renamed after generation.")
            new_chat_btn = page.query_selector('a[href="/app"], button:has-text("New chat")')
            if new_chat_btn and not page.url.endswith('/app'):
                new_chat_btn.click()
                time.sleep(2)
            return False
        finally:
            # Pair EVERY path's inner acquire with a release (depth-counted):
            # the whole-generation lock stays held by run()'s outer acquire.
            if lock_status == 'acquired':
                _release_chat_lock(project_title)
    except Exception as e:
        logger.warning(f"Error while managing project chat: {e}")
        return False


def _rename_current_chat(page, project_title: str) -> bool:
    """
    Rename the current chat to project_title so future runs can find it in the
    sidebar. New-UI flow: conversation actions menu -> 'Rename' -> dialog input
    -> 'Rename' button.
    """
    if not project_title:
        return False

    try:
        menu_btn = page.query_selector('button[aria-label="Open menu for conversation actions."]')
        if not menu_btn or not menu_btn.is_visible():
            logger.debug("Conversation actions menu not found; cannot rename chat")
            return False
        menu_btn.click()
        time.sleep(1.5)

        rename_item = None
        for it in page.query_selector_all('gem-menu-item'):
            try:
                if (it.text_content() or '').strip().lower() == 'rename' and it.is_visible():
                    rename_item = it
                    break
            except Exception:
                continue
        if not rename_item:
            logger.debug("'Rename' menu item not found")
            page.keyboard.press('Escape')
            return False
        rename_item.click()
        time.sleep(2)

        field = page.wait_for_selector(
            'mat-dialog-container input, mat-dialog-container textarea, '
            'div[role="dialog"] input, div[role="dialog"] textarea',
            timeout=8000)
        field.click()
        page.keyboard.press('Control+A')
        page.keyboard.press('Delete')
        field.type(project_title, delay=5)
        time.sleep(0.5)

        save_btn = None
        for bt in page.query_selector_all('mat-dialog-container button, div[role="dialog"] button'):
            text = (bt.text_content() or '').strip().lower()
            if text in ('save', 'rename', 'ok', 'done') and bt.is_visible():
                save_btn = bt
                break
        if not save_btn:
            logger.debug("Rename save button not found")
            page.keyboard.press('Escape')
            return False
        save_btn.click()
        time.sleep(3)
        logger.info(f"Chat renamed to '{project_title}' for future reuse")
        return True

    except Exception as e:
        logger.debug(f"Rename chat failed: {e}")
        try:
            page.keyboard.press('Escape')
        except Exception:
            pass
        return False


def _set_gemini_mode(page, mode: str):
    """
    Select the Gemini Web model and thinking level via the UI.

    Values mirror the Gemini Web picker exactly:
        Models:   '3.5 Flash-Lite' (Fastest answers), '3.8 Flash' (All-around
                  help), '3.1 Pro' (Advanced reasoning)
        Thinking: 'Low' (Quick and efficient — extended thinking off; the
                  picker label then carries no effort suffix), 'Medium'
                  (Balanced depth), 'High' (Extra thorough)

    `mode` accepts, in order of precedence:
      1. A "<model>|<thinking>" pair with the exact names above, e.g.
         "3.8 Flash|High" (what the Web UI sends).
      2. A bare model or thinking name from the lists above — only that
         dimension is changed.
      3. A legacy six-mode name (Fast / Medium / Pro / Fast Thinking /
         Medium Thinking / Pro Thinking / thinking) for old stored configs:
         Fast->Flash-Lite Low, Medium->Flash Low, Pro->Pro Low, and the
         * Thinking variants -> High.

    Current state is parsed from the picker button's aria-label
    ("Open mode picker, currently <model>[ Low|Medium|High]"). Items are
    matched by text because their data-test-id values are unstable hashes.
    Every item click applies and closes the menu, and each dimension survives
    a change of the other, so a model-only or effort-only change needs a
    single opening; only a change of both dimensions reopens the menu. When
    the picker already shows the requested combination it is not opened at
    all.
    """
    if not mode:
        mode = f"{getattr(config, 'GEMINIWEB_MODEL', '3.8 Flash')}|{getattr(config, 'GEMINIWEB_THINKING', 'Low')}"

    mode_key = str(mode).lower().strip()
    legacy_map = {
        'fast': ('flash-lite', 'low'),
        'medium': ('flash', 'low'),
        'pro': ('pro', 'low'),
        'fast thinking': ('flash-lite', 'high'),
        'medium thinking': ('flash', 'high'),
        'pro thinking': ('pro', 'high'),
        # legacy names
        'thinking': ('flash', 'high'),
    }
    model_aliases = {
        '3.5 flash-lite': 'flash-lite',
        '3.5 flash lite': 'flash-lite',
        'flash-lite': 'flash-lite',
        '3.8 flash': 'flash',
        'flash': 'flash',
        '3.1 pro': 'pro',
    }
    thinking_aliases = {'low': 'low', 'medium': 'medium', 'high': 'high'}

    desired_model = None
    desired_effort = None
    if mode_key in legacy_map:
        desired_model, desired_effort = legacy_map[mode_key]
    elif '|' in mode_key:
        model_part, _, thinking_part = mode_key.partition('|')
        desired_model = model_aliases.get(model_part.strip())
        desired_effort = thinking_aliases.get(thinking_part.strip())
        if desired_model is None and desired_effort is None:
            logger.warning(f"Unknown Gemini model/thinking '{mode}', skipping selection.")
            return
    elif mode_key in model_aliases:
        desired_model = model_aliases[mode_key]
    elif mode_key in thinking_aliases:
        desired_effort = thinking_aliases[mode_key]
    else:
        logger.warning(f"Unknown Gemini mode '{mode}', skipping selection.")
        return
    # Menu item texts start with these labels (e.g. "3.5 Flash-Lite Fastest answers",
    # "High Extra thorough")
    model_menu_labels = {
        'flash-lite': '3.5 flash-lite',
        'flash': '3.8 flash',
        'pro': '3.1 pro',
    }

    picker_sel = 'button[data-test-id="bard-mode-menu-button"]'

    def _read_state():
        try:
            btn = page.query_selector(picker_sel)
            if not btn:
                return None
            aria = (btn.get_attribute('aria-label') or '').lower()
            if 'currently' not in aria:
                return None
            current = aria.split('currently', 1)[1].strip()
            # "Flash High" -> effort 'high'; plain "Flash" means thinking off (Low)
            effort = 'low'
            for lvl in ('medium', 'high', 'low'):
                if current.endswith(lvl):
                    effort = lvl
                    current = current[:-len(lvl)].strip()
                    break
            return {'model': current, 'effort': effort}
        except Exception:
            return None

    def _open_menu():
        page.wait_for_selector(picker_sel, timeout=10000).click()
        time.sleep(1.5)

    def _click_menu_item(prefix):
        for it in page.query_selector_all('gem-menu-item'):
            try:
                text = (it.text_content() or '').strip().lower()
                if text.startswith(prefix) and it.is_visible():
                    it.click()
                    time.sleep(2)  # item click applies and closes the menu
                    return True
            except Exception:
                continue
        return False

    def _matches(state):
        # Only enforce the dimensions that were actually requested.
        if not state:
            return False
        if desired_model is not None and state['model'] != desired_model:
            return False
        if desired_effort is not None and state['effort'] != desired_effort:
            return False
        return True

    logger.info(f"Setting Gemini mode to: {mode}")
    try:
        state = _read_state()
        if _matches(state):
            logger.info(
                f"Gemini is already in the requested mode "
                f"(model={state['model']}, thinking={state['effort']}); skipping picker."
            )
            return

        if desired_model is not None and (state is None or state['model'] != desired_model):
            _open_menu()
            if not _click_menu_item(model_menu_labels[desired_model]):
                logger.warning(f"Could not find model menu item for '{desired_model}'")
                page.keyboard.press('Escape')
                return
            state = _read_state()

        if desired_effort is not None and not _matches(state):
            _open_menu()
            if not _click_menu_item(desired_effort):
                logger.warning(f"Could not find thinking menu item for '{desired_effort}'")
                page.keyboard.press('Escape')
                return
            state = _read_state()

        if _matches(state):
            logger.info(f"Successfully set Gemini mode: {mode} (model={desired_model}, thinking={desired_effort}).")
        else:
            logger.warning(f"Gemini mode selection did not verify: wanted {mode}, got {state}")
    except Exception as e:
        logger.error(f"Error setting Gemini mode: {e}")


def _inject_text_into_input(page, input_element, text: str) -> bool:
    """Inject text directly into the Gemini chat input."""
    input_element.click()
    time.sleep(0.3)

    try:
        input_element.fill(text)
        time.sleep(0.5)
        actual = input_element.inner_text().strip()
        if len(actual) >= max(10, len(text) // 2):
            logger.info("Prompt injected via fill()")
            return True
    except Exception as e:
        logger.debug(f"fill() failed: {e}")

    try:
        escaped = text.replace('`', '\\`').replace('$', '\\$')
        page.evaluate(f"""
            (el) => {{
                el.focus();
                el.innerText = `{escaped}`;
                const range = document.createRange();
                const sel   = window.getSelection();
                range.selectNodeContents(el);
                range.collapse(false);
                sel.removeAllRanges();
                sel.addRange(range);
                ['input', 'keydown', 'keyup', 'change'].forEach(name => {{
                    el.dispatchEvent(new Event(name, {{ bubbles: true }}));
                }});
            }}
        """, input_element)
        time.sleep(0.5)
        actual = input_element.inner_text().strip()
        if len(actual) >= max(10, len(text) // 2):
            logger.info("Prompt injected via JS innerHTML + events")
            return True
    except Exception as e:
        logger.error(f"JS injection failed: {e}")

    try:
        input_element.click()
        page.keyboard.press('Control+A')
        page.keyboard.press('Delete')
        time.sleep(0.2)
        page.keyboard.type(text, delay=5)
        time.sleep(0.5)
        actual = input_element.inner_text().strip()
        if len(actual) >= max(10, len(text) // 2):
            logger.info("Prompt injected via keyboard.type()")
            return True
    except Exception as e:
        logger.error(f"keyboard.type() injection failed: {e}")

    return False


def _wait_for_verification_complete(page):
    """Wait for video generation verification in Gemini (which can take a while)."""
    logger.info("Waiting for video generation to complete (this can take 2-5 minutes)...")
    
    # After submission, Gemini briefly shows a spinner, hides it, then shows "Generating video..." text,
    # before finally rendering the actual <video> element. We must wait up to ~5 mins.
    timeout = 360  # 6 minutes absolute max
    waited = 0
    poll_interval = 5
    
    # 2026-09 resync: Gemini rebuilt its UI (Angular "luminous" rewrite).
    # The video renders inside message-content > response-element > generated-video
    # > video-player > video. div[data-message-id] and button.generated-video-button
    # no longer exist.
    video_selectors = [
        'message-content generated-video video-player video',
        'message-content generated-video video',
        'generated-video video-player video',
        'generated-video video',
        'video-player video',
        'message-content video[src]',
        'div[data-message-id] video',
        'div[data-message-id] .playable-media',
        'button.generated-video-button',
        'video[src]',
    ]

    while waited < timeout:
        # Check if the video element has appeared (last match = newest message)
        found_video = False
        for sel in video_selectors:
            try:
                videos = page.query_selector_all(sel)
                el = videos[-1] if videos else None
                if el and el.is_visible():
                    found_video = True
                    logger.info(f"Video container found via {sel}!")
                    break
            except Exception:
                continue
                
        if found_video:
            # wait just a bit more for the browser to initialize the media element
            time.sleep(3)
            return True
            
        time.sleep(poll_interval)
        waited += poll_interval
        
        if waited % 30 == 0:
            logger.info(f"Still waiting for video... ({waited}s elapsed)")
            
    logger.warning("Timeout waiting for video element to become visible!")
    return False


# Locate the video response belonging to a specific prompt in the conversation.
# With parallel workers sharing the project chat, responses interleave — scope
# the download to the response following OUR prompt, not "last one on page".
_LOCATE_READY_JS = """(prompt) => {
  const norm = (s) => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
  const full = norm(prompt);
  if (!full) return false;
  // 2026-10: Gemini collapses long query bubbles - the textContent becomes the
  // first ~100 chars plus an ellipsis and a repeat of the prompt truncated at
  // ~640 chars, so a long prompt never appears contiguously. Try progressively
  // shorter needles; the first length with a match wins (ties -> most recent).
  const all = Array.from(document.querySelectorAll('user-query, message-content, model-response'));
  const qIdx = [];
  const qTexts = [];
  for (let i = 0; i < all.length; i++) {
    if (all[i].tagName.toLowerCase() === 'user-query') {
      qIdx.push(i);
      qTexts.push(norm(all[i].textContent));
    }
  }
  let qi = -1;
  for (const L of [1000, 800, 600, 500, 400, 300, 250, 200, 150, 100]) {
    const needle = full.slice(0, L);
    if (!needle) break;
    let found = -1;
    for (let k = 0; k < qTexts.length; k++) {
      if (qTexts[k].includes(needle)) found = qIdx[k];
    }
    if (found !== -1) { qi = found; break; }
  }
  if (qi === -1) return false;
  for (let i = qi + 1; i < all.length; i++) {
    const el = all[i];
    if (el.tagName.toLowerCase() === 'user-query') return false;
    const vid = el.querySelector('video');
    if (vid && vid.readyState >= 2) return true;
  }
  return false;
}"""

_LOCATE_CONTAINER_JS = """(prompt) => {
  const norm = (s) => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
  const full = norm(prompt);
  if (!full) return null;
  // Same collapsed-query handling as _LOCATE_READY_JS above.
  const all = Array.from(document.querySelectorAll('user-query, message-content, model-response'));
  const qIdx = [];
  const qTexts = [];
  for (let i = 0; i < all.length; i++) {
    if (all[i].tagName.toLowerCase() === 'user-query') {
      qIdx.push(i);
      qTexts.push(norm(all[i].textContent));
    }
  }
  let qi = -1;
  for (const L of [1000, 800, 600, 500, 400, 300, 250, 200, 150, 100]) {
    const needle = full.slice(0, L);
    if (!needle) break;
    let found = -1;
    for (let k = 0; k < qTexts.length; k++) {
      if (qTexts[k].includes(needle)) found = qIdx[k];
    }
    if (found !== -1) { qi = found; break; }
  }
  if (qi === -1) return null;
  for (let i = qi + 1; i < all.length; i++) {
    const el = all[i];
    if (el.tagName.toLowerCase() === 'user-query') return null;
    if (el.querySelector('video')) return el;
  }
  return null;
}"""


def _wait_for_own_video_response(page, prompt_text: str, timeout_s: float = 300) -> bool:
    """Wait until the video response following OUR prompt has a playable video."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if page.is_closed():
            return False
        try:
            if page.evaluate(_LOCATE_READY_JS, prompt_text):
                return True
        except Exception as e:
            # Message virtualization can tear down the JS execution context
            # mid-poll; keep waiting instead of aborting on a transient error.
            logger.debug(f"Own video response poll error (will retry): {e}")
        time.sleep(5)
    return False


def _locate_own_video_container(page, prompt_text: str):
    """Return an ElementHandle for the response content following our prompt."""
    try:
        handle = page.evaluate_handle(_LOCATE_CONTAINER_JS, prompt_text)
        return handle.as_element()
    except Exception as e:
        logger.debug(f"Prompt-based video locate failed: {e}")
        return None


def _try_download_native(page, output_path: str, prompt_text: str = None) -> Optional[str]:
    """Download the latest generated video using native Playwright download.

    2026-09 resync: the download button lives in the video player's controls
    overlay (video-player > .controls > .action-buttons) as
    button[aria-label="Download video"] inside gem-icon-button[fonticonname="download"],
    and is present in the DOM without hovering. Hovering <video> times out
    because the .controls overlay intercepts pointer events, so hover is
    best-effort only. When prompt_text is given, the download is scoped to the
    response following OUR prompt (parallel workers share the chat).
    """

    video_container_selectors = [
        'message-content generated-video video-player',
        'generated-video video-player',
        'generated-video',
        'video-player',
        'message-content video',
        'div[data-message-id] video',
        'div[data-message-id] .playable-media',
        'button.generated-video-button',
    ]

    download_button_selectors = [
        'video-player button[aria-label="Download video"]',
        'generated-video button[aria-label="Download video"]',
        'gem-icon-button[fonticonname="download"] button',
        'button[aria-label="Download video"]',
        'button[aria-label="Download"]',
        'button.download-button',
        'button[jsname][aria-label*="ownload"]',
        'a[download]',
    ]

    def _click_visible_download_button(scope=None) -> Optional[str]:
        # scope: optional ElementHandle to search inside (own prompt response)
        for btn_sel in download_button_selectors:
            try:
                if scope is not None:
                    btns = scope.query_selector_all(btn_sel)
                else:
                    btns = page.query_selector_all(btn_sel)
                if btns:
                    # Test if any of these buttons are visible and click the last one
                    for btn in reversed(btns):
                        if btn.is_visible():
                            logger.info(f"Clicking download button: {btn_sel}")
                            with page.expect_download(timeout=300000) as dl_info:
                                btn.click()
                            dl = dl_info.value
                            dl.save_as(output_path)
                            logger.info(f"Native download saved: {output_path}")
                            return output_path
            except Exception:
                continue
        return None

    def _do_hover_and_download(container, depth=0) -> Optional[str]:
        if not container or depth > 4:
            return None

        try:
            # Scroll into view and hover to trigger the toolbar (best-effort:
            # the player's .controls overlay can intercept pointer events).
            container.scroll_into_view_if_needed()
            time.sleep(1)
            try:
                container.hover(timeout=3000)
                time.sleep(2.0)  # Wait for animation
            except Exception as hover_err:
                logger.debug(f"Hover skipped at depth {depth}: {hover_err}")

            downloaded = _click_visible_download_button()
            if downloaded:
                return downloaded

            logger.debug(f"No download button visible on hover at depth {depth}. Trying parent...")
            parent = container.evaluate_handle('el => el.parentElement')
            return _do_hover_and_download(parent, depth + 1)

        except Exception as e:
            logger.debug(f"Hover/download failed at depth {depth}: {e}")
            return None

    try:
        # 2026-09: parallel workers share the project chat — scope to the
        # response following OUR prompt when we know it.
        own_container = None
        prompt_scoped = bool(prompt_text)
        if prompt_text:
            if _wait_for_own_video_response(page, prompt_text):
                own_container = _locate_own_video_container(page, prompt_text)
                if own_container is not None:
                    logger.info("Located own video response by prompt text")
            if own_container is None:
                # 2026-10: with a known prompt, a page-wide fallback here could
                # click a NEIGHBOUR response's download button (wrong video for
                # this shot). Fail and let the caller retry instead.
                logger.warning(
                    "Own video response not found; refusing page-wide "
                    "fallback (failing instead of wrong video)")
                return None

        if own_container is not None:
            # Own response only: click the download button inside it.
            downloaded = _click_visible_download_button(scope=own_container)
            if downloaded:
                return downloaded
            # The player controls overlay can need hover to appear — retry
            # within the OWN response before giving up.
            try:
                own_container.scroll_into_view_if_needed()
                own_container.hover(timeout=3000)
                time.sleep(2.0)
                downloaded = _click_visible_download_button(scope=own_container)
                if downloaded:
                    return downloaded
            except Exception as hover_err:
                logger.debug(f"Own-container hover retry failed: {hover_err}")
            logger.warning(
                "Own response has no usable download control; failing instead "
                "of page-wide search (wrong video is worse than a retry)")
            return None

        # Fast path: the button is now permanently in the DOM, no hover needed.
        downloaded = _click_visible_download_button()
        if downloaded:
            return downloaded

        video_element = None
        for sel in video_container_selectors:
            containers = page.query_selector_all(sel)
            if containers:
                video_element = containers[-1]
                logger.debug(f"Found video base element: {sel}")

                # Start recursive hover and check from the video element upwards
                path = _do_hover_and_download(video_element, 0)
                if path:
                    return path

        if not video_element:
            logger.warning("No video element found to hover.")
            return None

    except Exception as e:
        logger.debug(f"Native download preparation failed: {e}")

    return None

def _download_video_fallback(page, output_path: str) -> Optional[str]:
    """Fallback method: Extract video source and fetch directly or via JS."""
    try:
        video_selector = (
            'message-content generated-video video-player video, '
            'generated-video video, video-player video, '
            'div[data-message-id] video'
        )
        videos = page.query_selector_all(video_selector)
        
        if not videos:
            logger.error("No video elements found for fallback download.")
            return None
            
        video = videos[-1]
        src = video.get_attribute('src')
        
        if not src:
            logger.error("Video element missing src attribute.")
            return None
            
        logger.info(f"Found video src metadata: {src[:50]}...")
        
        if src.startswith('blob:'):
            # Evaluate JS to download blob using XMLHttpRequest (more reliable than fetch for some blobs)
            logger.info("Attempting to fetch blob video via JS (XHR)...")
            data_url = page.evaluate("""
                async (blobUrl) => {
                    return new Promise((resolve, reject) => {
                        const xhr = new XMLHttpRequest();
                        xhr.open('GET', blobUrl, true);
                        xhr.responseType = 'blob';
                        xhr.onload = function(e) {
                            if (this.status == 200) {
                                const blob = this.response;
                                const reader = new FileReader();
                                reader.onloadend = () => resolve(reader.result);
                                reader.readAsDataURL(blob);
                            } else {
                                reject('XHR status ' + this.status);
                            }
                        };
                        xhr.onerror = () => reject('XHR error');
                        xhr.send();
                    });
                }
            """, src)
            
            if data_url and ',' in data_url:
                _, data = data_url.split(',', 1)
                with open(output_path, 'wb') as f:
                    f.write(base64.b64decode(data))
                logger.info(f"Saved blob video: {output_path}")
                return output_path
                
        elif src.startswith('http'):
            logger.info("Attempting direct authenticated fetch for video...")
            response = page.request.get(src)
            if response.ok:
                with open(output_path, 'wb') as f:
                    f.write(response.body())
                logger.info(f"Saved video via fetch: {output_path}")
                return output_path
            else:
                logger.error(f"Direct fetch failed: HTTP {response.status}")
                
    except Exception as e:
        logger.error(f"Fallback download failed: {e}")
        
    return None

def run(image_path: str, motion_prompt: str, output_path: str, project_title: str = None, profile_dir: str = None, gemini_mode: str = None) -> Optional[str]:
    """Main entry point — run Playwright and generate a video."""
    from playwright.sync_api import sync_playwright

    gemini_url = getattr(config, 'GEMINIWEB_URL', 'https://gemini.google.com/app')
    timeout = getattr(config, 'GEMINIWEB_TIMEOUT', 120)

    logger.info(f"Generating video (GeminiWeb subprocess): {output_path}")
    logger.debug(f"  Prompt: {motion_prompt[:100]}...")
    logger.debug(f"  Reference Image: {image_path}")

    # ── Serialize generations per project chat ────────────────────
    # 2026-10: overlapping generations in one conversation trigger
    # Gemini's image-swap bug (one response's image is dropped and
    # replaced by the other exchange's picture). Acquire BEFORE the
    # browser launch so a waiting worker does not sit on a blank
    # Chrome window.
    if project_title and _acquire_chat_lock(project_title) == 'timeout':
        logger.warning(
            "Chat lock wait timed out; proceeding unlocked "
            "(overlapping generations in one chat risk Gemini's "
            "image-swap bug)")

    with sync_playwright() as playwright_instance:
        context = _create_browser_context(playwright_instance, profile_dir)
        page = context.new_page()
        # Gemini calls window.close() after its download interactions, which
        # kills the whole automation browser mid-flow — neuter it.
        page.add_init_script("window.close = () => {};")

        try:
            # ── Fast path: chat URL known from the registry — go straight to
            # the chat (skips the app home entirely). The chat page has the
            # same mode picker as the app home.
            used_existing_chat = False
            saved_url = _registry_get_chat_url(project_title) if project_title else None
            if saved_url and _open_project_chat_by_url(page, saved_url):
                logger.info(f"Opened registered project chat directly (skipped app home)")
                used_existing_chat = True
                _set_gemini_mode(page, gemini_mode)
            else:
                logger.info(f"Navigating to {gemini_url}")
                page.goto(gemini_url, wait_until='domcontentloaded', timeout=timeout * 1000)
                time.sleep(5)

                # ── Set Gemini Mode (Fast/Thinking/Pro) ──────────────────────
                _set_gemini_mode(page, gemini_mode)

                # ── Ensure correct chat ──────────────────────────────────────
                if project_title:
                    used_existing_chat = _ensure_project_chat(page, project_title)

            # Dismiss any dialogs
            try:
                dismiss_selectors = [
                    'button:has-text("Accept")',
                    'button:has-text("Got it")',
                    'button:has-text("I agree")',
                    'button:has-text("Continue")',
                ]
                for sel in dismiss_selectors:
                    try:
                        btn = page.query_selector(sel)
                        if btn and btn.is_visible():
                            btn.click()
                            time.sleep(1)
                    except Exception:
                        continue
            except Exception:
                pass


            # ── Upload the image ─────────────────────────────────────────────
            logger.info("Uploading reference image...")
            try:
                # Gemini Web uses a dynamic '+' upload menu button that spawns a file chooser
                upload_btn = None
                for sel in [
                    'button[aria-label="Upload image"]',
                    'button[aria-label="Add image"]',
                    'button[aria-label="Upload file"]',
                    'button[aria-label="Open upload file menu"]',
                    'button[aria-label="Upload"]'
                ]:
                    try:
                        btn = page.query_selector(sel)
                        if btn and btn.is_visible():
                            upload_btn = btn
                            break
                    except Exception:
                        continue

                if upload_btn:
                    logger.info(f"Clicking upload button: {upload_btn.get_attribute('aria-label')}")
                    upload_btn.click()
                    time.sleep(1)
                    
                    # See if an upload sub-menu exists, if so click it inside expect_file_chooser
                    menu_item = None
                    try:
                        # Find any menu item containing "Upload" 
                        upload_locators = page.locator('[role="menuitem"]').filter(has_text="Upload")
                        if upload_locators.count() > 0:
                            menu_item = upload_locators.first
                        else:
                            # Try generic texts
                            for text_sel in ['text="Upload from computer"', 'text="Upload image"', 'text="Upload file"']:
                                item = page.locator(text_sel).first
                                if item.is_visible():
                                    menu_item = item
                                    break
                    except Exception as e:
                        logger.error(f"Error finding submenu: {e}")
                            
                    if menu_item:
                        logger.info("Found sub-menu for upload. Triggering file chooser...")
                        try:
                            with page.expect_file_chooser(timeout=8000) as fc_info:
                                menu_item.click()
                            file_chooser = fc_info.value
                            file_chooser.set_files(image_path)
                            logger.info("Image file selected via submenu file chooser")
                        except Exception as e:
                            logger.error(f"File chooser timeout or failure: {e}")
                            return None
                    else:
                        logger.info("No sub-menu found, assuming direct file chooser on click")
                        file_input_selector = 'input[type="file"]'
                        file_input = page.query_selector(file_input_selector)
                        if file_input:
                            page.set_input_files(file_input_selector, image_path)
                            logger.info("Image file selected via direct file input after menu toggle")
                        else:
                            logger.error("Could not find file input or trigger file chooser")
                            return None
                else:
                    # Fallback to pure input if the UI changes
                    logger.warning("No upload button found, falling back to hidden file input")
                    page.set_input_files('input[type="file"]', image_path)
                    
                time.sleep(3)
            except Exception as e:
                logger.error(f"Failed to upload image: {e}")
                
                # Check if it was because we ran out of prompt input context or just an unknown error.
                return None


            # ── Find the chat input box ──────────────────────────────────────
            input_selectors = [
                'div.ql-editor[contenteditable="true"]',
                'div.ql-editor',
                'div[aria-label="Enter a prompt for Gemini"]',
                'div[aria-label="Describe your image"]',
                'rich-textarea div[contenteditable="true"]',
                'div[contenteditable="true"][role="textbox"]',
                'div[contenteditable="true"]',
                'textarea',
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    el = page.wait_for_selector(selector, timeout=8000, state='visible')
                    if el:
                        input_element = el
                        logger.info(f"Found input element: {selector}")
                        break
                except Exception:
                    continue

            if not input_element:
                logger.error("Could not find the chat input field")
                return None

            # ── Inject the prompt ────────────────────────────────────────────
            # Prepend a clear instruction for Veo 3.1 video generation
            full_prompt = f"Generate a video: {motion_prompt}"
            injected = _inject_text_into_input(page, input_element, full_prompt)
            if not injected:
                logger.error("All prompt injection attempts failed")
                return None

            time.sleep(1.0)

            # ── Submit the prompt ────────────────────────────────────────────
            send_selectors = [
                'button[aria-label="Send message"]',
                'button.send-button',
                'button[data-test-id="send-button"]',
                'button[aria-label="Send"]',
            ]
            sent = False
            for selector in send_selectors:
                try:
                    send_btn = page.wait_for_selector(selector, timeout=5000, state='visible')
                    if send_btn:
                        send_btn.click()
                        sent = True
                        logger.info(f"Clicked send button: {selector}")
                        break
                except Exception:
                    continue
                    
            if not sent:
                page.keyboard.press('Enter')

            logger.info("Request submitted, waiting for video generation...")
            
            # Wait for generation to finish
            _wait_for_verification_complete(page)

            # ── Name the chat after the project so future runs reuse it ─────
            if project_title and not used_existing_chat:
                if _rename_current_chat(page, project_title):
                    _registry_set_chat_url(project_title, page.url)

            # ── Download the video ───────────────────────────────────────────
            # Scoped to the response following OUR prompt so parallel workers
            # sharing the project chat never download each other's videos.
            result = _try_download_native(page, output_path, prompt_text=full_prompt)

            if not result and prompt_text:
                # Right after completion the download control may not be
                # attached yet or the file preparation can lag - give it one
                # settled retry before falling back.
                logger.warning("First download attempt failed; retrying once after 20s")
                time.sleep(20)
                result = _try_download_native(page, output_path, prompt_text=full_prompt)

            if not result:
                # Try fallback (blob / direct fetch)
                result = _download_video_fallback(page, output_path)

            if result and os.path.exists(result):
                file_size = os.path.getsize(result)
                logger.info(f"Generated (GeminiWeb Video): {result} ({file_size:,} bytes)")
                return result
            else:
                logger.error("Failed to download the generated video.")
                diag_path = output_path.replace('.mp4', '_diagnostic.png')
                page.screenshot(path=diag_path, full_page=False)
                logger.info(f"Diagnostic screenshot saved: {diag_path}")
                
                # Dump the HTML of the last message so we can inspect the Veo 3.1 structure
                try:
                    last_msg_html = page.evaluate('''() => {
                        const msgs = document.querySelectorAll('message-content');
                        return msgs.length > 0 ? msgs[msgs.length - 1].innerHTML : document.body.innerHTML;
                    }''')
                    html_dump_path = os.path.join(getattr(config, 'OUTPUT_DIR', 'output'), 'failed_video_dom.html')
                    with open(html_dump_path, 'w', encoding='utf-8') as f:
                        f.write(last_msg_html)
                    logger.info(f"Diagnostic HTML saved to: {html_dump_path}")
                except Exception as e:
                    logger.error(f"Failed to dump HTML: {e}")
                    
                time.sleep(15)  # Let it stay open a tiny bit longer for the user
                return None

        finally:
            # Never leave the per-project chat lock held: drain any leaked
            # inner acquisitions so the lock file is always removed.
            if project_title:
                for _ in range(10):
                    if _HELD_CHAT_LOCK != project_title:
                        break
                    _release_chat_lock(project_title)
            try:
                page.close()
            except Exception:
                pass
            try:
                context.close()
            except Exception:
                pass


if __name__ == "__main__":
    import argparse
    try:
        # Persist the run log - parallel-download failures were previously
        # undiagnosable because subprocess output was dropped.
        import logging as _logging
        from logging.handlers import RotatingFileHandler
        _log_dir = getattr(config, 'LOG_DIR', 'logs')
        os.makedirs(_log_dir, exist_ok=True)
        _fh = RotatingFileHandler(
            os.path.join(_log_dir, 'geminiweb_video_subprocess.log'),
            maxBytes=2000000, backupCount=2, encoding='utf-8')
        _fh.setLevel(_logging.DEBUG)
        _fh.setFormatter(_logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s():%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'))
        _logging.getLogger().addHandler(_fh)
        _logging.getLogger().setLevel(_logging.DEBUG)
    except Exception:
        pass
    parser = argparse.ArgumentParser()
    parser.add_argument("image_path")
    parser.add_argument("motion_prompt")
    parser.add_argument("output_path")
    parser.add_argument("project_title", nargs='?', default=None)
    parser.add_argument("--profile-dir", default=None)
    parser.add_argument("--gemini-mode", default=None)
    args = parser.parse_args()

    result = run(args.image_path, args.motion_prompt, args.output_path, args.project_title, args.profile_dir, args.gemini_mode)
    if result:
        print(f"SUCCESS:{result}")
        sys.exit(0)
    else:
        print("FAILED")
        sys.exit(1)
