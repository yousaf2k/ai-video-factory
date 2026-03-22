import sys
from playwright.sync_api import sync_playwright
import time
import base64
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

output_path = 'c:/AI/ai_video_factory_v1/output/test_download.mp4'

def _try_download_native(page, output_path: str):
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

    def _do_hover_and_download(container, depth=0):
        if not container or depth > 4:
            return None
            
        try:
            container.scroll_into_view_if_needed()
            time.sleep(1)
            container.hover()
            time.sleep(2.0)
            
            for btn_sel in download_button_selectors:
                try:
                    btns = page.query_selector_all(btn_sel)
                    if btns:
                        for btn in reversed(btns):
                            if btn.is_visible():
                                logger.info(f"Clicking download button: {btn_sel} (at DOM depth {depth})")
                                with page.expect_download(timeout=10000) as dl_info:
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
                logger.info(f"Found video base element: {sel}")
                
                path = _do_hover_and_download(video_element, 0)
                if path: 
                    return path

        if not video_element:
            logger.warning("No video element found to hover.")
            return None
    except Exception as e:
        logger.debug(f"Native download preparation failed: {e}")
    return None

def _download_video_fallback(page, output_path: str):
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

with sync_playwright() as p:
    try:
        b = p.chromium.launch_persistent_context(
            'e:/output/chrome_profile', 
            headless=False,
            channel="chrome",
            args=['--disable-blink-features=AutomationControlled']
        )
    except Exception as e:
        print(f"\\n--- BROWSER LAUNCH FAILED ---\\nError: {e}")
        sys.exit(1)
        
    page = b.new_page()
    page.goto('https://gemini.google.com/app/88752a6331830739', wait_until='domcontentloaded')
    time.sleep(10)
    
    # Try native first
    res = _try_download_native(page, output_path)
    if res:
        print("Native downloaded!")
    else:
        print("Native failed, trying fallback...")
        res2 = _download_video_fallback(page, output_path)
        if res2:
            print("Fallback downloaded!")
        else:
            print("All failed.")
            page.screenshot(path='c:/AI/ai_video_factory_v1/output/dl_test_fail.png')
            
            # Dump HTML to see what's really there
            html = page.evaluate("document.body.innerHTML")
            with open('c:/AI/ai_video_factory_v1/output/dl_test_fail.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("Saved DOM to output/dl_test_fail.html")
    b.close()
