"""
GeminiWeb Music Subprocess - Browser-based music generation via gemini.google.com

Runs as a standalone module (`python -m core.geminiweb_music_subprocess`) to isolate
Playwright's asyncio event loop from the caller's event loop ("Event loop is closed"
errors on Windows). Sends a "Create a music: ..." prompt to the Gemini web UI and
downloads the returned audio attachment.

Reuses the stable browser/chat/download helpers from core.geminiweb_video_subprocess;
the music-specific parts are the prompt composition, the audio-response wait and the
audio attachment download.
"""
import os
import sys
import time
import shutil
import subprocess
from typing import Optional

import config
from core.logger_config import get_logger

# Reuse the stable helpers from the video subprocess (chat registry/locks,
# browser context, mode setter, text injection). Importing between subprocess
# modules is safe - both run as `python -m core.*` from the project root.
from core.geminiweb_video_subprocess import (
    _create_browser_context,
    _registry_get_chat_url,
    _registry_set_chat_url,
    _open_project_chat_by_url,
    _ensure_project_chat,
    _rename_current_chat,
    _set_gemini_mode,
    _inject_text_into_input,
    _acquire_chat_lock,
    _release_chat_lock,
)
import core.geminiweb_video_subprocess as _vsub

logger = get_logger(__name__)

# Music generation can be slower than chat responses; allow a generous wait.
_AUDIO_RESPONSE_TIMEOUT = 600  # seconds


# Locate the response content following OUR prompt (same collapsed-query needle
# strategy as the video subprocess, but without requiring a <video> element).
_LOCATE_CONTAINER_JS = """(prompt) => {
  const norm = (s) => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
  const full = norm(prompt);
  if (!full) return null;
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
    if (el.tagName.toLowerCase() !== 'user-query') return el;
  }
  return null;
}"""

# Ready check: the response following OUR prompt exposes an audio element or a
# download affordance (file chip / download button / anchor with download attr).
_LOCATE_READY_JS = """(prompt) => {
  const norm = (s) => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
  const full = norm(prompt);
  if (!full) return false;
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
    if (el.querySelector('audio')) return true;
    if (el.querySelector('a[download]')) return true;
    if (el.querySelector('button[aria-label*="ownload" i]')) return true;
    if (el.querySelector('[data-test-id*="audio"], audio-player, generated-audio')) return true;
  }
  return false;
}"""


def _wait_for_own_audio_response(page, prompt_text: str, timeout_s: float = _AUDIO_RESPONSE_TIMEOUT) -> bool:
    """Wait until the response following OUR prompt exposes an audio affordance."""
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
            logger.debug(f"Own audio response poll error (will retry): {e}")
        time.sleep(5)
    return False


def _locate_own_response_container(page, prompt_text: str):
    """Return an ElementHandle for the response content following our prompt."""
    try:
        handle = page.evaluate_handle(_LOCATE_CONTAINER_JS, prompt_text)
        return handle.as_element()
    except Exception as e:
        logger.debug(f"Prompt-based audio locate failed: {e}")
        return None


