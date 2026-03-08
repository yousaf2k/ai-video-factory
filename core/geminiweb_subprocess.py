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


def _create_browser_context(playwright_instance):
    """Create a persistent browser context with the configured browser."""
    chrome_profile = getattr(config, 'GEMINIWEB_CHROME_PROFILE', None)
    if not chrome_profile:
        chrome_profile = os.path.join(
            getattr(config, 'OUTPUT_DIR', 'output'), 'chrome_profile'
        )
    os.makedirs(chrome_profile, exist_ok=True)
    
    browser_type_name = getattr(config, 'PLAYWRIGHT_BROWSER', 'chromium').lower()
    channel = getattr(config, 'PLAYWRIGHT_CHANNEL', 'chrome')
    
    logger.info(f"Using browser: {browser_type_name}, channel: {channel}, profile: {chrome_profile}")

    try:
        # Map browser type name to playwright browser type object
        if browser_type_name == "firefox":
            browser_type = playwright_instance.firefox
            channel = None # Firefox doesn't use channels in Playwright
        elif browser_type_name == "webkit":
            browser_type = playwright_instance.webkit
        else:
            browser_type = playwright_instance.chromium

        launch_args = [
            '--disable-blink-features=AutomationControlled',
            '--no-first-run',
            '--no-default-browser-check',
        ]
        
        # Ignored for firefox/webkit if they don't support these specific flags, 
        # but mostly harmless or handled by playwright.
        
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


