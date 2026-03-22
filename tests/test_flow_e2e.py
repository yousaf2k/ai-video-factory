from playwright.sync_api import sync_playwright
import time
import re
import os

def test_flow_e2e():
    test_image_path = 'E:/output/projects/1.jpg'
    if not os.path.exists(test_image_path):
        print(f"Test image not found at {test_image_path}, please specify a valid image path.")
        return

    print("Testing End-to-End Flow Video Generation...")
    with sync_playwright() as p:
        try:
            b = p.chromium.launch_persistent_context(
                'e:/output/chrome_profile', 
                headless=False,
                channel='chrome',
                args=['--disable-blink-features=AutomationControlled']
            )
            page = b.new_page()
            
            # Step 1: Open URL
            print("1. Opening https://labs.google/fx/tools/flow...")
            page.goto('https://labs.google/fx/tools/flow', wait_until='domcontentloaded')
            time.sleep(10)
            
            # Step 2: Press + New project
            print("2. Clicking '+ New project'...")
            new_project_btn = page.get_by_text("New project", exact=False).first
            if new_project_btn.is_visible():
                new_project_btn.click()
            else:
                new_project_btn = page.locator('button:has-text("New project")').first
                if new_project_btn.is_visible():
                    new_project_btn.click()
                else:
                    print("Could not find 'New project' button. You might already be in a project or the UI changed.")
            
            # Wait for project URL
            print("Waiting for project to load (URL should contain /project/)...")
            try:
                page.wait_for_url('**/project/**', timeout=30000)
            except Exception:
                print("Failed to navigate to project URL. Current URL:", page.url)

            project_url = page.url
            print(f"Current URL: {project_url}")
            match = re.search(r'/project/([a-zA-Z0-9\-]+)', project_url)
            if match:
                project_id = match.group(1)
                print(f"SUCCESS: Extracted Project ID: {project_id}")
            else:
                print("Could not extract Project ID from URL.")
            
            time.sleep(5)
            
            # Configure Options
            print("Configuring settings for Video...")
            settings_toggle = page.locator('button:has(i:has-text("crop_16_9")), button:has-text("Video"), button:has-text("Image")').first
            settings_toggle.click()
            time.sleep(2)
            
            print("Selecting 'Video'...")
            try:
                page.get_by_text("Video", exact=True).click()
            except: pass

            print("Selecting 'Landscape'...")
            try:
                page.get_by_text("Landscape").click()
            except: pass
                
            print("Selecting 1 variant...")
            try:
                page.get_by_role("button", name="1", exact=True).click()
            except: pass
                
            print("Selecting 'Veo 3.1 - Fast' model...")
            try:
                page.get_by_text("Veo", exact=False).first.click()
            except: pass
                
            page.keyboard.press("Escape")
            time.sleep(1)

            # 5. Press + to expand dialog and upload image
            print("Clicking '+' to expand panel...")
            add_btn = page.locator('button:has(i:has-text("add_2"))').last
            add_btn.click()
            time.sleep(2)
            
            print("Clicking upload icon button and waiting for file chooser...")
            with page.expect_file_chooser() as fc_info:
                page.locator('button:has(i:has-text("upload"))').click()
            
            file_chooser = fc_info.value
            print(f"Uploading file: {test_image_path}...")
            file_chooser.set_files(test_image_path)
            
            print("Waiting for image to process...")
            time.sleep(15)
            
            # 6. Enter prompt
            print("Clicking text box...")
            text_area = page.locator('div[contenteditable="true"]')
            text_area.click()
            
            print("Entering prompt...")
            page.keyboard.type("A cinematic shot, dynamic motion, futuristic aesthetics", delay=50)
            time.sleep(2)
            
            # 7. Press Right Arrow icon to generate
            print("Clicking the create (arrow-forward) button...")
            create_btn = page.locator('button:has(i:has-text("arrow_forward"))').last
            create_btn.click()
            
            print("WAITING FOR GENERATION TO FINISH AND GRID TO UPDATE...")
            initial_count = page.locator('video').count()
            print(f"Initial video count: {initial_count}")
            
            print("Monitoring grid for new video...")
            start_time = time.time()
            new_video_found = False
            while time.time() - start_time < 300: # 5 minute timeout
                current_count = page.locator('video').count()
                if current_count > initial_count or (initial_count == 0 and current_count > 0):
                    print(f"New video detected! Current count: {current_count}")
                    new_video_found = True
                    break
                time.sleep(5)
            
            if not new_video_found:
                print("Timed out waiting for new video in grid.")
            
            print("Fetching all video sources from the page...")
            video_srcs = page.evaluate('''() => {
                const videos = Array.from(document.querySelectorAll('video'));
                return videos.map(v => v.src);
            }''')
            print(f"Found video srcs: {video_srcs}")
            
            # The newest video's src should be here
            # We'll try to find a /fx/api/trpc/... src
            target_src = None
            for s in video_srcs:
                if "/fx/api/trpc/media.getMediaUrlRedirect" in s:
                    target_src = s
                    break
            
            if not target_src and video_srcs:
                target_src = video_srcs[0]
            
            if target_src:
                full_url = "https://labs.google" + target_src if target_src.startswith('/') else target_src
                print(f"Attempting to download from {full_url}...")
                dl_path = 'c:/AI/ai_video_factory_v1/output/flow_test_download.mp4'
                
                try:
                    response = page.request.get(full_url)
                    if response.status == 200:
                        with open(dl_path, 'wb') as f:
                            f.write(response.body())
                        print(f"SUCCESS: Video downloaded via direct fetch to {dl_path}")
                        return
                    else:
                        print(f"Failed to fetch video: HTTP {response.status}")
                except Exception as e:
                    print(f"Error during direct fetch: {e}")
            
            # If direct fetch failed or no src, try UI click as fallback
            print("Fallback: Attempting UI download click...")
            video_locator = page.locator('video').first
            try:
                container = video_locator.locator('xpath=ancestor::div[contains(@class, "sc-")]').first
                download_btns = container.locator('button:has(i:has-text("download")), button[aria-label*="download"], button[aria-label*="Download"]')
                
                if download_btns.count() > 0:
                    print("Found download button. Clicking...")
                    with page.expect_download(timeout=60000) as download_info:
                        download_btns.first.click(force=True)
                    download = download_info.value
                    download.save_as('c:/AI/ai_video_factory_v1/output/flow_test_download.mp4')
                    print("SUCCESS: Video downloaded via UI click.")
                else:
                    print("No download button found via UI.")
            except Exception as e:
                print(f"UI download failed: {e}")

        except Exception as e:
            print(f'Unhandled Error: {e}')

if __name__ == '__main__':
    test_flow_e2e()
