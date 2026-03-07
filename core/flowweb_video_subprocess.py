import sys
import os
import argparse
import time
import re
import json
from playwright.sync_api import sync_playwright

def run_flow_generation(image_path, prompt, output_path, aspect_ratio="16:9"):
    """
    Subprocess script to automate Google Flow video generation.
    - image_path: Path to reference image
    - prompt: Motion prompt/text description
    - output_path: Where to save final .mp4
    - aspect_ratio: '16:9' or '9:16'
    """
    print(f"Starting Google Flow Subprocess...")
    print(f"Image: {image_path}")
    print(f"Prompt: {prompt}")
    print(f"Output: {output_path}")

    # Use authenticated profile
    profile_path = 'e:/output/chrome_profile'
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch_persistent_context(
                profile_path,
                headless=False, # Keep headful to bypass some bot detection and for visibility if needed
                channel='chrome',
                args=['--disable-blink-features=AutomationControlled']
            )
            page = browser.new_page()
            
            # 1. Open Google Flow
            print("Navigating to Google Flow...")
            page.goto('https://labs.google/fx/tools/flow', wait_until='domcontentloaded')
            time.sleep(8)
            
            # 2. Check for "New project" button
            print("Creating new project...")
            new_btn = page.get_by_text("New project", exact=False).first
            if not new_btn.is_visible():
                new_btn = page.locator('button:has-text("New project")').first
            
            if new_btn.is_visible():
                new_btn.click()
            else:
                print("New project button not found, searching project ID in URL...")

            # Wait for project URL structure
            try:
                page.wait_for_url('**/project/**', timeout=20000)
            except:
                pass
            
            project_url = page.url
            print(f"Active Project URL: {project_url}")
            
            # 3. Configure Settings
            print("Configuring Generation Settings...")
            # Open settings panel
            settings_toggle = page.locator('button:has(i:has-text("crop_16_9")), button:has-text("Video"), button:has-text("Image")').first
            settings_toggle.click()
            time.sleep(2)
            
            # Select Video Mode
            page.get_by_text("Video", exact=True).click()
            
            # Select Aspect Ratio
            # Map "16:9" -> "Landscape", "9:16" -> "Portrait"
            ratio_text = "Landscape" if aspect_ratio == "16:9" else "Portrait"
            print(f"Setting Aspect Ratio: {ratio_text}")
            page.get_by_text(ratio_text).click()
            
            # Select 1 Variant
            page.get_by_role("button", name="1", exact=True).click()
            
            # Select Model (Veo 3.1 - Fast)
            page.get_by_text("Veo", exact=False).first.click()
            
            page.keyboard.press("Escape")
            time.sleep(1)
            
            # 4. Upload Image
            print("Expanding upload panel and selecting image...")
            # Click '+' to expand
            add_btn = page.locator('button:has(i:has-text("add_2"))').last
            add_btn.click()
            time.sleep(2)
            
            with page.expect_file_chooser() as fc:
                page.locator('button:has(i:has-text("upload"))').click()
            file_chooser = fc.value
            file_chooser.set_files(image_path)
            
            print("Image uploaded, waiting for processing...")
            time.sleep(15)
            
            # 5. Inject Prompt and Generate
            print("Injecting prompt...")
            text_area = page.locator('div[contenteditable="true"]')
            text_area.click()
            page.keyboard.type(prompt, delay=30)
            time.sleep(2)
            
            # Count current videos to detect when new one finishes
            initial_count = page.locator('video').count()
            
            print("Triggering Generation...")
            create_btn = page.locator('button:has(i:has-text("arrow_forward"))').last
            create_btn.click()
            
            # 6. Monitor Grid for New Video
            print("Monitoring grid for completion (max 5 minutes)...")
            start_time = time.time()
            found_new = False
            while time.time() - start_time < 300:
                current_count = page.locator('video').count()
                if current_count > initial_count or (initial_count == 0 and current_count > 0):
                    print(f"New video detected! Count: {current_count}")
                    found_new = True
                    break
                time.sleep(5)
            
            if not found_new:
                print("Generation monitoring timed out.")
            
            # 7. Download Video (Direct Fetch Strategy)
            print("Extracting video source for download...")
            time.sleep(5) # Give it a moment to stabilize the src attribute
            
            # Find the newest (usually first) video with a TRPC URL
            video_srcs = page.evaluate('''() => {
                return Array.from(document.querySelectorAll('video')).map(v => v.src);
            }''')
            
            target_src = None
            for s in video_srcs:
                if "/fx/api/trpc/media.getMediaUrlRedirect" in s:
                    target_src = s
                    break
            
            if not target_src and video_srcs:
                target_src = video_srcs[0] # Fallback to first video
            
            if target_src:
                full_url = "https://labs.google" + target_src if target_src.startswith('/') else target_src
                print(f"Downloading from source: {full_url}")
                
                response = page.request.get(full_url)
                if response.status == 200:
                    with open(output_path, 'wb') as f:
                        f.write(response.body())
                    print(f"SUCCESS: Video saved to {output_path}")
                else:
                    print(f"Download failed: HTTP {response.status}")
            else:
                print("FAILED: Could not find video source to download.")

            browser.close()

        except Exception as e:
            print(f"Subprocess Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--aspect_ratio", default="16:9")
    args = parser.parse_args()
    
    run_flow_generation(args.image, args.prompt, args.output, args.aspect_ratio)
