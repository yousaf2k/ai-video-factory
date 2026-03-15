"""
GeminiWeb Image Generator - Browser-based image generation via gemini.google.com

Uses Playwright to automate Chrome browser, navigate to Gemini web UI,
submit image generation prompts (using NanoBanana Pro), and download
the resulting images.

Requires:
    - playwright>=1.40.0
    - One-time setup: playwright install chromium
    - Google account logged in (persisted via Chrome user profile)
"""
import os
import time
import base64
import requests as http_requests
from pathlib import Path
from typing import Optional

import config
from core.logger_config import get_logger

logger = get_logger(__name__)

import threading

_generation_lock = threading.Lock()

def _create_browser_context(playwright_instance):
    """
    Create a persistent browser context.
    Uses a Chrome user profile stored in GEMINIWEB_CHROME_PROFILE so that
    Google login persists across runs.
    """
    profile_dir = getattr(config, 'GEMINIWEB_CHROME_PROFILE',
                          os.path.join(config.ABS_OUTPUT_DIR, 'chrome_profile'))
    os.makedirs(profile_dir, exist_ok=True)

    logger.info(f"Launching browser with profile: {profile_dir}")

    context = playwright_instance.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        headless=False,  # Must be visible for Google login & interaction
        args=[
            '--disable-blink-features=AutomationControlled',
            '--no-first-run',
            '--no-default-browser-check',
        ],
        viewport={'width': 1280, 'height': 900},
        user_agent=(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/131.0.0.0 Safari/537.36'
        ),
        locale='en-US',
        timezone_id='America/New_York',
        ignore_default_args=['--enable-automation'],
    )

    logger.info("Browser context created successfully")
    return context


def _compose_prompt(image_prompt: str, aspect_ratio: str = None) -> str:
    """
    Compose the full prompt to send to Gemini, including aspect ratio instruction.

    Args:
        image_prompt: The image description prompt
        aspect_ratio: Desired aspect ratio (e.g., "16:9", "9:16", "1:1")

    Returns:
        Full prompt string for Gemini
    """
    if aspect_ratio is None:
        aspect_ratio = getattr(config, 'IMAGE_ASPECT_RATIO', '16:9')

    prompt = f"Generate an image: {image_prompt}. The aspect ratio should be {aspect_ratio}."
    return prompt


def _wait_for_response_complete(page, timeout: int = 180):
    """
    Wait for Gemini to finish processing the response.
    Gemini shows a thinking/processing indicator while generating.
    We wait for it to disappear, meaning the response is complete.
    
    Args:
        page: Playwright page object
        timeout: Maximum wait time in seconds
    """
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
        thinking = page.query_selector('.thoughts-header-button, .loading-indicator, .thinking-indicator')
        # The thinking button exists but check if actively spinning
        loading_dots = page.query_selector('div.loading-dots, span.loading')
        if loading_dots and loading_dots.is_visible():
            logger.debug("Loading dots visible, still generating...")
            time.sleep(2)
            continue
            
        # If no stop button and no loading, response might be done
        # Wait a brief moment and double-check
        time.sleep(2)
        stop_btn = page.query_selector('button[aria-label="Stop response"]')
        if not stop_btn or not stop_btn.is_visible():
            logger.info("Gemini response appears complete")
            return
        
        time.sleep(2)
    
    logger.warning(f"Response wait timed out after {timeout}s")


def _find_generated_image(page) -> Optional[str]:
    """
    Search the page for a generated image and return its src URL.
    
    Args:
        page: Playwright page object
        
    Returns:
        Image src URL/data URI, or None if not found
    """
    # Priority 1: Gemini wraps generated images in button.image-button
    image_selectors = [
        'button.image-button img[src]',
        'button.generated-image-button img[src]',
        'img.generated-image[src]',
    ]

    for selector in image_selectors:
        images = page.query_selector_all(selector)
        if images:
            last_image = images[-1]
            src = last_image.get_attribute('src')
            if src and not src.endswith('.svg') and 'logo' not in src.lower():
                logger.info(f"Found generated image (selector: {selector})")
                return src

    # Priority 2: Look for any image from Google's image hosting
    all_images = page.query_selector_all('img[src]')
    for img in reversed(all_images):
        src = img.get_attribute('src')
        if not src:
            continue
        # Filter for likely generated images
        if (
            'blob:' in src or
            src.startswith('data:image') or
            'lh3.googleusercontent.com' in src or
            'googleusercontent.com/image' in src
        ):
            # Make sure it's not a tiny icon or avatar
            try:
                box = img.bounding_box()
                if box and box['width'] > 100 and box['height'] > 100:
                    logger.info(f"Found generated image via fallback (size: {box['width']}x{box['height']})")
                    return src
            except Exception:
                logger.info("Found generated image via fallback selector")
                return src

    return None


