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


def _create_browser_context(playwright_instance):
    """Create a persistent browser context with the configured browser."""
    chrome_profile = getattr(config, 'GEMINIWEB_CHROME_PROFILE', None)
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
                '--no-first-run',
                '--no-default-browser-check',
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
        )
        return context
    except Exception as e:
        logger.error(f"Failed to launch browser {browser_type_name}: {e}")
        raise


def _ensure_session_chat(page, session_title: str):
    """Ensure we are in a chat named after the session_title."""
    if not session_title:
        return

    logger.info(f"Ensuring Gemini chat for session: '{session_title}'")
    try:
        sidebar_selectors = [
            f'a[aria-label*="{session_title}"]',
            f'div[role="button"]:has-text("{session_title}")',
            f'a:has-text("{session_title}")',
        ]
        
        for sel in sidebar_selectors:
            try:
                chat_link = page.query_selector(sel)
                if chat_link:
                    logger.info(f"Found existing chat: '{session_title}'. Clicking...")
                    chat_link.click()
                    time.sleep(3)
                    return
            except Exception:
                continue
                
        logger.info(f"No existing chat found for '{session_title}'. Using current/new chat.")
        new_chat_btn = page.query_selector('a[href="/app"], button:has-text("New chat")')
        if new_chat_btn and not page.url.endswith('/app'):
            new_chat_btn.click()
            time.sleep(2)
    except Exception as e:
        logger.warning(f"Error while managing session chat: {e}")


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
    
    video_selectors = [
        'div[data-message-id] video',
        'div[data-message-id] .playable-media',
        'button.generated-video-button'
    ]
    
    while waited < timeout:
        # Check if the video element has appeared
        found_video = False
        for sel in video_selectors:
            try:
                el = page.query_selector(sel)
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


def _try_download_native(page, output_path: str) -> Optional[str]:
    """Download the latest generated video using native Playwright download."""
    
    video_container_selectors = [
        'generated-video video-player',
        'generated-video',
        'div[data-message-id] video',
        'div[data-message-id] .playable-media',
        'button.generated-video-button',
    ]

    download_button_selectors = [
        'button.download-button',
        'button[aria-label="Download video"]',
        'button[aria-label="Download"]',
        'button[jsname][aria-label*="ownload"]',
        'a[download]',
    ]

    def _do_hover_and_download(container, depth=0) -> Optional[str]:
        if not container or depth > 4:
            return None
            
        try:
            # Scroll into view and hover to trigger the toolbar
            container.scroll_into_view_if_needed()
            time.sleep(1)
            container.hover()
            time.sleep(2.0)  # Wait for animation
            
            # Check if any download button is now visible
            for btn_sel in download_button_selectors:
                try:
                    btns = page.query_selector_all(btn_sel)
                    if btns:
                        # Test if any of these buttons are visible and click the last one
                        for btn in reversed(btns):
                            if btn.is_visible():
                                logger.info(f"Clicking download button: {btn_sel} (at DOM depth {depth})")
                                with page.expect_download(timeout=120000) as dl_info:
                                    btn.click()
                                dl = dl_info.value
                                dl.save_as(output_path)
                                logger.info(f"Native download saved: {output_path}")
                                return output_path
                except Exception as repr_e:
                    continue
                    
            logger.debug(f"No download button visible on hover at depth {depth}. Trying parent...")
            parent = container.evaluate_handle('el => el.parentElement')
            return _do_hover_and_download(parent, depth + 1)
            
        except Exception as e:
            logger.debug(f"Hover/download failed at depth {depth}: {e}")
            return None

    try:
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
        video_selector = 'generated-video video, video-player video, div[data-message-id] video'
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

def run(image_path: str, motion_prompt: str, output_path: str, session_title: str = None) -> Optional[str]:
    """Main entry point — run Playwright and generate a video."""
    from playwright.sync_api import sync_playwright

    gemini_url = getattr(config, 'GEMINIWEB_URL', 'https://gemini.google.com/app')

    logger.info(f"Generating video (GeminiWeb subprocess): {output_path}")
    logger.debug(f"  Prompt: {motion_prompt[:100]}...")
    logger.debug(f"  Reference Image: {image_path}")

    with sync_playwright() as playwright_instance:
        context = _create_browser_context(playwright_instance)
        page = context.new_page()

        try:
            logger.info(f"Navigating to {gemini_url}")
            page.goto(gemini_url, wait_until='domcontentloaded', timeout=60000)
            time.sleep(5)

            # ── Ensure correct chat ──────────────────────────────────────────
            if session_title:
                _ensure_session_chat(page, session_title)

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

            # ── Download the video ───────────────────────────────────────────
            # Try native download first
            result = _try_download_native(page, output_path)
            
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
    parser = argparse.ArgumentParser()
    parser.add_argument("image_path")
    parser.add_argument("motion_prompt")
    parser.add_argument("output_path")
    parser.add_argument("session_title", nargs='?', default=None)
    args = parser.parse_args()

    result = run(args.image_path, args.motion_prompt, args.output_path, args.session_title)
    if result:
        print(f"SUCCESS:{result}")
        sys.exit(0)
    else:
        print("FAILED")
        sys.exit(1)
