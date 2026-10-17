"""
FlowWeb Image Subprocess — standalone Playwright script for Google Flow.

Invoked as a subprocess by core/flowweb_image_generator.py (same isolation
rationale as geminiweb_subprocess: Playwright's sync API cannot run inside
the FastAPI/asyncio process on Windows).

Usage:
    python -m core.flowweb_image_subprocess <prompt> <output_path> [options]

Exit code 0 + prints "SUCCESS:<path>" on success, exit code 1 + "FAILED".

Flow automation contract (https://flow.google.com/):
1. Project handling mirrors the GeminiWeb chat registry: the project-title ->
   project-URL registry (output/flow_project_registry.json) is consulted first;
   otherwise the Flow home page is searched for a project card with the title
   (click to open); otherwise a new project is created via "New project".
   Newly created/opened project URLs are registered for future runs.
2. Generation settings live in the settings popover of the prompt bar
   (Image/Video tabs, aspect ratio, model, outputs per prompt). Every setting
   is only touched when its current value differs from the requested one —
   the picker state is read first ("already selected -> skip" to save time).
3. Agent mode is NEVER toggled: it stays at its default (off).
4. The prompt is typed into the Slate contenteditable box and submitted with
   the arrow button; completion is detected by a NEW "Generated image" tile
   that has fully rendered.
"""
import sys
import os
import re
import time
from typing import Optional, List

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
from core.logger_config import get_logger

logger = get_logger(__name__)

# Model names as shown in Flow's model picker (screenshot/i18n verified)
FLOW_MODEL_CHOICES = ["Nano Banana Pro", "Nano Banana 2 Lite", "Nano Banana 2.1"]
# Aspect ratios Flow supports in the settings popover (exact button labels)
FLOW_ASPECT_RATIOS = ["16:9", "4:3", "1:1", "3:4", "9:16"]
# Outputs-per-prompt buttons (x1 is Flow's default; we keep it unless told else)
FLOW_OUTPUT_CHOICES = ["x1", "x2", "x3", "x4"]
# Workspace key for generations started without a project title (callers that
# don't pass one). They share one self-healing Flow workspace instead of
# opening the home page (which has no prompt box and would only time out).
DEFAULT_WORKSPACE_KEY = "__flow_default_workspace__"


def _normalize_text(text: str) -> str:
    """Lowercase, collapse whitespace and strip emoji/non-ascii decorations
    ('🍌 Nano Banana 2.1' -> 'nano banana 2.1') for robust label matching."""
    if not text:
        return ""
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip().lower()


# ── Mark + real-click helper ────────────────────────────────────────────────
# Flow's React app ignores synthetic element.click() events dispatched from
# JS (its handlers bind to the pointer-event pipeline), so JS element scans
# only MARK the chosen node and the actual click goes through Playwright's
# real input pipeline. A synthetic click remains as last-resort fallback.
_AVF_MARK = 'data-avf-click'


def _real_click_marked(page, timeout_ms: int = 8000) -> bool:
    sel = f'[{_AVF_MARK}="1"]'
    try:
        page.click(sel, timeout=timeout_ms)
        return True
    except Exception as e:
        logger.debug(f"Real click on marked element failed: {e}")
        try:
            page.evaluate(f"() => document.querySelector('{sel}')?.click()")
            return True
        except Exception:
            return False
    finally:
        try:
            page.evaluate(f"() => document.querySelector('{sel}')?.removeAttribute('{_AVF_MARK}')")
        except Exception:
            pass


def _keyboard_activate_marked(page) -> bool:
    """Focus the marked element and press Enter — native button behaviour
    fires a trusted click without moving the mouse, which sidesteps hover
    tooltips that intercept pointer clicks (e.g. Flow's credit-cost tooltip
    over the settings chip)."""
    sel = f'[{_AVF_MARK}="1"]'
    try:
        focused = page.evaluate(f"""() => {{
            const el = document.querySelector('{sel}');
            if (!el) return false;
            el.focus();
            return document.activeElement === el;
        }}""")
        if not focused:
            return False
        page.keyboard.press('Enter')
        return True
    except Exception as e:
        logger.debug(f"Keyboard activation failed: {e}")
        return False
    finally:
        try:
            page.evaluate(f"() => document.querySelector('{sel}')?.removeAttribute('{_AVF_MARK}')")
        except Exception:
            pass


# ── Per-project concurrency control (file locks, cross-process safe) ────────
# Two locks per project:
# - Generation slots: FLOW_PROJECT_CONCURRENCY slot files allow N parallel
#   generations inside one Flow project (Flow's grid handles concurrent
#   generations natively — that is what x2-x4 outputs do).
# - Settings lock (single slot): serializes the fast phase that must not race
#   between parallel workers — project creation/lookup (first run for a
#   project would otherwise create two Flow projects) and the settings
#   popover through prompt submit (Flow applies settings to future outputs,
#   so a concurrent change could land in the other worker's generation).
_HELD_LOCK_PATH: Optional[str] = None
_HELD_SETTINGS_LOCK: Optional[str] = None
_LOCK_STALE_SECONDS = 900  # steal after 15 min
_LOCK_POLL_SECONDS = 3


def _slot_lock_path(project_title: str, slot: int) -> str:
    safe = ''.join(c if c.isalnum() or c in '._-' else '_' for c in project_title)[:80]
    return os.path.join(getattr(config, 'OUTPUT_DIR', 'output'),
                        f'flow_project_lock_{safe}_slot{slot}.lock')


def _settings_lock_path(project_title: str) -> str:
    safe = ''.join(c if c.isalnum() or c in '._-' else '_' for c in project_title)[:80]
    return os.path.join(getattr(config, 'OUTPUT_DIR', 'output'),
                        f'flow_settings_lock_{safe}.lock')


def _lock_holder_dead(lock_path: str) -> bool:
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
            return k32.GetLastError() != 5
        res = k32.WaitForSingleObject(h, 0)
        k32.CloseHandle(h)
        return res != 0x102
    except Exception:
        return False


def _try_lock_file(lock_path: str) -> bool:
    """Atomically create a lock file (stealing it when the holder is dead)."""
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, f"{os.getpid()} {time.time()}".encode())
        os.close(fd)
        return True
    except FileExistsError:
        try:
            if _lock_holder_dead(lock_path) or (
                    time.time() - os.path.getmtime(lock_path) > _LOCK_STALE_SECONDS):
                logger.warning(f"Stealing stale Flow lock (dead holder): {lock_path}")
                os.remove(lock_path)
                return _try_lock_file(lock_path)
        except OSError:
            pass
        return False
    except OSError as e:
        logger.debug(f"Flow lock open failed ({lock_path}): {e}")
        return True  # proceed best-effort on unexpected FS errors


def _release_lock_file(lock_path: Optional[str]) -> None:
    if not lock_path:
        return
    try:
        os.remove(lock_path)
    except OSError:
        pass