def _try_download_audio(page, output_path: str, prompt_text: str = None) -> Optional[str]:
    """Download the audio attachment from the response following OUR prompt.

    Saves the raw download next to output_path as <output>.tmp - the caller
    converts it to the final mp3 with ffmpeg.
    """
    download_button_selectors = [
        'button[aria-label="Download audio"]',
        'audio-player button[aria-label*="ownload" i]',
        'generated-audio button[aria-label*="ownload" i]',
        'gem-icon-button[fonticonname="download"] button',
        'button[aria-label="Download"]',
        'button.download-button',
        'button[jsname][aria-label*="ownload" i]',
        'a[download]',
    ]

    tmp_path = output_path + '.tmp'
    if os.path.exists(tmp_path):
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    def _click_visible_download_button(scope=None) -> Optional[str]:
        for btn_sel in download_button_selectors:
            try:
                if scope is not None:
                    btns = scope.query_selector_all(btn_sel)
                else:
                    btns = page.query_selector_all(btn_sel)
                if btns:
                    for btn in reversed(btns):
                        if btn.is_visible():
                            logger.info(f"Clicking download button: {btn_sel}")
                            with page.expect_download(timeout=300000) as dl_info:
                                btn.click()
                            dl = dl_info.value
                            dl.save_as(tmp_path)
                            logger.info(f"Audio download saved: {tmp_path}")
                            return tmp_path
            except Exception:
                continue
        return None

    try:
        # Scope to the response following OUR prompt when known (parallel
        # workers share the project chat) - refuse page-wide fallback to avoid
        # grabbing a neighbour's audio.
        own_container = None
        if prompt_text:
            own_container = _locate_own_response_container(page, prompt_text)
            if own_container is not None:
                logger.info("Located own audio response by prompt text")

        if own_container is not None:
            downloaded = _click_visible_download_button(scope=own_container)
            if downloaded:
                return downloaded
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
                "of page-wide search (wrong audio is worse than a retry)")
            return None

        # No prompt text available - page-wide search (last resort).
        downloaded = _click_visible_download_button()
        if downloaded:
            return downloaded

        # Fallback: fetch an <audio> element's src directly.
        audios = page.query_selector_all('message-content audio, audio[src]')
        if audios:
            audio = audios[-1]
            src = audio.get_attribute('src')
            if src:
                logger.info(f"Found audio src: {src[:60]}...")
                if src.startswith('blob:'):
                    data_url = page.evaluate("""
                        async (blobUrl) => {
                            return new Promise((resolve, reject) => {
                                const xhr = new XMLHttpRequest();
                                xhr.open('GET', blobUrl, true);
                                xhr.responseType = 'blob';
                                xhr.onload = function(e) {
                                    if (this.status == 200) {
                                        const reader = new FileReader();
                                        reader.onloadend = () => resolve(reader.result);
                                        reader.readAsDataURL(this.response);
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
                        import base64
                        _, data = data_url.split(',', 1)
                        with open(tmp_path, 'wb') as f:
                            f.write(base64.b64decode(data))
                        logger.info(f"Saved blob audio: {tmp_path}")
                        return tmp_path
                elif src.startswith('http'):
                    response = page.request.get(src)
                    if response.ok:
                        with open(tmp_path, 'wb') as f:
                            f.write(response.body())
                        logger.info(f"Saved audio via fetch: {tmp_path}")
                        return tmp_path

    except Exception as e:
        logger.error(f"Audio download failed: {e}")

    return None


def _convert_to_mp3(source_path: str, output_path: str) -> Optional[str]:
    """Convert a downloaded audio/video file to mp3 (no-op when already mp3)."""
    ext = os.path.splitext(source_path)[1].lower()

    if ext == '.mp3':
        if os.path.abspath(source_path) != os.path.abspath(output_path):
            os.replace(source_path, output_path)
        return output_path

    ffmpeg = subprocess.run(
        [shutil.which("ffmpeg") or "ffmpeg", "-y", "-loglevel", "error",
         "-i", source_path, "-vn", "-acodec", "libmp3lame", "-q:a", "2", output_path],
        capture_output=True, timeout=600)
    if ffmpeg.returncode != 0 or not os.path.isfile(output_path):
        logger.error(f"ffmpeg conversion failed: {ffmpeg.stderr.decode(errors='ignore')[:500]}")
        return None
    try:
        os.remove(source_path)
    except Exception:
        pass
    return output_path


def run(music_prompt: str, output_path: str, project_title: str = None,
        profile_dir: str = None, gemini_mode: str = None) -> Optional[str]:
    """Main entry point - run Playwright and generate music."""
    from playwright.sync_api import sync_playwright

    gemini_url = getattr(config, 'GEMINIWEB_URL', 'https://gemini.google.com/app')
    timeout = getattr(config, 'GEMINIWEB_TIMEOUT', 120)

    # The prompt sent to Gemini always starts with the configured music prefix.
    prefix = getattr(config, 'MUSIC_GEMINIWEB_PROMPT_PREFIX', 'Create a music:')
    full_prompt = f"{prefix} {music_prompt}".strip()

    logger.info(f"Generating music (GeminiWeb subprocess): {output_path}")
    logger.debug(f"  Prompt: {full_prompt[:120]}...")

    chat_lock_path = None
    if project_title:
        chat_lock_path = _acquire_chat_lock(project_title)
        if not chat_lock_path:
            logger.warning(
                "Chat lock wait timed out; proceeding unlocked "
                "(overlapping generations in one chat risk response crosstalk)")

    with sync_playwright() as playwright_instance:
        context = _create_browser_context(playwright_instance, profile_dir)
        page = context.new_page()
        # Gemini calls window.close() after its download interactions, which
        # kills the whole automation browser mid-flow - neuter it.
        page.add_init_script("window.close = () => {};")

        try:
            # Fast path: chat URL known from the registry - go straight to the chat.
            used_existing_chat = False
            saved_url = _registry_get_chat_url(project_title) if project_title else None
            if saved_url and _open_project_chat_by_url(page, saved_url):
                logger.info("Opened registered project chat directly (skipped app home)")
                used_existing_chat = True
                _set_gemini_mode(page, gemini_mode)
            else:
                logger.info(f"Navigating to {gemini_url}")
                page.goto(gemini_url, wait_until='domcontentloaded', timeout=timeout * 1000)
                time.sleep(5)

                _set_gemini_mode(page, gemini_mode)

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

            # Find the chat input box
            input_selectors = [
                'div.ql-editor[contenteditable="true"]',
                'div.ql-editor',
                'div[aria-label="Enter a prompt for Gemini"]',
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

            # Inject the prompt and submit
            injected = _inject_text_into_input(page, input_element, full_prompt)
            if not injected:
                logger.error("All prompt injection attempts failed")
                return None

            time.sleep(1.0)

            sent = False
            for selector in [
                'button[aria-label="Send message"]',
                'button.send-button',
                'button[data-test-id="send-button"]',
                'button[aria-label="Send"]',
            ]:
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

            logger.info("Request submitted, waiting for music generation...")

            # Wait for the audio response following OUR prompt
            ready = _wait_for_own_audio_response(page, full_prompt)
            if not ready:
                logger.warning("Timed out waiting for an audio response; "
                               "attempting download anyway")

            # Name the chat after the project so future runs reuse it
            if project_title and not used_existing_chat:
                if _rename_current_chat(page, project_title):
                    _registry_set_chat_url(project_title, page.url)

            # Download the audio attachment (raw, possibly non-mp3 container)
            result = _try_download_audio(page, output_path, prompt_text=full_prompt)

            if not result:
                logger.warning("First download attempt failed; retrying once after 20s")
                time.sleep(20)
                result = _try_download_audio(page, output_path, prompt_text=full_prompt)

            if not result or not os.path.exists(result):
                logger.error("Failed to download the generated audio.")
                try:
                    diag_path = output_path.replace('.mp4', '_diagnostic.png').replace('.mp3', '_diagnostic.png')
                    page.screenshot(path=diag_path, full_page=False)
                    logger.info(f"Diagnostic screenshot saved: {diag_path}")
                except Exception:
                    pass
                return None

            # Normalize to mp3 (Gemini may deliver wav/ogg/mp4 containers)
            final_path = _convert_to_mp3(result, output_path)
            if not final_path:
                return None

            file_size = os.path.getsize(final_path)
            logger.info(f"Generated (GeminiWeb Music): {final_path} ({file_size:,} bytes)")
            return final_path

        finally:
            # Never leave the per-project chat lock held: drain any leaked
            # inner acquisitions so the lock file is always removed.
            if project_title:
                for _ in range(10):
                    if getattr(_vsub, '_HELD_CHAT_LOCK', None) != project_title:
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
        import logging as _logging
        from logging.handlers import RotatingFileHandler
        _log_dir = getattr(config, 'LOG_DIR', 'logs')
        os.makedirs(_log_dir, exist_ok=True)
        _fh = RotatingFileHandler(
            os.path.join(_log_dir, 'geminiweb_music_subprocess.log'),
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
    parser.add_argument("music_prompt")
    parser.add_argument("output_path")
    parser.add_argument("project_title", nargs='?', default=None)
    parser.add_argument("--profile-dir", default=None)
    parser.add_argument("--gemini-mode", default=None)
    args = parser.parse_args()

    result = run(args.music_prompt, args.output_path, args.project_title, args.profile_dir, args.gemini_mode)
    if result:
        print(f"SUCCESS:{result}")
        sys.exit(0)
    else:
        print("FAILED")
        sys.exit(1)
