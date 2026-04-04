"""
GeminiWeb Subprocess Helper — standalone Playwright script.

This script is invoked as a subprocess by generate_image_geminiweb().
Running Playwright in a fresh, isolated Python process avoids all asyncio
event-loop conflicts with FastAPI/Uvicorn on Windows.

Usage:
    python -m core.geminiweb_subprocess <prompt> <output_path> [aspect_ratio]

Exit code 0 and prints the output path on success, exit code 1 on failure.

Techniques used:
- Prompt injection: direct fill() / evaluate() into the contenteditable
  input box, without touching the clipboard.
- Image download: Playwright native expect_download() triggered by clicking
  the generated image's download button (revealed by hover), with fallbacks
  to data-URI extraction and element screenshot.
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

# Calibrated Gemini alpha masks (48x48 and 96x96 PNGs base64 encoded)
# Used for high-precision reverse alpha-blending restoration.
_MASK_48_B64 = "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"
_MASK_96_B64 = "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"

def _get_mask(b64_str: str):
    import base64
    import numpy as np
    import cv2
    decoded = base64.b64decode(b64_str)
    nparr = np.frombuffer(decoded, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)


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
        if channel and channel not in valid_chromium_channels:
            logger.warning(f"Invalid chromium channel '{channel}', defaulting to None")
            channel = None

    logger.info(f"Using browser: {browser_type_name}, channel: {channel}, profile: {chrome_profile}")

    try:

        if browser_type_name == "chromium":
            launch_args = [
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-features=OptimizationGuideModelExecution,OptimizationGuideOnDeviceModel',
            ]
        else:
            launch_args = []
        
        context = browser_type.launch_persistent_context(
            user_data_dir=chrome_profile,
            headless=False,
            channel=channel if channel else None,
            args=launch_args,
            viewport={'width': 1280, 'height': 900},
            ignore_default_args=['--enable-automation'],
        )
        return context
    except Exception as e:
        logger.error(f"Failed to launch browser {browser_type_name}: {e}")
        raise


def _compose_prompt(image_prompt: str, aspect_ratio: str = None) -> str:
    """Compose the full prompt with aspect ratio instruction."""
    ar = aspect_ratio or getattr(config, 'IMAGE_ASPECT_RATIO', '16:9')
    ar_instruction = f" The aspect ratio should be {ar}."
    return f"Generate an image: {image_prompt}.{ar_instruction}"


def _ensure_project_chat(page, project_title: str):
    """
    Ensure we are in a chat named after the project_title.
    1. Look for existing chat in sidebar.
    2. If found, click it.
    3. If not, stay in new chat (or click 'New chat') and we'll rename it later.
    """
    if not project_title:
        return

    logger.info(f"Ensuring Gemini chat for project: '{project_title}'")
    
    try:
        # 1. Look for existing chat in sidebar
        # Sidebar items are usually <a> tags with 'aria-label' or title containing the chat name
        sidebar_selectors = [
            f'a[aria-label*="{project_title}"]',
            f'div[role="button"]:has-text("{project_title}")',
            f'a:has-text("{project_title}")',
        ]
        
        for sel in sidebar_selectors:
            try:
                chat_link = page.query_selector(sel)
                if chat_link:
                    logger.info(f"Found existing chat: '{project_title}'. Clicking...")
                    chat_link.click()
                    time.sleep(3)
                    return
            except Exception:
                continue
                
        logger.info(f"No existing chat found for '{project_title}'. Using current/new chat.")
        # If we are not in a new chat, click 'New chat'
        new_chat_btn = page.query_selector('a[href="/app"], button:has-text("New chat")')
        if new_chat_btn and not page.url.endswith('/app'):
            new_chat_btn.click()
            time.sleep(2)

    except Exception as e:
        logger.warning(f"Error while managing project chat: {e}")


def _set_gemini_mode(page, mode: str):
    """
    Select the Gemini model mode (Fast, Thinking, Pro) via the UI.
    Uses the data-test-id selectors provided by the user.
    """
    if not mode:
        mode = getattr(config, 'GEMINIWEB_DEFAULT_MODE', 'Fast')
    
    # Standardize mode name to lowercase for selector mapping
    mode_key = mode.lower().strip()
    selectors = {
        "fast": "bard-mode-option-fast",
        "thinking": "bard-mode-option-thinking",
        "pro": "bard-mode-option-pro"
    }
    
    target_id = selectors.get(mode_key)
    if not target_id:
        logger.warning(f"Unknown Gemini mode '{mode}', skipping selection.")
        return

    logger.info(f"Setting Gemini mode to: {mode}")
    try:
        # 1. Click the model picker button
        picker_btn = page.wait_for_selector('button[data-test-id="bard-mode-menu-button"]', timeout=10000)
        if picker_btn:
            # Check current mode to avoid redundant clicks
            current_mode = picker_btn.inner_text().strip().lower()
            if mode_key in current_mode:
                logger.info(f"Gemini is already in {mode} mode.")
                return

            picker_btn.click()
            time.sleep(1.5) # Wait for menu
            
            # 2. Click the specific mode option
            option_sel = f'button[data-test-id="{target_id}"], [data-test-id="{target_id}"]'
            option_btn = page.wait_for_selector(option_sel, timeout=5000)
            if option_btn:
                option_btn.click()
                logger.info(f"Successfully selected {mode} mode.")
                time.sleep(2) # Wait for mode switch to settle
            else:
                logger.warning(f"Could not find menu option for mode: {mode}")
        else:
            logger.warning("Could not find Gemini model picker button.")
    except Exception as e:
        logger.error(f"Error setting Gemini mode: {e}")


def _wait_for_response_complete(page, timeout: int = 180):
    """Wait for Gemini to finish processing the response."""
    import time
    logger.info("Waiting for Gemini to finish responding...")
    start_time = time.time()
    
    # First wait a bit for the response to start
    time.sleep(3)
    
    while time.time() - start_time < timeout:
        # Check if Gemini is still processing
        # The stop button appears while generating, disappears when done
        stop_btn = page.query_selector('button[aria-label="Stop response"]')
        if stop_btn and stop_btn.is_visible():
            logger.debug("Gemini still generating...")
            time.sleep(2)
            continue
            
        # Also check for the thinking/loading indicators
        loading_dots = page.query_selector('div.loading-dots, span.loading')
        spinner_selectors = [
            '.loading-indicator', '.response-loading', 'mat-progress-bar', 
            '.thinking-indicator', '[data-test-id="loading"]'
        ]
        
        still_loading = False
        if loading_dots and loading_dots.is_visible():
            still_loading = True
        else:
            for sel in spinner_selectors:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        still_loading = True
                        break
                except Exception:
                    continue
                    
        if not still_loading:
            # If no stop button and no loading, response might be done
            # Wait a brief moment and double-check
            time.sleep(2)
            stop_btn = page.query_selector('button[aria-label="Stop response"]')
            if not stop_btn or not stop_btn.is_visible():
                logger.info("Gemini response appears complete")
                return
                
        time.sleep(2)
        
    logger.warning(f"Response wait timed out after {timeout}s")



def _find_generated_image(page):
    """Search the page for a generated image and return its src URL."""
    image_selectors = [
        'div[data-message-id] img[src*="blob:"]',
        'div[data-message-id] img[src*="data:image"]',
        'div[data-message-id] img[src*="lh3.googleusercontent"]',
        'div[data-message-id] img[src*="encrypted"]',
        'img.generated-image[src]',
        'button.image-button img[src]',
        'button.generated-image-button img[src]',
        'div[data-message-id] img[src]',
    ]
    for selector in image_selectors:
        try:
            images = page.query_selector_all(selector)
            for img in reversed(images):
                src = img.get_attribute('src')
                if src and not src.startswith('data:image/svg') and 'avatar' not in src.lower():
                    width = img.evaluate('el => el.naturalWidth || el.width || 0')
                    if width > 50:
                        logger.info(f"Found generated image: {selector} (width={width})")
                        return src
        except Exception:
            continue
    return None


def _wait_for_image_response(page, timeout: int = None):
    """Wait for Gemini to generate and display an image in the response."""
    if timeout is None:
        timeout = getattr(config, 'GEMINIWEB_TIMEOUT', 120)
    try:
        _wait_for_response_complete(page, timeout)
    except Exception:
        pass
    image_src = _find_generated_image(page)
    if image_src:
        return image_src
    try:
        selector = (
            'button.image-button img[src], '
            'button.generated-image-button img[src], '
            'img.generated-image[src], '
            'div[data-message-id] img[src]'
        )
        page.wait_for_selector(selector, timeout=30000, state='visible')
        time.sleep(2)
        image_src = _find_generated_image(page)
    except Exception as e:
        logger.error(f"Timeout or error waiting for image: {e}")
    return image_src


def _inject_text_into_input(page, input_element, text: str) -> bool:
    """
    Inject text directly into the Gemini chat input without using the clipboard.

    Strategy:
    1. Try Playwright's native fill() — works for plain <textarea> or simple
       contenteditable elements.
    2. If fill() leaves the box empty (Quill virtualises its DOM), fall back to
       dispatching an 'input' event after setting innerHTML via JavaScript.
       This properly notifies React/Quill that the content changed.

    Args:
        page: Playwright page object
        input_element: The located input element
        text: The prompt text to inject

    Returns:
        True if text was injected successfully, False otherwise
    """
    # ── Attempt 1: Fast Keyboard Insert (Universal & Robust) ──────────────────
    try:
        page.evaluate("(el) => el.focus()", input_element)
        time.sleep(0.05)
        page.keyboard.press('Control+A')
        page.keyboard.press('Delete')
        time.sleep(0.05)
        # Use insert_text for instantaneous content deployment
        page.keyboard.insert_text(text)
        time.sleep(0.1)
        actual = input_element.inner_text().strip()
        if len(actual) >= max(10, len(text) // 2):
            logger.info("Prompt injected via keyboard.insert_text()")
            return True
        logger.debug(f"keyboard.insert_text() left box empty (got {len(actual)} chars), trying alternative")
    except Exception as e:
        logger.debug(f"keyboard.insert_text() failed: {e}, trying alternative")

    # ── Attempt 2: native fill() ─────────────────────────────────────────────
    try:
        input_element.fill(text)
        time.sleep(0.3)
        actual = input_element.inner_text().strip()
        if len(actual) >= max(10, len(text) // 2):
            logger.info("Prompt injected via fill()")
            return True
    except Exception:
        pass

    # ── Attempt 3: JS innerHTML ──────────────────────────────────────────────
    try:
        escaped = text.replace('`', '\\`').replace('$', '\\$')
        page.evaluate(f"""
            (el) => {{
                el.focus();
                el.innerText = `{escaped}`;
                ['input', 'keydown', 'keyup', 'change'].forEach(name => {{
                    el.dispatchEvent(new Event(name, {{ bubbles: true }}));
                }});
            }}
        """, input_element)
        time.sleep(0.3)
        actual = input_element.inner_text().strip()
        if len(actual) >= max(10, len(text) // 2):
            logger.info("Prompt injected via JS innerText")
            return True
    except Exception:
        pass

    return False


def _try_download_native(page, output_path: str) -> Optional[str]:
    """
    Download the latest generated image using multiple strategies.
    Optimized for high-resolution capture by persisting the lightbox view.
    """
    image_container_selectors = [
        'button.image-button',
        'button.generated-image-button',
        '[data-message-id] div[jsname] img',
    ]

    # Standard and high-res button selectors
    download_button_selectors = [
        'button[data-test-id="download-generated-image-button"]',
        'button[aria-label="Download full size image"]',
        'button[aria-label="Download full-sized image"]',
        'button[aria-label="Download image"]',
        'button[aria-label="Download"]',
        'button.image-button[aria-label*="Download"]',
        'a[aria-label*="Download"]',
        'mat-icon[fonticon="download"]',
        'a[download]',
    ]

    lightbox_close_selectors = [
        'button[aria-label="Close"]',
        'button[jsname][aria-label*="lose"]',
        'div.close-button',
    ]

    try:
        # Find the last rendered image container
        image_container = None
        for sel in image_container_selectors:
            containers = page.query_selector_all(sel)
            if containers:
                image_container = containers[-1]
                break

        if not image_container:
            logger.warning("No image container found for native download")
            return None

        # Trigger lightbox interaction
        logger.info("Step 0: Triggering image interaction (hover + click)...")
        try:
            image_container.scroll_into_view_if_needed()
            image_container.hover()
            time.sleep(1.0)
            
            # Strategy: Click 'Download' once to potentially trigger High-Res generation/swap
            # Some high-res buttons only appear on hover or after an initial interaction.
            try:
                # Force hover on the main image to reveal overlay buttons
                main_img = page.query_selector('img.main-image, div.lightbox img, div[role="dialog"] img')
                if main_img:
                    main_img.hover()
                    time.sleep(1.0)

                primary_trigger = page.query_selector('button[data-test-id="download-generated-image-button"]') or \
                                  page.query_selector('button[aria-label="Download full size image"]') or \
                                  page.query_selector('a[aria-label="Download image"], a[jsname="A47GAd"]') or \
                                  page.query_selector('button[aria-label="Download image"]')
                
                if primary_trigger:
                    logger.debug(f"Initial trigger click on '{primary_trigger.tag_name}' to start High-Res preparation...")
                    primary_trigger.click()
                    time.sleep(3.0) # Wait brief moment for potential swap/menu
            except Exception: pass

            # Polling wait for the "full size" version (Gemini can be slow to generate/swap)
            logger.info("Waiting for 'Download full size image' button to appear (~45s max)...")
            full_res_btn_sel = 'button[data-test-id="download-generated-image-button"], button[aria-label="Download full size image"]'
            found_full = False
            for i in range(45): 
                try:
                    btn = page.query_selector(full_res_btn_sel)
                    if btn and btn.is_visible():
                        logger.info(f"Detected 'Download full size image' button at {i}s!")
                        found_full = True
                        break
                    
                    # Also check if image natural width has increased (indicating a high-res swap happened)
                    dims = page.evaluate("""
                        () => {
                            const img = document.querySelector('img.main-image, .picker-dialog img, div[role="dialog"] img');
                            return img ? { w: img.naturalWidth } : null;
                        }
                    """)
                    if dims and dims['w'] > 2000:
                        logger.info("Detected high-res natural image swap!")
                        found_full = True # We can try to download now even if button label didn't change (e.g. jsevent)
                        break
                except Exception: pass
                time.sleep(1.0)
            
            if not found_full:
                logger.debug("Full-sized button not found after 45s wait. Proceeding with standard capture.")


            # Ensure lightbox img is visible
            lightbox_img_sel = 'img.main-image, div.lightbox img, div[role="dialog"] img, .picker-dialog img'
            try:
                page.wait_for_selector(lightbox_img_sel, timeout=5000, state='visible')
                logger.debug("Lightbox image visible.")
            except Exception: 
                logger.warning("Lightbox image not stabilized, proceeding anyway")
        except Exception as click_err:
            logger.debug(f"Lightbox interaction error: {click_err}")
            image_container.hover()
            time.sleep(1.0)

        # ── Strategy 1: expect_download() ──
        logger.info("Strategy 1: Attempting native browser download (Prioritizing Original)...")
        for btn_sel in download_button_selectors:
            try:
                btns = page.locator(btn_sel).all()
                if btns:
                    btn = btns[-1] 
                    if btn.is_visible():
                        logger.info(f"Targeting download button: '{btn_sel}'")
                        try:
                            # If it's the full-sized one, give it more time to generate
                            if "full-sized" in btn_sel: time.sleep(1.5)
                            
                            # Gemini occasionally fails with a "Could not download image" toast.
                            # We retry up to 3 times before failing Strategy 1.
                            for retry_attempt in range(3):
                                try:
                                    with page.expect_download(timeout=10000) as dl_info:
                                        btn.click()
                                    dl = dl_info.value
                                    dl.save_as(output_path)
                                    break # Success
                                except Exception as dl_err:
                                    # Check for "Could not download image" toast or similar
                                    error_toast = page.query_selector('div:has-text("Could not download image"), snack-bar:has-text("Could not download")')
                                    if error_toast and error_toast.is_visible():
                                        logger.warning(f"Strategy 1: Detected error toast (attempt {retry_attempt+1}). Retrying in 2s...")
                                        time.sleep(2)
                                        continue
                                    
                                    # If it's the last attempt or not a recognized toast error, let it bubble up
                                    if retry_attempt == 2:
                                        raise dl_err
                                    logger.debug(f"Strategy 1 attempt {retry_attempt+1} failed: {dl_err}. Retrying...")
                                    time.sleep(1)
                            
                            fsize = os.path.getsize(output_path)
                            if fsize > 3000000: # IDEAL SUCCESS: > 3MB (likely original)
                                logger.info(f"Strategy 1 IDEAL SUCCESS: {output_path} ({fsize:,} bytes)")
                                return output_path
                            elif fsize > 1000000: # GOOD SUCCESS: > 1MB (likely high-res preview)
                                logger.info(f"Strategy 1 GOOD SUCCESS: {output_path} ({fsize:,} bytes). Continuing to check for better copies...")
                                # We'll keep this but continue the loop if "full-sized" wasn't hit yet
                                if "full-sized" in btn_sel: return output_path
                                # If we hit a non-full-sized but it's okay, maybe try one more button
                            else:
                                logger.warning(f"Strategy 1 file small ({fsize:,} bytes). Retrying alternatives...")
                                # os.remove(output_path) # Don't remove yet, keep as backup if ALL else fails
                        except Exception as dl_err:
                            logger.debug(f"expect_download failed for '{btn_sel}': {dl_err}")
                            
                            # Check for new tab (Strategy 1.1)
                            pages = page.context.pages
                            if len(pages) > 1:
                                new_page = pages[-1]
                                logger.info(f"New tab detected at {new_page.url[:60]}")
                                time.sleep(3)
                                new_url = new_page.url
                                if 'googleusercontent' in new_url or 'blob:' in new_url:
                                    fetch_url = new_url
                                    if 'googleusercontent.com' in fetch_url and '=' in fetch_url:
                                        fetch_url = fetch_url.split('=')[0] + '=s0'
                                    
                                    logger.info(f"Fetching from new tab: {fetch_url[:80]}...")
                                    resp = page.request.get(fetch_url)
                                    body = resp.body()
                                    if resp.ok and len(body) > 200000:
                                        with open(output_path, 'wb') as f:
                                            f.write(body)
                                        new_page.close()
                                        logger.info(f"Strategy 1.1 SUCCESS: Extracted {len(body):,} bytes from tab")
                                        return output_path
                                    
                                    # Screenshot fallback for tab
                                    img_el = new_page.query_selector('img')
                                    if img_el:
                                        img_el.screenshot(path=output_path)
                                        fsize_ss = os.path.getsize(output_path)
                                        logger.warning(f"Strategy 1.1 SCREENSHOT: {fsize_ss:,} bytes")
                                        new_page.close()
                                        if fsize_ss > 200000: return output_path
            except Exception as e:
                logger.debug(f"Strategy 1 internal loop error: {e}")
                continue

        # ── Strategy 2: Direct High-Res URL Fetch ──
        logger.info("Strategy 2: Attempting direct authenticated URL fetch (=s0)...")
        img_selectors = [
            'img.main-image', 
            'div.lightbox img', 
            'div[role="dialog"] img', 
            '.picker-dialog img',
            'button.image-button img', 
            'div[data-message-id] img[src*="googleusercontent"]'
        ]
        for img_sel in img_selectors:
            try:
                imgs = page.query_selector_all(img_sel)
                for img in reversed(imgs):
                    src = img.get_attribute('src')
                    if not src or src.startswith('data:image/svg') or 'avatar' in src.lower(): continue
                    
                    is_google_host = any(x in src for x in ['googleusercontent.com', 'gstatic.com', 'google.com', 'encrypted-tbn'])
                    if src.startswith('http') and (is_google_host or len(src) > 100):
                        fetch_url = src
                        if 'googleusercontent.com' in src and '=' in src:
                            fetch_url = src.split('=')[0] + '=s0'
                        
                        logger.info(f"Found image element ({img_sel}), fetching {fetch_url[:80]}...")
                        response = page.request.get(fetch_url)
                        if response.ok:
                            body = response.body()
                            if len(body) > 200000:
                                with open(output_path, 'wb') as f: f.write(body)
                                logger.info(f"Strategy 2 SUCCESS: {output_path} ({len(body):,} bytes)")
                                return output_path
                            else:
                                logger.debug(f"Strategy 2 fetch result too small: {len(body):,} bytes")
            except Exception as e: 
                logger.debug(f"Strategy 2 check failed for {img_sel}: {e}")
                continue

        # ── Strategy 3: JS Canvas Extraction ──
        logger.info("Strategy 3: Attempting JS Canvas extraction (Natural Resolution)...")
        for img_sel in ['img.main-image', 'div.lightbox img', 'div[role="dialog"] img', 'button.image-button img']:
            try:
                imgs = page.query_selector_all(img_sel)
                for img_el in reversed(imgs):
                    src = img_el.get_attribute('src')
                    if not src or src.startswith('data:image/svg'): continue
                    
                    nw = img_el.evaluate('el => el.naturalWidth || 0')
                    nh = img_el.evaluate('el => el.naturalHeight || 0')
                    logger.debug(f"Canvas source ({img_sel}): {nw}x{nh}")
                    if nw < 300: continue # Skip tiny previews
                    
                    data_url = img_el.evaluate("""
                        (img) => new Promise(resolve => {
                            const extract = () => {
                                const c = document.createElement('canvas');
                                c.width = img.naturalWidth; c.height = img.naturalHeight;
                                c.getContext('2d').drawImage(img, 0, 0);
                                resolve(c.toDataURL('image/png'));
                            };
                            if (!img.complete) { img.onload = extract; } else { extract(); }
                        })
                    """)
                    if data_url and ',' in data_url:
                        _, data = data_url.split(',', 1)
                        img_bytes = base64.b64decode(data)
                        if len(img_bytes) > 200000:
                            with open(output_path, 'wb') as f: f.write(img_bytes)
                            logger.info(f"Strategy 3 SUCCESS: {len(img_bytes):,} bytes")
                            return output_path
            except Exception as e: 
                logger.debug(f"Strategy 3 failed: {e}")
                continue

        logger.warning("All native download strategies failed or yielded low resolution")
        return None

    finally:
        # Cleanup: Close lightbox
        try:
            for close_sel in lightbox_close_selectors:
                close_btn = page.locator(close_sel).first
                if close_btn.is_visible(timeout=500):
                    close_btn.click()
                    time.sleep(1)
                    break
        except Exception: pass


def _download_image_fallback(page, image_src: str, output_path: str) -> Optional[str]:
    """Fallback — prioritized byte fetching over scaling-sensitive screenshots."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 1. data: URI
    if image_src.startswith('data:image'):
        try:
            _, data = image_src.split(',', 1)
            with open(output_path, 'wb') as f: f.write(base64.b64decode(data))
            return output_path
        except Exception: return None

    # 2. Direct fetch with high-res param
    if image_src.startswith('http'):
        try:
            fetch_url = image_src
            if 'googleusercontent.com' in fetch_url and '=' in fetch_url:
                fetch_url = fetch_url.split('=')[0] + '=s0'
            logger.info(f"Fallback fetch: {fetch_url[:80]}...")
            resp = page.request.get(fetch_url)
            if resp.ok and len(resp.body()) > 2000:
                with open(output_path, 'wb') as f: f.write(resp.body())
                return output_path
        except Exception: pass

    # 3. blob: URL
    if image_src.startswith('blob:'):
        try:
            data_url = page.evaluate("""
                async (url) => {
                    const r = await fetch(url);
                    const b = await r.blob();
                    return new Promise(res => {
                        const fr = new FileReader();
                        fr.onloadend = () => res(fr.result);
                        fr.readAsDataURL(b);
                    });
                }
            """, image_src)
            if data_url and ',' in data_url:
                _, d = data_url.split(',', 1)
                img_bytes = base64.b64decode(d)
                if len(img_bytes) > 1000:
                    with open(output_path, 'wb') as f: f.write(img_bytes)
                    return output_path
        except Exception: pass

    # 4. Element screenshot (Absolute last resort)
    try:
        page.evaluate("() => document.querySelectorAll('footer, .chat-input, .prompt-area').forEach(el => el.style.display='none')")
        for sel in ['div[data-message-id] img', 'button.image-button img']:
            for img in reversed(page.query_selector_all(sel)):
                if img.get_attribute('src') == image_src:
                    img.scroll_into_view_if_needed()
                    time.sleep(0.5)
                    img.screenshot(path=output_path)
                    return output_path
    except Exception: pass