def _acquire_project_lock(project_title: str, timeout: int = 600) -> bool:
    """Grab one of the project's generation slots (re-entrant aware).

    Returns True when a slot is held (or best-effort after the wait times
    out — the caller proceeds unlocked, as before)."""
    global _HELD_LOCK_PATH
    slots = max(1, int(getattr(config, 'FLOW_PROJECT_CONCURRENCY', 2)))
    deadline = time.time() + timeout
    while True:
        if _HELD_LOCK_PATH:
            return True  # already hold a slot in this process
        for slot in range(slots):
            lock_path = _slot_lock_path(project_title, slot)
            if _try_lock_file(lock_path):
                _HELD_LOCK_PATH = lock_path
                logger.info(f"Acquired Flow generation slot {slot + 1}/{slots} for '{project_title}'")
                return True
        if time.time() >= deadline:
            logger.warning(f"Flow generation slots all busy for '{project_title}'; "
                           f"proceeding unlocked after {timeout}s")
            return True
        logger.debug(f"Flow generation slots busy for '{project_title}'; waiting...")
        time.sleep(_LOCK_POLL_SECONDS)


def _release_project_lock(project_title: str) -> None:
    global _HELD_LOCK_PATH
    _release_lock_file(_HELD_LOCK_PATH)
    _HELD_LOCK_PATH = None
    logger.info(f"Released Flow generation slot for '{project_title}'")


def _acquire_settings_lock(project_title: str, timeout: int = 300) -> bool:
    """Serialize project lookup + settings application + submit between the
    project's parallel workers (single slot). Best-effort on timeout."""
    global _HELD_SETTINGS_LOCK
    if _HELD_SETTINGS_LOCK:
        return True
    deadline = time.time() + timeout
    lock_path = _settings_lock_path(project_title)
    while True:
        if _try_lock_file(lock_path):
            _HELD_SETTINGS_LOCK = lock_path
            logger.info(f"Acquired Flow settings lock for '{project_title}'")
            return True
        if time.time() >= deadline:
            logger.warning(f"Flow settings lock wait timed out for '{project_title}'; proceeding unlocked")
            return True
        time.sleep(_LOCK_POLL_SECONDS)


def _release_settings_lock(project_title: str) -> None:
    global _HELD_SETTINGS_LOCK
    _release_lock_file(_HELD_SETTINGS_LOCK)
    _HELD_SETTINGS_LOCK = None
    logger.info(f"Released Flow settings lock for '{project_title}'")


# ── Project registry (project_title -> project URL) ─────────────────────────

def _registry_path() -> str:
    return os.path.join(getattr(config, 'OUTPUT_DIR', 'output'), 'flow_project_registry.json')


def _registry_get_project_url(project_title: str) -> Optional[str]:
    try:
        import json
        path = _registry_path()
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            url = data.get(project_title)
            if url and '/project' in url:
                return url
    except Exception as e:
        logger.debug(f"Flow registry read failed: {e}")
    return None


def _registry_set_project_url(project_title: str, project_url: str) -> None:
    try:
        from core import json_atomic
        path = _registry_path()
        if project_url and '/project' in project_url:
            def _set(data):
                if not isinstance(data, dict):
                    data = {}
                data[project_title] = project_url.split('?')[0]
                return data

            os.makedirs(os.path.dirname(path), exist_ok=True)
            json_atomic.update_json(path, _set, default={})
            logger.info(f"Registered Flow project: '{project_title}' -> {project_url}")
    except Exception as e:
        logger.debug(f"Flow registry write failed: {e}")


# ── Browser helpers ──────────────────────────────────────────────────────────

def _create_browser_context(playwright_instance, profile_dir=None):
    """Persistent browser context sharing the GeminiWeb Google-login profile."""
    chrome_profile = profile_dir or getattr(config, 'GEMINIWEB_CHROME_PROFILE', None)
    if not chrome_profile:
        chrome_profile = os.path.join(getattr(config, 'OUTPUT_DIR', 'output'), 'chrome_profile')
    os.makedirs(chrome_profile, exist_ok=True)

    browser_type_name = getattr(config, 'PLAYWRIGHT_BROWSER', 'chromium').lower()
    channel = getattr(config, 'PLAYWRIGHT_CHANNEL', 'chrome')

    if browser_type_name == "firefox":
        browser_type = playwright_instance.firefox
        channel = None
    elif browser_type_name == "webkit":
        browser_type = playwright_instance.webkit
        channel = None
    else:
        browser_type = playwright_instance.chromium
        valid_chromium_channels = ["chrome", "chrome-beta", "chrome-dev", "chrome-canary",
                                   "msedge", "msedge-beta", "msedge-dev", "msedge-canary"]
        if channel not in valid_chromium_channels:
            channel = None

    logger.info(f"Using browser: {browser_type_name}, channel: {channel}, profile: {chrome_profile}")

    if browser_type_name == "chromium":
        launch_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-session-crashed-bubble',
            '--no-first-run',
            '--no-default-browser-check',
        ]
    else:
        launch_args = []

    context = browser_type.launch_persistent_context(
        user_data_dir=chrome_profile,
        headless=False,
        channel=channel if channel else None,
        args=launch_args,
        viewport={'width': 1440, 'height': 960},
        ignore_default_args=['--enable-automation'],
        accept_downloads=True,
    )
    return context


def _dismiss_overlays(page):
    """Best-effort dismissal of promo banners / intro dialogs that block the
    prompt bar (announcement carousel, 'Nano Banana Pro' intro, cookie consent)."""
    dismiss_texts = ["Try now", "Got it", "Accept all", "I agree", "Accept", "Continue", "OK"]
    for sel in (
        'button[aria-label*="Dismiss" i]',
        'button[aria-label*="Close" i]',
    ):
        try:
            for btn in page.query_selector_all(sel)[:3]:
                if btn.is_visible():
                    btn.click()
                    time.sleep(1)
        except Exception:
            continue
    for text in dismiss_texts:
        try:
            for btn in page.query_selector_all(f'button:has-text("{text}")')[:3]:
                if btn.is_visible():
                    btn.click()
                    time.sleep(1)
                    break
        except Exception:
            continue


