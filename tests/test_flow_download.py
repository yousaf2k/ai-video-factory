from playwright.sync_api import sync_playwright
import time
import os

def test_flow_download_v2():
    project_id = '4afc953f-90d4-4777-b930-25af9c036ab2'
    project_url = f'https://labs.google/fx/tools/flow/project/{project_id}'
    
    print(f"Testing Download V2 (Direct DOM Evaluation) from: {project_url}")
    
    with sync_playwright() as p:
        try:
            b = p.chromium.launch_persistent_context(
                'e:/output/chrome_profile', 
                headless=False,
                channel='chrome',
                args=['--disable-blink-features=AutomationControlled']
            )
            page = b.new_page()
            
            print(f"Opening project URL...")
            page.goto(project_url, wait_until='networkidle')
            time.sleep(10)
            
            # Use evaluate to get ALL video srcs even if hidden
            print("Evaluating DOM to find video sources...")
            video_data = page.evaluate('''() => {
                const videos = Array.from(document.querySelectorAll('video'));
                return videos.map(v => ({
                    src: v.src,
                    visible: v.offsetWidth > 0 && v.offsetHeight > 0,
                    id: v.id || v.className
                }));
            }''')
            
            print(f"Found {len(video_data)} video elements in DOM.")
            for i, v in enumerate(video_data):
                print(f"Video {i}: src={v['src']}, visible={v['visible']}")

            # Filter for actual generated video URLs (the trpc ones)
            trpc_videos = [v for v in video_data if "/fx/api/trpc/media.getMediaUrlRedirect" in v['src']]
            print(f"Found {len(trpc_videos)} generated videos with TRPC URLs.")

            if not trpc_videos:
                print("No generated videos found. Falling back to any video src...")
                trpc_videos = [v for v in video_data if v['src']]

            if trpc_videos:
                target_src = trpc_videos[0]['src']
                full_url = "https://labs.google" + target_src if target_src.startswith('/') else target_src
                print(f"\nAttempting to download from: {full_url}")
                
                dl_path = 'c:/AI/ai_video_factory_v1/output/flow_direct_download.mp4'
                
                # Use page.request to fetch with browser cookies
                response = page.request.get(full_url)
                if response.status == 200:
                    with open(dl_path, 'wb') as f:
                        f.write(response.body())
                    print(f"SUCCESS: Video downloaded via direct fetch to {dl_path}")
                else:
                    print(f"Direct fetch failed: HTTP {response.status}")
            else:
                print("FAILED: No video sources found at all.")

        except Exception as e:
            print(f'Unhandled Error: {e}')

if __name__ == '__main__':
    test_flow_download_v2()