def _wait_for_response_complete(page, timeout: int = 180):
    """Wait for Gemini to finish processing the response."""
    logger.info("Waiting for Gemini to finish responding...")
    spinner_selectors = [
        '.loading-indicator',
        '.response-loading',
        'mat-progress-bar',
        '.thinking-indicator',
        '[data-test-id="loading"]',
    ]
    time.sleep(5)
    waited = 0
    while waited < timeout:
        still_loading = False
        for sel in spinner_selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    still_loading = True
                    break
            except Exception:
                continue
        if not still_loading:
            break
        time.sleep(2)
        waited += 2
    time.sleep(3)


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
    input_element.click()
    time.sleep(0.3)

    # ── Attempt 1: native fill() ─────────────────────────────────────────────
    try:
        input_element.fill(text)
        time.sleep(0.5)
        actual = input_element.inner_text().strip()
        if len(actual) >= max(10, len(text) // 2):
            logger.info("Prompt injected via fill()")
            return True
        logger.debug(f"fill() left box mostly empty (got {len(actual)} chars), trying JS injection")
    except Exception as e:
        logger.debug(f"fill() failed: {e}, trying JS injection")

    # ── Attempt 2: JS innerHTML + input event (for Quill / ProseMirror) ──────
    try:
        # Escape backticks so the string is safe inside a JS template literal
        escaped = text.replace('`', '\\`').replace('$', '\\$')
        page.evaluate(f"""
            (el) => {{
                el.focus();
                // Set the raw text content (works for div[contenteditable])
                el.innerText = `{escaped}`;
                // Move cursor to the end so the editor knows where to continue
                const range = document.createRange();
                const sel   = window.getSelection();
                range.selectNodeContents(el);
                range.collapse(false);
                sel.removeAllRanges();
                sel.addRange(range);
                // Fire all events the framework listens to
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
        logger.warning(f"JS injection also unreliable (got {len(actual)}/{len(text)} chars)")
    except Exception as e:
        logger.error(f"JS injection failed: {e}")

    # ── Attempt 3: keyboard type (slow but universally reliable) ─────────────
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


def _try_download_native(page, output_path: str) -> Optional[str]:
    """
    Download the latest generated image using Playwright's native download API.

    Gemini renders generated images inside clickable image buttons. When you
    hover over one, a toolbar with a download icon appears. This function:
      1. Locates the last generated image element.
      2. Waits for Gemini to prepare the full-resolution version.
      3. Hovers over it to reveal the action toolbar.
      4. Clicks the download button and intercepts the file via expect_download().
      5. If the file is suspiciously small, waits and retries for full quality.

    Args:
        page: Playwright page object
        output_path: Where to save the downloaded file

    Returns:
        Path to the saved image, or None if download was not possible
    """
    # Selectors for the image wrapper buttons Gemini renders
    image_container_selectors = [
        'button.image-button',
        'button.generated-image-button',
        '[data-message-id] div[jsname] img',
    ]

    # Selectors for the download button (appears in toolbar on hover)
    download_button_selectors = [
        'button[aria-label="Download"]',
        'button[aria-label="Download full-sized image"]',
        'button[jsname][aria-label*="ownload"]',
        'a[download]',
    ]

    # Minimum expected file size for a full-res Gemini image (4 MB)
    MIN_FULL_RES_SIZE = 4 * 1024 * 1024

    def _do_hover_and_download(image_container) -> Optional[str]:
        """Hover over the image container and click the download button."""
        image_container.hover()
        time.sleep(1.5)  # give the toolbar animation time to complete

        for btn_sel in download_button_selectors:
            try:
                btns = page.query_selector_all(btn_sel)
                if btns:
                    btn = btns[-1]
                    if btn.is_visible():
                        logger.info(f"Clicking download button: {btn_sel}")
                        with page.expect_download(timeout=60000) as dl_info:
                            btn.click()
                        dl = dl_info.value
                        dl.save_as(output_path)
                        logger.info(f"Native download saved: {output_path}")
                        return output_path
            except Exception as e:
                logger.debug(f"Download attempt via '{btn_sel}' failed: {e}")
                continue
        return None

    try:
        # Find the last rendered image container
        image_container = None
        for sel in image_container_selectors:
            containers = page.query_selector_all(sel)
            if containers:
                image_container = containers[-1]
                logger.debug(f"Found image container: {sel}")
                break

        if not image_container:
            return None

        # ── Wait for Gemini to prepare the full-resolution image ─────────────
        # Gemini generates images asynchronously; the thumbnail appears first
        # and the full-res version becomes available several seconds later.
        logger.info("Waiting 5s for Gemini to prepare full-resolution image...")
        time.sleep(5)

        # ── Download with retries (handles network errors + low-res files) ───
        best_size = 0
        for attempt in range(3):
            if attempt > 0:
                wait = 10
                logger.warning(f"Retry {attempt}/2: waiting {wait}s before re-attempting download...")
                time.sleep(wait)
                # Re-hover since toolbar may have disappeared
                image_container.hover()
                time.sleep(1)

            result = _do_hover_and_download(image_container)
            if not result:
                logger.warning(f"Download attempt {attempt+1} failed (no download triggered)")
                continue

            file_size = os.path.getsize(output_path)
            logger.info(f"Attempt {attempt+1} downloaded: {file_size:,} bytes")

            if file_size >= MIN_FULL_RES_SIZE:
                logger.info(f"Full-res image downloaded ({file_size:,} bytes)")
                return output_path

            # Keep track of the best (largest) file we got
            if file_size > best_size:
                best_size = file_size

        # Return whatever we have even if it's smaller than expected
        if best_size > 0:
            logger.warning(f"Could not get full-res after 3 attempts, using best: {best_size:,} bytes")
            return output_path

        return None

    except Exception as e:
        logger.debug(f"Native download preparation failed: {e}")

    return None



def _download_image_fallback(page, image_src: str, output_path: str) -> Optional[str]:
    """
    Fallback image extractor — used only when native download is not available.

    Handles:
    - data: URIs (base64 decode)
    - blob: URLs (fetch inside browser context and read as data URL)
    - Direct HTTP fetch for regular URLs (bypasses UI buttons and scales up to original size)
    - Element screenshot (absolute last resort)

    Args:
        page: Playwright page object
        image_src: src attribute of the <img> element
        output_path: Where to save the image

    Returns:
        Path to the saved image, or None if all methods fail
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # ── data: URI ────────────────────────────────────────────────────────────
    if image_src.startswith('data:image'):
        try:
            _, data = image_src.split(',', 1)
            with open(output_path, 'wb') as f:
                f.write(base64.b64decode(data))
            logger.info(f"Saved image from data URI: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"data: URI decode failed: {e}")
            return None

    # ── blob: URL — fetch inside browser context ──────────────────────────────
    if image_src.startswith('blob:'):
        try:
            data_url = page.evaluate("""
                async (blobUrl) => {
                    const resp = await fetch(blobUrl);
                    const blob = await resp.blob();
                    return new Promise(resolve => {
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                    });
                }
            """, image_src)
            if data_url and ',' in data_url:
                _, data = data_url.split(',', 1)
                with open(output_path, 'wb') as f:
                    f.write(base64.b64decode(data))
                logger.info(f"Saved blob: image: {output_path}")
                return output_path
        except Exception as e:
            logger.error(f"blob: URL extraction failed: {e}")

    # ── Direct HTTP fetch (for googleusercontent, etc.) ──────────────────────
    if image_src.startswith('http'):
        try:
            # If it's a Gemini image, we remove the sizing parameters to get the uncompressed original
            # e.g. https://lh3.googleusercontent.com/...=w1024-h1024 -> =s0
            fetch_url = image_src
            if 'googleusercontent.com' in fetch_url and '=' in fetch_url:
                fetch_url = fetch_url.split('=')[0] + '=s0'
            
            logger.info(f"Attempting direct authenticated fetch: {fetch_url}")
            # Use Playwright's native API context to inherit all Gemini auth cookies automatically
            response = page.request.get(fetch_url)
            if response.ok:
                with open(output_path, 'wb') as f:
                    f.write(response.body())
                logger.info(f"Saved original image via fetch: {output_path}")
                return output_path
            else:
                logger.error(f"Direct fetch failed: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Direct authenticated fetch failed: {e}")

    # ── Element screenshot (absolute last resort) ─────────────────────────────
    try:
        # We restrict the screenshot to only elements inside the message to avoid 
        # accidentally screenshotting the text input area or UI icons
        for selector in ['div[data-message-id] img', 'button.image-button img']:
            for img in reversed(page.query_selector_all(selector)):
                if img.get_attribute('src') == image_src:
                    img.scroll_into_view_if_needed()
                    img.screenshot(path=output_path)
                    logger.info(f"Saved via element screenshot (thumbnail only): {output_path}")
                    return output_path
    except Exception as e:
        logger.error(f"Element screenshot failed: {e}")

    return None




def _remove_watermark(image_path: str):
    """
    High-precision watermark restoration using reverse alpha-blending.
    Updated v0.2.5: Adjusted for JPG compression noise (Logo Color=252.0)
    and enhanced dilation of the cleanup mask to eliminate edge residues.
    """
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
        # This handles resized screenshots where the watermark was downscaled.
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
            # Full-res native download: mask fits perfectly.
            # Pure reverse alpha-blending — no inpainting needed (avoids artifacts on sharp PNGs).
            img[gy:gy+mh, gx:gx+mw] = restored
        else:
            # Screenshot / resized image: use inpainting to handle compression halos,
            # then surgical corner fix for any bright pixels just outside the mask.
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
        logger.info(f"Precise restoration success: {image_path} @ ({gx},{gy}) scale={best_match['scale']:.2f} conf={best_match['val']:.3f} (JPG refined)")

    except Exception as e:
        logger.error(f"Error in precise watermark restoration: {e}")


def run(prompt: str, output_path: str, aspect_ratio: str = None) -> Optional[str]:
    """Main entry point — run Playwright and generate an image."""
    from playwright.sync_api import sync_playwright

    gemini_url = getattr(config, 'GEMINIWEB_URL', 'https://gemini.google.com/app')
    timeout = getattr(config, 'GEMINIWEB_TIMEOUT', 120)

    logger.info(f"Generating image (GeminiWeb subprocess): {output_path}")
    logger.debug(f"  Prompt: {prompt[:100]}...")
    logger.debug(f"  Aspect ratio: {aspect_ratio or config.IMAGE_ASPECT_RATIO}")

    with sync_playwright() as playwright_instance:
        context = _create_browser_context(playwright_instance)
        page = context.new_page()

        try:
            logger.info(f"Navigating to {gemini_url}")
            page.goto(gemini_url, wait_until='domcontentloaded', timeout=60000)
            time.sleep(5)

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

            # ── Inject the prompt (no clipboard / copy-paste) ────────────────
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
    args = parser.parse_args()

    result = run(args.prompt, args.output_path, args.aspect_ratio)
    if result:
        print(f"SUCCESS:{result}")
        sys.exit(0)
    else:
        print("FAILED")
        sys.exit(1)