def _wait_for_image_response(page, timeout: int = None) -> Optional[str]:
    """
    Wait for Gemini to generate and display an image in the response.
    
    First waits for the response to complete, then searches for the image.

    Args:
        page: Playwright page object
        timeout: Maximum wait time in seconds

    Returns:
        URL or data URI of the generated image, or None if failed
    """
    if timeout is None:
        timeout = getattr(config, 'GEMINIWEB_TIMEOUT', 120)

    logger.info(f"Waiting up to {timeout}s for image generation...")

    # Step 1: Wait for Gemini to finish generating the response
    _wait_for_response_complete(page, timeout)
    
    # Step 2: Give extra time for images to fully render
    time.sleep(5)
    
    # Step 3: Search for the generated image
    image_src = _find_generated_image(page)
    if image_src:
        return image_src
    
    # Step 4: Maybe the image needs scrolling to be visible
    logger.info("Image not found immediately, trying to scroll down...")
    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    time.sleep(3)
    
    image_src = _find_generated_image(page)
    if image_src:
        return image_src

    logger.warning("No generated image found in response")
    return None


def _download_image(page, image_src: str, output_path: str) -> Optional[str]:
    """
    Download the generated image from its source URL or data URI.

    Args:
        page: Playwright page object (used for context/cookies)
        image_src: Image URL or data URI
        output_path: Where to save the image

    Returns:
        Path to saved image, or None if failed
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if image_src.startswith('data:image'):
            # Handle data URI (base64 encoded)
            header, data = image_src.split(',', 1)
            image_bytes = base64.b64decode(data)

            with open(output_path, 'wb') as f:
                f.write(image_bytes)

            logger.info(f"Saved image from data URI: {output_path}")

        elif image_src.startswith('blob:'):
            # Handle blob URLs — convert via JavaScript in the page context
            logger.info("Image is a blob URL, extracting via page context...")

            base64_data = page.evaluate("""
                async (blobUrl) => {
                    try {
                        const response = await fetch(blobUrl);
                        const blob = await response.blob();
                        return new Promise((resolve, reject) => {
                            const reader = new FileReader();
                            reader.onloadend = () => resolve(reader.result);
                            reader.onerror = reject;
                            reader.readAsDataURL(blob);
                        });
                    } catch (e) {
                        return null;
                    }
                }
            """, image_src)

            if base64_data and ',' in base64_data:
                _, data = base64_data.split(',', 1)
                image_bytes = base64.b64decode(data)

                with open(output_path, 'wb') as f:
                    f.write(image_bytes)

                logger.info(f"Saved image from blob: {output_path}")
            else:
                logger.warning("Could not extract blob, falling back to screenshot")
                return _screenshot_image(page, output_path)

        else:
            # Regular URL — download it with auth cookies
            cookies = page.context.cookies()
            cookie_header = '; '.join(f"{c['name']}={c['value']}" for c in cookies
                                       if 'google' in c.get('domain', ''))

            headers = {
                'User-Agent': page.evaluate('navigator.userAgent'),
                'Cookie': cookie_header,
                'Referer': 'https://gemini.google.com/',
            }

            response = http_requests.get(image_src, headers=headers, timeout=30)

            if response.status_code == 200 and len(response.content) > 100:
                with open(output_path, 'wb') as f:
                    f.write(response.content)

                logger.info(f"Downloaded image: {output_path}")
            else:
                logger.warning(
                    f"Failed to download image (status: {response.status_code}), "
                    "falling back to screenshot"
                )
                return _screenshot_image(page, output_path)

        # Verify file was created and has content
        if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
            return output_path

        logger.error("Downloaded image file is empty or missing")
        return None

    except Exception as e:
        logger.error(f"Failed to download image: {e}")
        return _screenshot_image(page, output_path)


def _screenshot_image(page, output_path: str) -> Optional[str]:
    """
    Fallback: take a screenshot of the generated image element.

    Args:
        page: Playwright page object
        output_path: Where to save the screenshot

    Returns:
        Path to saved screenshot, or None if failed
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Try to screenshot just the image element
        image_selectors = [
            'button.image-button img',
            'button.generated-image-button img',
            'div[data-message-id] img',
        ]

        for selector in image_selectors:
            images = page.query_selector_all(selector)
            if images:
                last_image = images[-1]
                last_image.screenshot(path=output_path)
                logger.info(f"Screenshot saved: {output_path}")
                return output_path

        # Ultimate fallback: screenshot the whole page
        logger.warning("No image element found, taking full page screenshot")
        page.screenshot(path=output_path, full_page=False)
        return output_path

    except Exception as e:
        logger.error(f"Screenshot fallback failed: {e}")
        return None