def _remove_watermark(image_path: str, media_type: str = "image"):
    """
    Remove watermark using either the builtin CV2 logic or an external tool.
    Configured via config.WATERMARK_REMOVAL_METHOD.
    """
    # ── Strategy 1: External Tool ──────────────────────────────────────────
    if getattr(config, 'WATERMARK_REMOVAL_METHOD', 'builtin') == 'external':
        if media_type == "video":
            tool_path = getattr(config, 'GEMINI_WATERMARK_TOOL_VIDEO', '')
        else:
            tool_path = getattr(config, 'GEMINI_WATERMARK_TOOL_IMAGE', '')

        if tool_path and os.path.exists(tool_path):
            logger.info(f"Using external watermark tool ({media_type}): {tool_path}")
            import subprocess
            try:
                # The parameter for external tool is the full path to image/video
                result = subprocess.run([tool_path, image_path], capture_output=True, text=True, check=True)
                logger.info(f"External watermark tool output: {result.stdout.strip()}")
                return
            except Exception as e:
                logger.error(f"External watermark tool failed: {e}. Falling back to builtin (if image).")
        else:
            logger.warning(f"External watermark tool ({media_type}) configured but path missing or invalid.")
            if media_type == "video":
                return # No fallback for video

    if media_type == "video":
        logger.warning("Builtin watermark removal is not supported for video.")
        return

    # ── Strategy 2: Builtin Precision Restoration (Images Only) ────────────
    try:
        import cv2
        import numpy as np
        
        img = cv2.imread(image_path)
        if img is None:
            return

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        quad = gray[h//2:, w//2:]
        
        m48 = _get_mask(_MASK_48_B64)
        m96 = _get_mask(_MASK_96_B64)
        
        best_match = None
        
        # Step 1: Try native scale (1.0) first — fast path for full-res downloads.
        for mask in [m48, m96]:
            mh, mw = mask.shape[:2]
            if mh > quad.shape[0] or mw > quad.shape[1]:
                continue
            res = cv2.matchTemplate(quad, mask, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if best_match is None or max_val > best_match['val']:
                best_match = {'val': max_val, 'loc': max_loc, 'scale': 1.0, 'mask': mask}

        # Step 2: If native scale is not confident enough, do multi-scale search.
        if not best_match or best_match['val'] < 0.7:
            for mask in [m48, m96]:
                for s in np.linspace(0.4, 1.6, 20):
                    mh_s, mw_s = mask.shape[:2]
                    nh, nw = int(mh_s * s), int(mw_s * s)
                    if nh < 10 or nh > quad.shape[0] or nw > quad.shape[1]:
                        continue
                    resized_mask = cv2.resize(mask, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
                    res = cv2.matchTemplate(quad, resized_mask, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, max_loc = cv2.minMaxLoc(res)
                    if best_match is None or max_val > best_match['val']:
                        best_match = {'val': max_val, 'loc': max_loc, 'scale': s, 'mask': resized_mask}

        is_native_scale = best_match and abs(best_match['scale'] - 1.0) < 0.05

        if not best_match or best_match['val'] < 0.35:
            logger.info(f"No watermark detected in {image_path} (confidence={best_match['val'] if best_match else 0:.3f})")
            return

        mx, my = best_match['loc']
        mh, mw = best_match['mask'].shape[:2]
        gx, gy = mx + (w // 2), my + (h // 2)

        alpha = best_match['mask'].astype(np.float32) / 255.0
        LOGO_COLOR = 252.0

        roi = img[gy:gy+mh, gx:gx+mw].astype(np.float32)
        alpha_3ch = cv2.merge([alpha, alpha, alpha])
        denom = np.maximum(1.0 - alpha_3ch, 0.05)
        restored = (roi - (alpha_3ch * LOGO_COLOR)) / denom
        restored = np.clip(restored, 0, 255).astype(np.uint8)

        if is_native_scale:
            img[gy:gy+mh, gx:gx+mw] = restored
        else:
            cleanup_mask = (best_match['mask'] > 2).astype(np.uint8) * 255
            kernel = np.ones((3, 3), np.uint8)
            cleanup_mask = cv2.dilate(cleanup_mask, kernel, iterations=1)
            final_roi = cv2.inpaint(restored, cleanup_mask, inpaintRadius=2, flags=cv2.INPAINT_TELEA)
            img[gy:gy+mh, gx:gx+mw] = final_roi

            PAD = 1
            ey1 = max(gy - PAD, 0);  ey2 = min(gy + mh + PAD, h)
            ex1 = max(gx - PAD, 0);  ex2 = min(gx + mw + PAD, w)
            band = img[ey1:ey2, ex1:ex2].copy()
            smooth = cv2.medianBlur(band, 3)
            diff = np.abs(band.astype(np.int32) - smooth.astype(np.int32)).max(axis=2)
            ph, pw = band.shape[:2]
            outer_only = np.zeros((ph, pw), dtype=bool)
            outer_only[:PAD, :] = True;   outer_only[-PAD:, :] = True
            outer_only[:, :PAD] = True;   outer_only[:, -PAD:] = True
            to_fix = outer_only & (diff > 20)
            if to_fix.any():
                band[to_fix] = smooth[to_fix]
                img[ey1:ey2, ex1:ex2] = band
        cv2.imwrite(image_path, img)
        logger.info(f"Builtin watermark restoration success: {image_path} @ ({gx},{gy}) scale={best_match['scale']:.2f} (JPG refined)")

    except Exception as e:
        logger.error(f"Error in builtin watermark restoration: {e}")


def run(prompt: str, output_path: str, aspect_ratio: str = None, project_title: str = None, reference_image_path: str = None, profile_dir: str = None, gemini_mode: str = None) -> Optional[str]:
    """Main entry point — run Playwright and generate an image."""
    from playwright.sync_api import sync_playwright

    gemini_url = getattr(config, 'GEMINIWEB_URL', 'https://gemini.google.com/app')
    timeout = getattr(config, 'GEMINIWEB_TIMEOUT', 120)

    logger.info(f"Generating image (GeminiWeb subprocess): {output_path}")
    logger.debug(f"  Prompt: {prompt[:100]}...")
    logger.debug(f"  Aspect ratio: {aspect_ratio or config.IMAGE_ASPECT_RATIO}")

    with sync_playwright() as playwright_instance:
        context = _create_browser_context(playwright_instance, profile_dir)
        page = context.pages[0] if context.pages else context.new_page()

        try:
            logger.info(f"Navigating to {gemini_url}")
            # Increase navigation buffer to respect GEMINIWEB_TIMEOUT loaded above
            page.goto(gemini_url, wait_until='domcontentloaded', timeout=timeout * 1000)
            time.sleep(2)

            # ── Set Gemini Mode (Fast/Thinking/Pro) ──────────────────────────
            _set_gemini_mode(page, gemini_mode)

            # ── Ensure correct chat ──────────────────────────────────────────
            if project_title:
                _ensure_project_chat(page, project_title)

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

            full_prompt = _compose_prompt(prompt, aspect_ratio)
            logger.info(f"Sending prompt: {full_prompt[:120]}...")

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
            try:
                combined_selector = ", ".join(input_selectors)
                el = page.wait_for_selector(combined_selector, timeout=12000, state='visible')
                if el:
                    input_element = el
                    logger.info("Found input element")
            except Exception:
                pass

            if not input_element:
                logger.error("Could not find the chat input field")
                return None

            # ── Upload Reference Images ───────────────────────────────────────
            images_to_upload = reference_image_path if isinstance(reference_image_path, list) else ([reference_image_path] if reference_image_path else [])
            
            for ref_path in images_to_upload:
                if ref_path and os.path.exists(ref_path):
                    import shutil
                    try:
                        logger.info(f"Uploading reference image: {ref_path}")
                        
                        # 1. Click the Plus/Upload button to open menu
                        upload_selectors = [
                            'button[aria-label^="Upload"]',
                            'button.upload-card-button',
                            'button[aria-label="Add text or media"]',
                            'button[aria-label="Open upload file menu"]',
                        ]
                        clicked = False
                        for sel in upload_selectors:
                            try:
                                btn = page.query_selector(sel)
                                if btn and btn.is_visible():
                                    btn.click()
                                    time.sleep(1.5)  # wait for menu animation
                                    clicked = True
                                    logger.info(f"Clicked upload trigger button: {sel}")
                                    break
                            except Exception:
                                continue
                        
                        uploaded = False
                        if clicked:
                            # 2. Click 'Upload files' and intercept with FileChooser
                            menu_item_selectors = [
                                'button[aria-label^="Upload files"]',
                                'div[role="menuitem"]:has-text("Upload files")',
                                '.mat-mdc-list-item:has-text("Upload files")',
                                'button:has-text("Upload files")',
                            ]
                            for m_sel in menu_item_selectors:
                                try:
                                    if page.query_selector(m_sel):
                                        with page.expect_file_chooser() as fc_info:
                                            page.click(m_sel)
                                        file_chooser = fc_info.value
                                        file_chooser.set_files(ref_path)
                                        uploaded = True
                                        logger.info(f"Uploaded reference image via FileChooser trigger ({m_sel})")
                                        time.sleep(2)  # Reduced from 5s; subsequent wait_for_selector for thumbnails handles the heavy lifting
                                        break
                                except Exception as e:
                                    logger.debug(f"Click menu item failed for {m_sel}: {e}")
                                    continue
                                    
                        if not uploaded:
                            logger.warning(f"Could not upload {ref_path} via FileChooser trigger. Trying direct set_input_files fallback...")
                            page.set_input_files('input[type="file"]', ref_path)
                            logger.info(f"Reference image {ref_path} uploaded via direct set_input_files fallback")
                            time.sleep(2)  # Reduced from 5s
    
                    except Exception as e:
                        logger.error(f"Failed to upload reference image {ref_path}: {e}")
                
                if not uploaded and ref_path:
                    logger.error(f"ABORTING: Mandatory reference image {ref_path} failed to upload. Cannot ensure consistency.")
                    return None

            # ── Wait for thumbnails to render in the input area ──────────────
            if images_to_upload:
                try:
                    logger.info("Waiting for image thumbnails to appear in input...")
                    # Gemini usually shows thumbnails in these elements
                    thumbnail_selectors = [
                        'mat-chip-row img',
                        'div.thumbnail-wrapper img',
                        '.image-thumbnail img',
                        'div[contenteditable="true"] img',
                    ]
                    page.wait_for_selector(", ".join(thumbnail_selectors), timeout=15000)
                    logger.info("Thumbnails detected")
                    time.sleep(2) # Extra buffer for backend attachment
                except Exception as thumb_err:
                    logger.warning(f"Timeout waiting for thumbnail preview: {thumb_err}. Proceeding anyway.")

            # ── Inject the prompt (no clipboard / copy-paste) ────────────────
            injected = _inject_text_into_input(page, input_element, full_prompt)
            if not injected:
                logger.error("All prompt injection attempts failed")
                return None

            time.sleep(0.4) # Reduced from 1.0s

            # ── Submit the prompt ────────────────────────────────────────────
            send_selectors = [
                'button[aria-label="Send message"]',
                'button.send-button',
                'button[data-test-id="send-button"]',
                'button[aria-label="Send"]',
            ]
            sent = False
            try:
                combined_send = ", ".join(send_selectors)
                send_btn = page.wait_for_selector(combined_send, timeout=5000, state='visible')
                if send_btn:
                    send_btn.click()
                    sent = True
                    logger.info("Clicked send button")
            except Exception:
                pass
            if not sent:
                page.keyboard.press('Enter')

            logger.info("Prompt submitted, waiting for image generation...")
            image_src = _wait_for_image_response(page, timeout)

            if not image_src:
                logger.warning("No image found on first check, trying expanded view...")
                try:
                    expand_selectors = [
                        'button.image-button',
                        'button:has-text("Show image")',
                        'button:has-text("View image")',
                    ]
                    for sel in expand_selectors:
                        try:
                            btn = page.query_selector(sel)
                            if btn and btn.is_visible():
                                btn.click()
                                time.sleep(3)
                                break
                        except Exception:
                            continue
                    image_src = _wait_for_image_response(page, 30)
                except Exception:
                    pass

            if not image_src:
                logger.error("No image was generated by Gemini")
                diag_path = output_path.replace('.png', '_diagnostic.png')
                page.screenshot(path=diag_path, full_page=False)
                logger.info(f"Diagnostic screenshot saved: {diag_path}")
                return None

            # ── Download the image ───────────────────────────────────────────
            logger.info("Waiting 5 seconds for full resolution to stabilize...")
            time.sleep(5)  # Wait for full res image to fully render (User requested)
            
            # Preferred: Playwright native download (highest quality, exact file)
            result = _try_download_native(page, output_path)
            if not result:
                # Fallback: extract from src attribute (data URI / blob URL)
                result = _download_image_fallback(page, image_src, output_path)

            if result:
                _remove_watermark(result)
                file_size = os.path.getsize(result)
                logger.info(f"Generated (GeminiWeb): {result} ({file_size:,} bytes)")
                return result
            else:
                logger.error("Failed to download the generated image")
                diag_path = output_path.replace('.png', '_download_diagnostic.png')
                page.screenshot(path=diag_path, full_page=False)
                logger.info(f"Download failure diagnostic screenshot saved: {diag_path}")
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
    parser.add_argument("prompt")
    parser.add_argument("output_path")
    parser.add_argument("--aspect-ratio", default=None)
    parser.add_argument("--project-title", default=None)
    parser.add_argument("--reference-image", action="append", default=[])
    parser.add_argument("--profile-dir", default=None)
    parser.add_argument("--gemini-mode", default=None)
    args = parser.parse_args()

    # Pass the list directly
    result = run(args.prompt, args.output_path, args.aspect_ratio, args.project_title, args.reference_image, args.profile_dir, args.gemini_mode)
    if result:
        print(f"SUCCESS:{result}")
        sys.exit(0)
    else:
        print("FAILED")
        sys.exit(1)