def _wait_for_prompt_box(page, timeout_s: int = 20):
    """Wait until the project prompt bar (Slate contenteditable) is usable."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            box = page.query_selector('div[contenteditable="true"][data-slate-editor="true"], '
                                      'div[role="textbox"][contenteditable="true"], '
                                      'div[contenteditable="true"]')
            if box and box.is_visible():
                return box
        except Exception:
            pass
        time.sleep(1)
    return None


def _open_project_by_url(page, project_url: str) -> bool:
    """Navigate to a registered project URL and verify it actually loaded."""
    try:
        page.goto(project_url, wait_until='domcontentloaded', timeout=45000)
        time.sleep(6)
        if _wait_for_prompt_box(page, timeout_s=15):
            return True
        logger.debug(f"Registered Flow project URL did not load a project: {project_url}")
    except Exception as e:
        logger.debug(f"Failed to open Flow project URL {project_url}: {e}")
    return False


def _open_existing_project_card(page, project_title: str) -> bool:
    """On the Flow home page, find the project card titled project_title and
    click it (requirement: open existing projects by clicking)."""
    target = _normalize_text(project_title)
    if not target:
        return False

    # Give the project grid a moment to render
    try:
        page.wait_for_selector('text="New project"', timeout=10000, state='visible')
    except Exception:
        pass

    candidates = page.locator(f'text="{project_title}"')
    try:
        count = candidates.count()
    except Exception:
        count = 0
    if not count:
        # Fallback: case-insensitive has-text scan
        candidates = page.locator(f':has-text("{project_title}")')
        try:
            count = candidates.count()
        except Exception:
            count = 0

    for i in range(min(count, 10)):
        try:
            el = candidates.nth(i)
            if not el.is_visible():
                continue
            text = _normalize_text(el.inner_text() or '')
            if text and target not in text and text not in target:
                continue
            logger.info(f"Found existing Flow project card for '{project_title}'. Clicking...")
            el.click()
            time.sleep(5)
            if _wait_for_prompt_box(page, timeout_s=20):
                if '/project' in page.url:
                    _registry_set_project_url(project_title, page.url)
                return True
            # Click did not open a project; continue with next candidate
        except Exception as e:
            logger.debug(f"Project card candidate {i} failed: {e}")
            continue
    return False


def _create_new_project(page, project_title: str) -> bool:
    """Click 'New project' on the Flow home page and wait for the project
    editor. The project is renamed to project_title (Flow defaults to names
    like 'Oct 16 - 12:57') and the URL registered under project_title."""
    logger.info("Creating a new Flow project...")
    clicked = False
    for sel in (
        'button:has-text("New project")',
        'a:has-text("New project")',
        'div[role="button"]:has-text("New project")',
        ':text("New project")',
    ):
        try:
            loc = page.locator(sel).first
            if loc.is_visible():
                loc.click()
                clicked = True
                break
        except Exception:
            continue
    if not clicked:
        logger.error("'New project' button not found on Flow home page")
        return False

    # Wait for the project editor to open (URL gains /project/<id>)
    try:
        page.wait_for_url('**/project/**', timeout=30000)
    except Exception:
        pass
    time.sleep(4)

    if _wait_for_prompt_box(page, timeout_s=25):
        if '/project' in page.url:
            _registry_set_project_url(project_title, page.url)
        _rename_flow_project(page, project_title)
        return True
    logger.error("New Flow project did not open a prompt box")
    return False


# Flow's header project-name input (top-left corner). New projects default to
# timestamp names like 'Oct 16 - 12:57'.
_PROJECT_NAME_INPUT_SEL = 'input[aria-label="Editable text"]'
_AUTO_NAME_RE = re.compile(r'^[a-z]{3} \d{1,2} - \d{1,2}:\d{2}$', re.IGNORECASE)


def _read_project_name(page) -> Optional[str]:
    try:
        value = page.evaluate("""(sel) => {
            const el = document.querySelector(sel);
            return el ? el.value : null;
        }""", _PROJECT_NAME_INPUT_SEL)
        return (value or '').strip() or None
    except Exception:
        return None


def _rename_flow_project(page, project_title: str, only_auto_names: bool = False) -> bool:
    """Set the header project name (top-left corner) to project_title.

    only_auto_names=True only renames when the current name is one of Flow's
    auto-generated timestamp names ('Oct 16 - 12:57'), so user-chosen names
    are never overwritten on later runs."""
    if not project_title:
        return False
    try:
        current = _read_project_name(page)
        if current is None:
            logger.debug("Project name input not found; skipping rename")
            return False
        if current == project_title:
            logger.debug(f"Flow project already named '{project_title}'")
            return True
        if only_auto_names and not _AUTO_NAME_RE.match(current):
            logger.debug(f"Keeping user-set Flow project name '{current}'")
            return False

        loc = page.locator(_PROJECT_NAME_INPUT_SEL).first
        loc.wait_for(state='visible', timeout=8000)
        loc.click()
        loc.fill(project_title)
        page.keyboard.press('Enter')
        time.sleep(1.5)
        # Blur so the editor commits the change
        try:
            box = page.query_selector('div[contenteditable="true"]')
            if box:
                box.click(position={"x": 5, "y": 5})
        except Exception:
            page.keyboard.press('Escape')
        time.sleep(1)

        verified = _read_project_name(page)
        if verified == project_title:
            logger.info(f"Renamed Flow project to '{project_title}'")
            return True
        logger.warning(f"Flow project rename did not verify (shows '{verified}')")
        return False
    except Exception as e:
        logger.debug(f"Flow project rename failed: {e}")
        return False


def _ensure_flow_project(page, project_title: str) -> bool:
    """1. Open registered project URL. 2. Click the existing project card on
    the home page. 3. Create a new project. Returns True when a project with
    a usable prompt bar is open. Empty titles share DEFAULT_WORKSPACE_KEY."""
    flow_url = getattr(config, 'FLOWWEB_URL', 'https://flow.google.com/')
    project_title = project_title or DEFAULT_WORKSPACE_KEY

    saved_url = _registry_get_project_url(project_title)
    if saved_url and _open_project_by_url(page, saved_url):
        logger.info(f"Opened registered Flow project for '{project_title}' (skipped home)")
        # Heal workspaces created before renaming existed (auto timestamp names)
        _rename_flow_project(page, project_title, only_auto_names=True)
        return True
    if saved_url:
        logger.info(f"Registered Flow project for '{project_title}' is gone; searching home page")

    logger.info(f"Navigating to {flow_url}")
    page.goto(flow_url, wait_until='domcontentloaded', timeout=45000)
    time.sleep(6)
    _dismiss_overlays(page)

    if _open_existing_project_card(page, project_title):
        logger.info(f"Opened existing Flow project '{project_title}' by clicking its card")
        return True

    return _create_new_project(page, project_title)


# ── Settings popover ─────────────────────────────────────────────────────────

_OPEN_SETTINGS_JS = r"""() => {
  const norm = (s) => (s || '').replace(/[^\x00-\x7F]+/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
  // The settings chip lives in the prompt bar (aria-label 'Settings trigger')
  // and shows the model name plus the outputs count ('Nano Banana 2.1 x1').
  const buttons = Array.from(document.querySelectorAll('button, div[role="button"]'));
  const matches = buttons.filter(b => {
    if (!b.offsetParent && b.getClientRects().length === 0) return false; // not rendered
    const t = norm(b.textContent);
    const aria = norm(b.getAttribute('aria-label') || '');
    if (aria.includes('settings trigger') || aria === 'settings') return true;
    if (/\bnano banana\b/.test(t) || /\bveo\b/.test(t)) return true;
    if (/\bx[1-4]\b/.test(t) && t.length <= 24) return true;
    return false;
  });
  if (!matches.length) return false;
  // Prefer the last match (prompt-bar chip) over any lookalike elsewhere;
  // mark it — the real click happens through Playwright's input pipeline.
  matches[matches.length - 1].setAttribute('data-avf-click', '1');
  return true;
}"""

_SETTINGS_OPEN_JS = r"""() => {
  const norm = (s) => (s || '').replace(/[^\x00-\x7F]+/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
  const labels = Array.from(document.querySelectorAll('div, span, h2, h3, label'))
    .filter(e => e.offsetParent && e.getClientRects().length > 0)
    .map(e => norm(e.textContent));
  if (labels.some(t => t.includes('aspect ratio') || t.includes('outputs per prompt'))) return true;
  // The popover renders no section labels — detect it by its controls:
  // aspect-ratio chips, outputs x1-x4 buttons, or Image/Video tabs. Toggle
  // text carries concatenated icon ligatures ('crop_16_916:9'), so suffix
  // matching is required.
  const btns = Array.from(document.querySelectorAll('button, div[role="button"], div[role="radio"]'))
    .filter(e => e.offsetParent && e.getClientRects().length > 0)
    .map(e => norm(e.textContent));
  const endsWithAny = (list) => btns.some(t => list.some(w => t === w || t.endsWith(w)));
  const arCount = ['16:9', '4:3', '1:1', '3:4', '9:16'].filter(ar => btns.some(t => t === ar || t.endsWith(ar))).length;
  const outCount = ['x1', 'x2', 'x3', 'x4'].filter(x => btns.includes(x)).length;
  const hasTabs = endsWithAny(['image']) && endsWithAny(['video']);
  return arCount >= 3 || outCount >= 3 || hasTabs;
}"""


def _settings_popover_open(page) -> bool:
    try:
        return page.evaluate(_SETTINGS_OPEN_JS)
    except Exception:
        return False


def _open_settings_popover(page, attempts: int = 3) -> bool:
    """Open the settings popover from the prompt-bar chip. Returns True when
    the popover content (aspect ratio / outputs labels) is visible. The chip
    carries a hover tooltip that intercepts pointer clicks, so the marked
    chip is activated via keyboard (focus + Enter) first."""
    if _settings_popover_open(page):
        return True
    for attempt in range(attempts):
        try:
            if not page.evaluate(_OPEN_SETTINGS_JS):
                logger.debug("Settings chip not found in prompt bar")
            else:
                if not _keyboard_activate_marked(page):
                    _real_click_marked(page)
            time.sleep(2)
            if _settings_popover_open(page):
                return True
        except Exception as e:
            logger.debug(f"Open settings attempt {attempt + 1} failed: {e}")
        time.sleep(1.5)
    return False


def _close_settings_popover(page):
    try:
        page.keyboard.press("Escape")
        time.sleep(1)
        # Click elsewhere to be sure (popover may ignore Escape)
        if _settings_popover_open(page):
            try:
                box = page.query_selector('div[contenteditable="true"]')
                if box:
                    box.click(position={"x": 5, "y": 5})
            except Exception:
                pass
            time.sleep(1)
            if _settings_popover_open(page):
                page.keyboard.press("Escape")
    except Exception:
        pass


# Element-state scan for the popover controls. Returns buttons with their
# labels plus selected-state hints so each setting is only clicked when its
# value actually differs ("already selected -> don't change; save time").
_POPOVER_CONTROLS_JS = r"""() => {
  const norm = (s) => (s || '').replace(/[^\x00-\x7F]+/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
  const nodes = Array.from(document.querySelectorAll('button, div[role="button"], div[role="radio"], div[role="menuitemradio"], [aria-pressed], [role="option"], [role="menuitem"]'));
  return nodes
    .filter(e => e.offsetParent && e.getClientRects().length > 0)
    .map(e => {
      const cls = (e.className && e.className.baseVal !== undefined) ? e.className.baseVal : (e.className || '');
      // Selected-state styling (mat-button-toggle-checked) sits on the
      // mat-button-toggle wrapper, not on the inner button.
      let parent = e.parentElement, pcls = '';
      for (let i = 0; i < 2 && parent; i++) {
        pcls += ' ' + String(parent.className || '').toLowerCase();
        parent = parent.parentElement;
      }
      return {
        text: norm(e.textContent).slice(0, 80),
        aria: norm(e.getAttribute('aria-label') || ''),
        pressed: e.getAttribute('aria-pressed'),
        checked: e.getAttribute('aria-checked'),
        state: e.getAttribute('data-state') || '',
        cls: String(cls).toLowerCase(),
        pcls: pcls.trim(),
      };
    });
}"""


def _selected_hint(ctrl) -> bool:
    """Heuristic: is this toggle/chip currently selected/active?"""
    if ctrl.get('pressed') == 'true' or ctrl.get('checked') == 'true':
        return True
    if ctrl.get('state') == 'checked' or ctrl.get('state') == 'active':
        return True
    cls = (ctrl.get('cls', '') + ' ' + ctrl.get('pcls', ''))
    return any(marker in cls for marker in ('selected', 'active', 'checked', 'bg-white', 'bg-primary'))


def _control_text_matches(ctrl: dict, wanted: str) -> bool:
    """Exact or suffix match — mat-button-toggle text carries icon ligature
    prefixes concatenated WITHOUT a space ('crop_16_916:9', 'imageimage'),
    so 'endswith(wanted)' is the reliable matcher."""
    text = ctrl.get('text') or ''
    return text == wanted or text.endswith(wanted)


def _find_control(controls, predicate):
    matches = [c for c in controls if predicate(c)]
    return matches[0] if matches else None


_CLICK_MARKED_BY_TEXT_JS = r"""(wanted) => {
  const norm = (s) => (s || '').replace(/[^\x00-\x7F]+/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
  const nodes = Array.from(document.querySelectorAll('button, div[role="button"], div[role="radio"], [role="menuitemradio"]'));
  const vis = nodes.filter(e => e.offsetParent && e.getClientRects().length > 0);
  // Suffix match: mat-button-toggle text carries concatenated icon ligature
  // prefixes ('crop_16_916:9'); outputs are exact ('x1').
  const match = vis.find(e => {
    const t = norm(e.textContent);
    return t === wanted || t.endsWith(wanted);
  });
  if (!match) return false;
  match.setAttribute('data-avf-click', '1');
  return true;
}"""


def _click_popover_button(page, ctrl) -> bool:
    """Click a scanned popover control by its visible text (suffix-tolerant)
    through the real input pipeline."""
    wanted = (ctrl.get('text') or '').strip()
    if not wanted:
        return False
    try:
        if not page.evaluate(_CLICK_MARKED_BY_TEXT_JS, wanted):
            logger.debug(f"Popover control '{wanted}' not found for click")
            return False
        return _real_click_marked(page, timeout_ms=5000)
    except Exception as e:
        logger.debug(f"Click popover control '{wanted}' failed: {e}")
        return False


def _log_agent_state(page):
    """Read-only: log the Agent toggle state. NEVER clicks it (stays off)."""
    try:
        for btn in page.query_selector_all('button:has-text("Agent")'):
            if btn.is_visible():
                pressed = btn.get_attribute('aria-pressed')
                logger.info(f"Flow Agent button visible (aria-pressed={pressed}); leaving untouched")
                return
    except Exception:
        pass


def _select_media_type_image(page, controls) -> bool:
    """Make sure the Image tab (not Video) is active in the popover."""
    def is_tab(c):
        return (_control_text_matches(c, 'image') or _control_text_matches(c, 'video'))

    image_ctrl = _find_control(controls, lambda c: _control_text_matches(c, 'image'))
    video_ctrl = _find_control(controls, lambda c: _control_text_matches(c, 'video'))
    if image_ctrl is None:
        logger.debug("Image/Video tabs not found in settings popover")
        return True  # nothing to do; Image may be the only mode available

    if _selected_hint(image_ctrl):
        logger.info("Flow media type already 'Image'; skipping")
        return True
    logger.info("Selecting Flow media type: Image")
    if _click_popover_button(page, image_ctrl):
        time.sleep(1.5)
        if video_ctrl and _selected_hint(video_ctrl):
            logger.warning("Image tab click did not register")
        return True
    return False


def _select_aspect_ratio(page, aspect_ratio: str) -> bool:
    if not aspect_ratio:
        aspect_ratio = getattr(config, 'IMAGE_ASPECT_RATIO', '16:9')
    ar = aspect_ratio.strip()
    if ar not in FLOW_ASPECT_RATIOS:
        logger.warning(f"Aspect ratio '{ar}' not offered by Flow {FLOW_ASPECT_RATIOS}; using 16:9")
        ar = "16:9"

    controls = page.evaluate(_POPOVER_CONTROLS_JS) or []
    target = _find_control(controls, lambda c: _control_text_matches(c, ar))
    if target is None:
        logger.warning(f"Aspect ratio button '{ar}' not found in popover")
        return False
    if _selected_hint(target):
        logger.info(f"Flow aspect ratio already {ar}; skipping")
        return True
    logger.info(f"Setting Flow aspect ratio: {ar}")
    if not _click_popover_button(page, target):
        return False
    time.sleep(1)
    return True


def _select_model(page, model: str) -> bool:
    """Open the model dropdown and pick the requested model — only when the
    current selection differs (chip already shows the model name)."""
    desired = model or getattr(config, 'FLOW_IMAGE_MODEL', 'Nano Banana 2.1')
    desired_n = _normalize_text(desired)

    controls = page.evaluate(_POPOVER_CONTROLS_JS) or []
    # The dropdown trigger carries the current model name
    trigger = None
    for c in controls:
        text = c['text']
        if any(_normalize_text(name) in text for name in FLOW_MODEL_CHOICES):
            trigger = c
            break
    if trigger is None:
        logger.warning("Flow model dropdown not found in popover")
        return False

    current_text = trigger['text']
    if desired_n in current_text:
        logger.info(f"Flow model already '{desired}'; skipping")
        return True

    logger.info(f"Switching Flow model from '{current_text}' to '{desired}'")
    if not _click_popover_button(page, trigger):
        return False
    time.sleep(1.5)

    # Menu items appear after opening the dropdown — mark a match and click
    # through the real input pipeline
    menu = page.evaluate(r"""(desired) => {
      const norm = (s) => (s || '').replace(/[^\x00-\x7F]+/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
      const wanted = norm(desired);
      const nodes = Array.from(document.querySelectorAll('[role="menuitem"], [role="option"], [role="menu"] button, [role="listbox"] > *'));
      const vis = nodes.filter(e => e.offsetParent && e.getClientRects().length > 0);
      let exact = null, partial = null;
      for (const e of vis) {
        const t = norm(e.textContent);
        if (!t) continue;
        if (t === wanted) { exact = e; break; }
        if (!partial && t.includes(wanted)) partial = e;
      }
      const target = exact || partial;
      if (!target) return false;
      target.setAttribute('data-avf-click', '1');
      return true;
    }""", desired)
    if not menu:
        logger.warning(f"Flow model menu item '{desired}' not found")
        page.keyboard.press("Escape")
        return False
    _real_click_marked(page)
    time.sleep(1.5)

    # Verify the trigger now shows the requested model
    controls = page.evaluate(_POPOVER_CONTROLS_JS) or []
    trigger = None
    for c in controls:
        text = c['text']
        if any(_normalize_text(name) in text for name in FLOW_MODEL_CHOICES):
            trigger = c
            break
    if trigger and desired_n in trigger['text']:
        logger.info(f"Flow model set to '{desired}'")
        return True
    logger.warning(f"Flow model switch did not verify (chip shows '{trigger['text'] if trigger else '?'}')")
    return True  # proceed anyway; wrong model still generates an image


def _select_outputs(page, outputs: str) -> bool:
    desired = (outputs or getattr(config, 'FLOW_IMAGE_OUTPUTS', 'x1')).strip().lower()
    if desired not in FLOW_OUTPUT_CHOICES:
        logger.warning(f"Outputs '{outputs}' invalid; using x1")
        desired = "x1"

    controls = page.evaluate(_POPOVER_CONTROLS_JS) or []
    target = _find_control(controls, lambda c: c['text'] == desired)
    if target is None:
        logger.debug(f"Outputs button '{desired}' not found (may match via regex scan)")
        # Fallback: any control matching \bx[1-4]\b
        target = _find_control(controls, lambda c: re.fullmatch(r'x[1-4]', c['text'] or '') is not None)
    if target is None:
        logger.warning("Outputs controls not found in popover")
        return False
    if _selected_hint(target):
        logger.info(f"Flow outputs already {desired}; skipping")
        return True
    logger.info(f"Setting Flow outputs: {desired}")
    if not _click_popover_button(page, target):
        return False
    time.sleep(1)
    return True


def _apply_image_settings(page, aspect_ratio: Optional[str], model: Optional[str], outputs: Optional[str]) -> None:
    """Open the settings popover and align Image-mode settings with the
    request. Settings already showing the requested value are never clicked."""
    if not _open_settings_popover(page):
        logger.warning("Could not open Flow settings popover; using project defaults "
                       "(aspect ratio/model may differ from request)")
        return

    try:
        _log_agent_state(page)
        controls = page.evaluate(_POPOVER_CONTROLS_JS) or []
        _select_media_type_image(page, controls)
        _select_aspect_ratio(page, aspect_ratio)
        _select_model(page, model)
        _select_outputs(page, outputs)
    except Exception as e:
        logger.warning(f"Error applying Flow settings: {e}")
    finally:
        _close_settings_popover(page)


# ── Reference image (ingredient) upload ──────────────────────────────────────

def _upload_reference_images(page, ref_paths: List[str]) -> bool:
    """Upload reference images as Flow ingredients via the '+' button in the
    prompt bar. Returns True when every image uploaded (or none requested)."""
    if not ref_paths:
        return True

    for ref_path in ref_paths:
        if not ref_path or not os.path.exists(ref_path):
            logger.error(f"Reference image not found: {ref_path}")
            return False
        uploaded = False
        try:
            logger.info(f"Uploading reference image: {ref_path}")
            # 1. Click the '+' (add ingredients) button in the prompt bar
            add_js = r"""() => {
              const norm = (s) => (s || '').replace(/[^\x00-\x7F]+/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
              const buttons = Array.from(document.querySelectorAll('button, div[role="button"]'));
              const cands = buttons.filter(b => {
                if (!b.offsetParent) return false;
                const aria = norm(b.getAttribute('aria-label') || '');
                const t = norm(b.textContent);
                if (aria.includes('ingredient') || aria.includes('upload')) return true;
                return t === '+' || t === 'add';
              });
              if (!cands.length) return false;
              cands[cands.length - 1].setAttribute('data-avf-click', '1');
              return true;
            }"""
            if page.evaluate(add_js):
                _real_click_marked(page)
            time.sleep(2)

            # 2a. A file chooser may open directly, or via an upload menu item
            menu_js = r"""() => {
              const norm = (s) => (s || '').replace(/[^\x00-\x7F]+/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
              const items = Array.from(document.querySelectorAll('[role="menuitem"], button, div[role="button"], li'));
              const match = items.filter(e => e.offsetParent && /upload|ingredient|add (media|file|image|photo)/.test(norm(e.textContent) + ' ' + norm(e.getAttribute('aria-label') || '')));
              if (!match.length) return false;
              match[0].setAttribute('data-avf-click', '1');
              return true;
            }"""
            try:
                with page.expect_file_chooser(timeout=8000) as fc_info:
                    if page.evaluate(menu_js):
                        _real_click_marked(page)
                file_chooser = fc_info.value
                file_chooser.set_files(ref_path)
                uploaded = True
            except Exception:
                # 2b. Direct input fallback (hidden file inputs)
                try:
                    page.set_input_files('input[type="file"]', ref_path)
                    uploaded = True
                except Exception as e:
                    logger.debug(f"Direct file input upload failed: {e}")

            if uploaded:
                time.sleep(4)
                # Flow may show a crop/confirm dialog for uploaded ingredients
                confirm_js = r"""() => {
                  const norm = (s) => (s || '').replace(/[^\x00-\x7F]+/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
                  const dlg = document.querySelector('[role="dialog"], dialog');
                  if (!dlg) return false;
                  const match = Array.from(dlg.querySelectorAll('button')).filter(b => {
                    const t = norm(b.textContent);
                    return ['done', 'save', 'add', 'confirm', 'use image'].includes(t);
                  });
                  if (!match.length) return false;
                  match[match.length - 1].setAttribute('data-avf-click', '1');
                  return true;
                }"""
                try:
                    if page.evaluate(confirm_js):
                        _real_click_marked(page)
                        time.sleep(2)
                except Exception:
                    pass
                logger.info(f"Reference image uploaded: {ref_path}")
        except Exception as e:
            logger.error(f"Failed to upload reference image {ref_path}: {e}")
            uploaded = False

        if not uploaded:
            logger.error(f"ABORTING: mandatory reference image {ref_path} failed to upload")
            return False

    # Wait for ingredient thumbnails to attach to the prompt
    try:
        page.wait_for_selector('div[contenteditable="true"] img, [role="dialog"] img', timeout=15000)
        time.sleep(2)
    except Exception:
        logger.warning("Ingredient thumbnail preview not detected; proceeding anyway")
    return True


# ── Prompt + submit + completion ─────────────────────────────────────────────

def _inject_prompt(page, input_element, prompt: str) -> bool:
    """Type the prompt into Flow's ProseMirror editor (focus, select-all,
    insert). Playwright's actionability click can time out on the prompt bar,
    so a JS focus fallback keeps the flow alive."""
    min_chars = max(10, len(prompt) // 2)
    try:
        input_element.scroll_into_view_if_needed()
        try:
            input_element.click(timeout=8000)
        except Exception as e:
            logger.debug(f"Prompt box click timed out ({e}); focusing via JS")
            page.evaluate("(el) => el.focus()", input_element)
        time.sleep(0.4)
        page.keyboard.press('Control+A')
        page.keyboard.press('Delete')
        time.sleep(0.1)
        page.keyboard.insert_text(prompt)
        time.sleep(0.4)
        actual = (input_element.inner_text() or '').strip()
        if len(actual) >= min_chars:
            logger.info("Prompt injected via keyboard.insert_text()")
            return True
        logger.debug(f"insert_text left {len(actual)} chars; trying type()")
        page.keyboard.press('Control+A')
        page.keyboard.press('Delete')
        page.keyboard.type(prompt, delay=10)
        time.sleep(0.3)
        actual = (input_element.inner_text() or '').strip()
        if len(actual) >= min_chars:
            logger.info("Prompt injected via keyboard.type()")
            return True
    except Exception as e:
        logger.debug(f"Prompt injection failed: {e}")
    logger.error("All prompt injection attempts failed")
    return False


def _submit_prompt(page) -> bool:
    """Click the submit (arrow) button — aria-label 'Start generation'; falls
    back to Enter. The click goes through Playwright's real input pipeline
    (Flow ignores synthetic JS clicks)."""
    submit_js = r"""() => {
      const norm = (s) => (s || '').replace(/[^\x00-\x7F]+/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();
      const buttons = Array.from(document.querySelectorAll('button'));
      const enabled = buttons.filter(b => b.offsetParent && !b.disabled);
      // 1. Arrow-forward icon button (the round submit arrow)
      let match = enabled.filter(b => (b.querySelector('i, span, mat-icon, svg')?.textContent || '').toLowerCase().includes('arrow_forward')
                                     || norm(b.getAttribute('aria-label')).includes('arrow forward'));
      // 2. Generate/Start-generation labelled buttons
      if (!match.length) match = enabled.filter(b => {
        const hay = norm(b.textContent) + ' ' + norm(b.getAttribute('aria-label'));
        return /generate|start generation|^send$|submit/.test(hay) && !hay.includes('project');
      });
      if (!match.length) return false;
      match[match.length - 1].setAttribute('data-avf-click', '1');
      return true;
    }"""
    try:
        if page.evaluate(submit_js) and _real_click_marked(page):
            logger.info("Clicked Flow submit button")
            return True
    except Exception as e:
        logger.debug(f"Submit button click failed: {e}")
    try:
        page.keyboard.press('Enter')
        logger.info("Submitted prompt with Enter key")
        return True
    except Exception:
        return False


# Snapshot of currently rendered generated images, used to detect the NEW
# tile after submitting. Prioritizes Flow's alt label ('Generated image'),
# falls back to large hosted images.
_SNAPSHOT_JS = r"""() => {
  // Generated tiles are large <img> elements (alt 'Tile displaying a user's
  // image', src https://flow.google.com/asb/...). Icons/avatars are tiny.
  const imgs = Array.from(document.querySelectorAll('img'));
  return imgs
    .filter(im => {
      const src = im.src || '';
      if (!src.startsWith('http')) return false;
      return im.naturalWidth >= 200;
    })
    .map(im => ({src: im.src, w: im.naturalWidth}));
}"""

# Locator for freshly rendered images (runs repeatedly until it finds one
# whose src was NOT in the pre-submit snapshot and which is done generating:
# no percentage text still counting inside its tile). Returns ALL matching
# candidates plus their tile labels — with FLOW_PROJECT_CONCURRENCY > 1,
# several prompts generate side by side and the tile label (derived from the
# prompt) is what attributes each tile to its own worker.
_NEW_IMAGE_JS = r"""(knownSrcs) => {
  const norm = (s) => (s || '').split('?')[0];
  const known = new Set((knownSrcs || []).map(x => norm(typeof x === 'string' ? x : x.src)));
  const pctRe = /^\d+\s*%$/;
  const out = [];
  const imgs = Array.from(document.querySelectorAll('img'));
  for (const im of imgs.reverse()) {
    const src = im.src || '';
    if (!src.startsWith('http') || known.has(norm(src))) continue;
    if (im.naturalWidth < 200) continue;
    // Walk up to the tile: check for an active progress indicator and grab
    // the tile label (Flow derives it from the generation prompt).
    let tile = im;
    let busy = false;
    let label = '';
    for (let i = 0; i < 8 && tile; i++) {
      const pct = Array.from(tile.querySelectorAll('span, div')).some(e => {
        const t = (e.textContent || '').trim();
        if (!pctRe.test(t)) return false;
        const r = e.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && parseInt(t) < 100;
      });
      const cls = String(tile.className || '').toLowerCase();
      if (!label) {
        const aria = tile.getAttribute && tile.getAttribute('aria-label');
        if (aria && aria.length > 3) label = aria;
      }
      if (pct || /shimmer|skeleton|spinner|loading/.test(cls)) { busy = true; break; }
      tile = tile.parentElement;
    }
    if (busy) continue;
    out.push({src: src, w: im.naturalWidth, h: im.naturalHeight, label: label});
  }
  return out;
}"""


def _normalize_words(text: str) -> List[str]:
    """Lowercase word tokens for fuzzy tile-label matching."""
    if not text:
        return []
    return [w for w in re.sub(r'[^a-z0-9]+', ' ', text.lower()).split() if len(w) > 1]


def _score_candidate(candidate: dict, prompt: str) -> float:
    """Fraction of the tile label's words that appear in our prompt. Flow
    shortens tile labels to a prompt fragment, so the correct tile scores
    near 1.0 while another shot's tile shares almost no words."""
    label_words = _normalize_words(candidate.get('label') or '')
    if not label_words:
        return 0.0
    prompt_words = set(_normalize_words(prompt))
    if not prompt_words:
        return 0.0
    hits = sum(1 for w in label_words if w in prompt_words)
    return hits / len(label_words)


def _pick_own_candidate(candidates: List[dict], prompt: str) -> Optional[dict]:
    """Best prompt-matching candidate, or None when nothing matches well
    enough (it is probably another worker's tile — keep waiting)."""
    if not candidates:
        return None
    scored = sorted(
        ((_score_candidate(c, prompt), c) for c in candidates),
        key=lambda pair: pair[0], reverse=True)
    best_score, best = scored[0]
    if best_score < 0.5:
        logger.debug(f"Best new-tile score {best_score:.2f} too low "
                     f"(label={best.get('label')!r}); likely another worker's tile")
        return None
    return best


def _wait_for_new_image(page, known_srcs: List[dict], prompt: str, timeout_s: int) -> Optional[dict]:
    """Poll until OUR image (tile label matching our prompt) has rendered.
    Falls back to the newest candidate near the end of the timeout."""
    logger.info(f"Waiting up to {timeout_s}s for Flow to generate the image...")
    deadline = time.time() + timeout_s
    stable_src = None
    stable_count = 0
    while time.time() < deadline:
        if page.is_closed():
            return None
        try:
            candidates = page.evaluate(_NEW_IMAGE_JS, known_srcs)
            chosen = _pick_own_candidate(candidates, prompt)
            if chosen:
                if chosen['src'] == stable_src:
                    stable_count += 1
                else:
                    stable_src = chosen['src']
                    stable_count = 1
                if stable_count >= 2:  # same candidate across two consecutive polls
                    score = _score_candidate(chosen, prompt)
                    logger.info(f"New Flow image detected ({chosen['w']}x{chosen['h']}, "
                                f"prompt-match {score:.2f}, label={chosen.get('label')!r})")
                    return chosen
            else:
                stable_src = None
                stable_count = 0
                if candidates:
                    logger.debug(f"{len(candidates)} new tile(s) visible but none matches our prompt yet")
        except Exception as e:
            logger.debug(f"New-image poll error (will retry): {e}")
        time.sleep(3)
    # Timeout fallback: accept the newest candidate rather than nothing
    try:
        candidates = page.evaluate(_NEW_IMAGE_JS, known_srcs) or []
        if candidates:
            chosen = candidates[0]
            logger.warning(f"Timed out waiting for a prompt-matching tile; "
                           f"falling back to newest candidate (label={chosen.get('label')!r})")
            return chosen
    except Exception:
        pass
    logger.warning(f"Flow image generation timed out after {timeout_s}s")
    return None


def _ensure_png(path: str) -> str:
    """Convert a downloaded image to PNG in place when it isn't one (Flow
    serves webp). Falls back to the original file if conversion is
    unavailable."""
    try:
        with open(path, 'rb') as f:
            magic = f.read(8)
        if magic.startswith(b'\x89PNG'):
            return path
        import cv2
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None:
            logger.warning(f"Could not decode {path} for PNG conversion; keeping original")
            return path
        png_path = os.path.splitext(path)[0] + '.png'
        if png_path != path and os.path.exists(png_path):
            os.remove(png_path)
        cv2.imwrite(png_path, img)
        if png_path != path:
            os.remove(path)
        logger.debug(f"Converted {os.path.basename(path)} to PNG")
        return png_path
    except Exception as e:
        logger.warning(f"PNG conversion failed for {path}: {e}")
        return path


def _download_new_image(page, image_info: dict, output_path: str) -> Optional[str]:
    """Download the generated image: native download action first (tile
    toolbar / More-options menu), then an authenticated fetch of the tile's
    same-origin source URL, then element screenshot. Non-PNG results (Flow
    serves webp) are converted to PNG."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    target_src = image_info['src'].split('?')[0]

    # JS: mark the download control of the tile that owns srcPrefix. Looks
    # for a direct download button, then a 'Download' item under the tile's
    # 'More options' menu (hover-only toolbar).
    _MARK_DOWNLOAD_JS = r"""(srcPrefix) => {
      const imgs = Array.from(document.querySelectorAll('img')).reverse();
      const img = imgs.find(im => (im.src || '').split('?')[0] === srcPrefix);
      if (!img) return 'no-img';
      let tile = img;
      for (let i = 0; i < 8 && tile; i++) {
        const btns = Array.from(tile.querySelectorAll('button'));
        const direct = btns.find(b => /download/i.test((b.getAttribute('aria-label') || '') + ' ' + (b.textContent || '')));
        if (direct) { direct.setAttribute('data-avf-click', '1'); return 'direct'; }
        const more = btns.find(b => (b.getAttribute('aria-label') || '') === 'More options');
        if (more) { more.setAttribute('data-avf-click', '1'); return 'more'; }
        tile = tile.parentElement;
      }
      return 'no-button';
    }"""

    _MARK_MENU_DOWNLOAD_JS = r"""() => {
      const items = Array.from(document.querySelectorAll('[role="menuitem"], .cdk-overlay-container button, [role="menu"] button'))
        .filter(e => e.offsetParent);
      const hit = items.find(e => /download/i.test((e.textContent || '') + ' ' + (e.getAttribute('aria-label') || '')));
      if (!hit) return false;
      hit.setAttribute('data-avf-click', '1');
      return true;
    }"""

    # ── Strategy 1: hover the tile (reveals the toolbar) and use the native
    #    download action, capturing the browser download. ───────────────────
    try:
        handle = page.evaluate_handle("""(srcPrefix) => {
          const imgs = Array.from(document.querySelectorAll('img')).reverse();
          return imgs.find(im => (im.src || '').split('?')[0] === srcPrefix) || null;
        }""", target_src)
        el = handle.as_element()
        if el:
            el.scroll_into_view_if_needed()
            el.hover(timeout=5000)
            time.sleep(1.2)
            kind = page.evaluate(_MARK_DOWNLOAD_JS, target_src)
            logger.debug(f"Download strategy-1 scan: {kind}")
            if kind in ('direct', 'more'):
                with page.expect_download(timeout=20000) as dl_info:
                    _real_click_marked(page, timeout_ms=6000)
                    if kind == 'more':
                        time.sleep(1.5)
                        if page.evaluate(_MARK_MENU_DOWNLOAD_JS):
                            _real_click_marked(page, timeout_ms=6000)
                        else:
                            page.keyboard.press("Escape")
                            raise RuntimeError("no download item in More options menu")
                download = dl_info.value
                download.save_as(output_path)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                    logger.info(f"Downloaded via Flow download action: {output_path}")
                    return _ensure_png(output_path)
    except Exception as e:
        logger.debug(f"Native download failed: {e}")
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass

    # ── Strategy 2: authenticated fetch of the image source ────────────────
    try:
        src = image_info['src']
        if src.startswith('blob:'):
            # In-page extraction: fetch the blob inside the page and convert
            # to a data URL (blob: URLs are not reachable from Python).
            data_url = page.evaluate("""async (blobUrl) => {
                try {
                    const response = await fetch(blobUrl);
                    const blob = await response.blob();
                    return await new Promise((resolve, reject) => {
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.onerror = reject;
                        reader.readAsDataURL(blob);
                    });
                } catch (e) { return null; }
            }""", src)
            if data_url and ',' in data_url:
                import base64
                _, data = data_url.split(',', 1)
                image_bytes = base64.b64decode(data)
                if len(image_bytes) > 10000:
                    with open(output_path, 'wb') as f:
                        f.write(image_bytes)
                    logger.info(f"Extracted blob image in-page: {output_path} ({len(image_bytes):,} bytes)")
                    return _ensure_png(output_path)
            logger.debug("In-page blob extraction failed")
        else:
            # googleusercontent thumbs carry size suffixes (=s960 / =w..-h..);
            # =s0 requests the original resolution. Flow's own /asb/ URLs are
            # same-origin signed links that fetch directly.
            full = re.sub(r'=(s\d+|w\d+-h\d+|w\d+)(-[a-z]+)*$', '=s0', src)
            response = page.request.get(full, timeout=60000)
            if response.status == 200:
                body = response.body()
                ctype = (response.headers or {}).get('content-type', '')
                if len(body) > 10000 and ('image' in ctype or not ctype):
                    with open(output_path, 'wb') as f:
                        f.write(body)
                    logger.info(f"Downloaded via authenticated fetch: {output_path} ({len(body):,} bytes)")
                    return _ensure_png(output_path)
                logger.debug(f"Fetch body unusable (type={ctype}, size={len(body)})")
            else:
                logger.debug(f"Authenticated fetch failed: HTTP {response.status}")
    except Exception as e:
        logger.debug(f"Authenticated fetch error: {e}")

    # ── Strategy 3: element screenshot (lossy last resort) ─────────────────
    try:
        handle = page.evaluate_handle("""(srcPrefix) => {
          const imgs = Array.from(document.querySelectorAll('img')).reverse();
          return imgs.find(im => (im.src || '').split('?')[0] === srcPrefix) || null;
        }""", image_info['src'].split('?')[0])
        el = handle.as_element()
        if el:
            el.scroll_into_view_if_needed()
            el.screenshot(path=output_path)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                logger.warning(f"Saved element screenshot fallback: {output_path}")
                return output_path
    except Exception as e:
        logger.debug(f"Element screenshot fallback failed: {e}")

    return None


def _snapshot_images(page) -> List[dict]:
    try:
        return page.evaluate(_SNAPSHOT_JS) or []
    except Exception:
        return []


def run(prompt: str, output_path: str, aspect_ratio: str = None, project_title: str = None,
        reference_image_path: List[str] = None, profile_dir: str = None,
        model: str = None, outputs: str = None) -> Optional[str]:
    """Main entry point — run Playwright and generate one image on Flow."""
    from playwright.sync_api import sync_playwright

    timeout = getattr(config, 'FLOWWEB_TIMEOUT', 300)
    workspace_key = project_title or DEFAULT_WORKSPACE_KEY
    logger.info(f"Generating image (FlowWeb subprocess): {output_path}")
    logger.debug(f"  Prompt: {prompt[:100]}...")
    logger.debug(f"  Aspect ratio: {aspect_ratio or config.IMAGE_ASPECT_RATIO} | model: {model or config.FLOW_IMAGE_MODEL} | outputs: {outputs or config.FLOW_IMAGE_OUTPUTS}")
    logger.info(f"Flow workspace: '{workspace_key}'")

    _acquire_project_lock(workspace_key)

    with sync_playwright() as playwright_instance:
        context = _create_browser_context(playwright_instance, profile_dir)
        page = context.pages[0] if context.pages else context.new_page()
        known: List[dict] = []
        try:
            # ── Serialized phase (per workspace): project lookup/creation, the
            # settings popover and prompt submit must not race between this
            # workspace's parallel workers — Flow applies settings to future
            # outputs, and a first run would otherwise create two projects.
            _acquire_settings_lock(workspace_key)
            try:
                if not _ensure_flow_project(page, workspace_key):
                    logger.error("Could not open or create a Flow project")
                    diag = output_path.replace('.png', '_project_diagnostic.png')
                    try:
                        page.screenshot(path=diag, full_page=False)
                        logger.info(f"Diagnostic screenshot saved: {diag}")
                    except Exception:
                        pass
                    return None

                _dismiss_overlays(page)
                _apply_image_settings(page, aspect_ratio, model, outputs)

                refs = [r for r in (reference_image_path or []) if r]
                if not _upload_reference_images(page, refs):
                    return None

                # Locate the prompt box and send the prompt
                input_element = _wait_for_prompt_box(page, 20)
                if not input_element:
                    logger.error("Could not find the Flow prompt box")
                    return None

                known = _snapshot_images(page)
                logger.info(f"Pre-submit snapshot: {len(known)} existing generated image(s)")

                if not _inject_prompt(page, input_element, prompt):
                    return None
                time.sleep(0.5)

                if not _submit_prompt(page):
                    logger.error("Could not submit the prompt")
                    return None
            finally:
                # End the serialized phase; generation + download run in
                # parallel with this workspace's other workers now.
                _release_settings_lock(workspace_key)

            image_info = _wait_for_new_image(page, known, prompt, timeout)
            if not image_info:
                diag = output_path.replace('.png', '_diagnostic.png')
                try:
                    page.screenshot(path=diag, full_page=False)
                    logger.info(f"Diagnostic screenshot saved: {diag}")
                except Exception:
                    pass
                logger.error("No new Flow image was generated")
                return None

            time.sleep(3)  # let the tile settle / full-res URL attach
            result = _download_new_image(page, image_info, output_path)
            if result:
                size = os.path.getsize(result)
                logger.info(f"Generated (FlowWeb): {result} ({size:,} bytes)")
                return result

            diag = output_path.replace('.png', '_download_diagnostic.png')
            try:
                page.screenshot(path=diag, full_page=False)
                logger.info(f"Download failure diagnostic screenshot saved: {diag}")
            except Exception:
                pass
            logger.error("Failed to download the generated Flow image")
            return None

        finally:
            _release_project_lock(workspace_key)
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
        import logging as _logging
        from logging.handlers import RotatingFileHandler
        _log_dir = getattr(config, 'LOG_DIR', 'logs')
        os.makedirs(_log_dir, exist_ok=True)
        _fh = RotatingFileHandler(
            os.path.join(_log_dir, 'flowweb_image_subprocess.log'),
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
    parser.add_argument("prompt")
    parser.add_argument("output_path")
    parser.add_argument("--aspect-ratio", default=None)
    parser.add_argument("--project-title", default=None)
    parser.add_argument("--reference-image", action="append", default=[])
    parser.add_argument("--profile-dir", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--outputs", default=None)
    args = parser.parse_args()

    result = run(args.prompt, args.output_path, args.aspect_ratio, args.project_title,
                 args.reference_image, args.profile_dir, args.model, args.outputs)
    if result:
        print(f"SUCCESS:{result}")
        sys.exit(0)
    else:
        print("FAILED")
        sys.exit(1)