def _try_download_full_size(page, output_path: str) -> Optional[str]:
    """
    Try to click the 'Download full-sized image' button and save it.
    Gemini provides a download button for generated images.
    
    Args:
        page: Playwright page object
        output_path: Where to save the image
        
    Returns:
        Path to saved image, or None if not available
    """
    try:
        # Look for the download button
        download_selectors = [
            'button[aria-label="Download full-sized image"]',
            'button.generated-image-button',
            'button[aria-label="Download"]',
        ]
        
        for selector in download_selectors:
            btn = page.query_selector(selector)
            if btn and btn.is_visible():
                # Set up download handler
                with page.expect_download(timeout=30000) as download_info:
                    btn.click()
                download = download_info.value
                download.save_as(output_path)
                logger.info(f"Downloaded full-size image via button: {output_path}")
                return output_path
                
    except Exception as e:
        logger.debug(f"Full-size download not available: {e}")
    
    return None


def generate_image_geminiweb(
    prompt: str,
    output_path: str,
    aspect_ratio: str = None,
    resolution: str = None,
    seed: int = None,
    project_title: str = None
) -> Optional[str]:
    """
    Generate a single image using Gemini web UI via browser automation.

    This method launches Chrome (or reuses an existing instance), navigates to
    gemini.google.com/app, submits the image prompt with aspect ratio, waits for
    the image to be generated, and downloads it.

    Args:
        prompt: Text description of the image to generate
        output_path: Full path where the image will be saved
        aspect_ratio: Optional aspect ratio override (e.g., "16:9")
        resolution: Not used for GeminiWeb mode (kept for API consistency)
        seed: Not used for GeminiWeb mode (kept for API consistency)
        project_title: Optional title for Gemini Web chat persistence

    Returns:
        Path to the generated image file, or None if failed
    """
    logger.info(f"Generating image (GeminiWeb): {output_path}")
    logger.debug(f"  Prompt: {prompt[:100]}...")
    logger.debug(f"  Aspect ratio: {aspect_ratio or config.IMAGE_ASPECT_RATIO}")

    gemini_url = getattr(config, 'GEMINIWEB_URL', 'https://gemini.google.com/app')
    timeout = getattr(config, 'GEMINIWEB_TIMEOUT', 120)

    # Run Playwright in a completely separate Python process to avoid
    # asyncio event loop conflicts with FastAPI/Uvicorn on Windows.
    # The subprocess approach is the only reliable way to use Playwright's
    # sync_api from within an async web server.
    import subprocess
    import sys

    script_path = os.path.join(os.path.dirname(__file__), 'geminiweb_subprocess.py')

    cmd = [
        sys.executable, script_path,
        prompt, output_path,
    ]
    if aspect_ratio:
        cmd.extend(['--aspect-ratio', aspect_ratio])
    if project_title:
        cmd.extend(['--project-title', project_title])

    try:
        with _generation_lock:
            logger.info(f"Launching GeminiWeb subprocess: {script_path}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 120,  # extra buffer for the subprocess
                cwd=os.path.dirname(os.path.dirname(__file__)),
            )

            logger.debug(f"Subprocess stdout: {result.stdout[:500]}")
            if result.stderr:
                logger.debug(f"Subprocess stderr: {result.stderr[:500]}")

            if result.returncode == 0:
                # Parse the output path from stdout
                for line in result.stdout.strip().split('\n'):
                    if line.startswith('SUCCESS:'):
                        generated_path = line[len('SUCCESS:'):].strip()
                        if os.path.exists(generated_path):
                            file_size = os.path.getsize(generated_path)
                            logger.info(f"Generated (GeminiWeb): {generated_path} ({file_size:,} bytes)")
                            print(f"[PASS] Generated (GeminiWeb): {generated_path}")
                            return generated_path

                # If we got exit 0 but no SUCCESS line, check if the file exists
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    logger.info(f"Generated (GeminiWeb): {output_path} ({file_size:,} bytes)")
                    print(f"[PASS] Generated (GeminiWeb): {output_path}")
                    return output_path

                logger.error("Subprocess exited 0 but no image file found")
                return None
            else:
                logger.error(f"GeminiWeb subprocess failed (exit code {result.returncode})")
                logger.error(f"stdout: {result.stdout}")
                logger.error(f"stderr: {result.stderr}")
                print(f"[FAIL] GeminiWeb subprocess failed")
                return None

    except subprocess.TimeoutExpired:
        logger.error(f"GeminiWeb subprocess timed out after {timeout + 120}s")
        print("[FAIL] GeminiWeb: Subprocess timed out")
        return None
    except Exception as e:
        import traceback
        logger.error(f"Failed to generate image (GeminiWeb): {e}\n{traceback.format_exc()}")
        print(f"[FAIL] Failed to generate image (GeminiWeb): {e}")
        return None


def cleanup_browser():
    """
    Close the browser context and Playwright instance.
    No longer needed as contexts are managed per request.
    """
    logger.info("Browser cleanup complete (No-op)")
