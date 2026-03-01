"""
GeminiWeb Subprocess Helper — standalone Playwright script.

This script is invoked as a subprocess by generate_image_geminiweb().
Running Playwright in a fresh, isolated Python process avoids all asyncio
event-loop conflicts with FastAPI/Uvicorn on Windows.

Usage:
    python -m core.geminiweb_subprocess <prompt> <output_path> [aspect_ratio]

Exit code 0 and prints the output path on success, exit code 1 on failure.
"""
import sys
import os
import time
import json
import base64
import requests as http_requests
from pathlib import Path
from typing import Optional

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
from core.logger_config import get_logger

logger = get_logger(__name__)


def _create_browser_context(playwright_instance):
    """Create a persistent browser context with Chrome profile."""
    chrome_profile = getattr(config, 'GEMINIWEB_CHROME_PROFILE', None)
    if not chrome_profile:
        chrome_profile = os.path.join(
            getattr(config, 'OUTPUT_DIR', 'output'), 'chrome_profile'
        )
    os.makedirs(chrome_profile, exist_ok=True)
    logger.info(f"Using Chrome profile: {chrome_profile}")

    try:
        context = playwright_instance.chromium.launch_persistent_context(
            user_data_dir=chrome_profile,
            headless=False,
            channel="chrome",
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--no-default-browser-check',
            ],
            viewport={'width': 1280, 'height': 900},
            ignore_default_args=['--enable-automation'],
        )
        return context
    except Exception as e:
        logger.error(f"Failed to launch browser: {e}")
        raise


def _compose_prompt(image_prompt: str, aspect_ratio: str = None) -> str:
    """Compose the full prompt with aspect ratio instruction."""
    ar = aspect_ratio or getattr(config, 'IMAGE_ASPECT_RATIO', '16:9')
    ar_instruction = f"\n\nPlease generate the image in {ar} aspect ratio."
    return image_prompt + ar_instruction


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


def _download_image(page, image_src: str, output_path: str) -> Optional[str]:
    """Download the generated image from its source URL or data URI."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if image_src.startswith('data:image'):
        try:
            header, data = image_src.split(',', 1)
            image_data = base64.b64decode(data)
            with open(output_path, 'wb') as f:
                f.write(image_data)
            return output_path
        except Exception as e:
            logger.error(f"Failed to decode data URI: {e}")
            return None

    if image_src.startswith('blob:'):
        try:
            data_url = page.evaluate("""
                async (blobUrl) => {
                    const response = await fetch(blobUrl);
                    const blob = await response.blob();
                    return new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                    });
                }
            """, image_src)
            if data_url and ',' in data_url:
                header, data = data_url.split(',', 1)
                image_data = base64.b64decode(data)
                with open(output_path, 'wb') as f:
                    f.write(image_data)
                return output_path
        except Exception as e:
            logger.error(f"Failed to download blob URL: {e}")

    try:
        cookies = page.context.cookies()
        session = http_requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain', ''))
        response = session.get(image_src, timeout=30, stream=True)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(8192):
                f.write(chunk)
        return output_path
    except Exception as e:
        logger.error(f"Failed to download image via HTTP: {e}")

    try:
        img_elements = page.query_selector_all('img')
        for img in reversed(img_elements):
            src = img.get_attribute('src')
            if src == image_src:
                img.screenshot(path=output_path)
                return output_path
    except Exception as e:
        logger.error(f"Failed to screenshot image element: {e}")

    return None


def _try_download_full_size(page, output_path: str) -> Optional[str]:
    """Try to click the 'Download full-sized image' button and save it."""
    download_selectors = [
        'button[aria-label="Download"]',
        'button:has-text("Download")',
        'a[download]',
    ]
    for sel in download_selectors:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                with page.expect_download(timeout=15000) as download_info:
                    btn.click()
                download = download_info.value
                download.save_as(output_path)
                logger.info(f"Downloaded full-size image via button: {output_path}")
                return output_path
        except Exception:
            continue
    return None


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

            # Find input
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

            input_element.click()
            time.sleep(0.5)
            page.keyboard.press('Control+A')
            page.keyboard.press('Delete')
            time.sleep(0.3)

            # Enter prompt
            try:
                page.evaluate("""
                    async (text) => {
                        await navigator.clipboard.writeText(text);
                    }
                """, full_prompt)
                time.sleep(0.3)
                page.keyboard.press('Control+V')
                time.sleep(1)
            except Exception:
                page.keyboard.type(full_prompt, delay=5)
                time.sleep(1)

            actual_text = input_element.inner_text().strip()
            if len(actual_text) < 10:
                input_element.click()
                page.keyboard.press('Control+A')
                page.keyboard.press('Delete')
                time.sleep(0.3)
                page.keyboard.type(full_prompt, delay=5)
                time.sleep(1)

            time.sleep(1.5)

            # Send
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

            result = _try_download_full_size(page, output_path)
            if not result:
                result = _download_image(page, image_src, output_path)

            if result:
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
