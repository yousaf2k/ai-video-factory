import sys
from playwright.sync_api import sync_playwright
import time
import base64

with sync_playwright() as p:
    b = p.chromium.launch_persistent_context('E:/output/chrome_profile', headless=False)
    page = b.new_page()
    page.goto('https://gemini.google.com/app', wait_until='domcontentloaded')
    time.sleep(5)
    
    print("Looking for recent chats in sidebar...")
    try:
        # Gemini puts recent chats in list items typically inside a navigation bar
        recent_chats = page.query_selector_all('li.recent-container div[role="button"], a[role="link"]:has(div.recent-title), a.recent-conversation, div.recent-conversation')
        if recent_chats:
            print(f"Found {len(recent_chats)} recent chats. Clicking the first one...")
            recent_chats[0].click()
            time.sleep(5)
        else:
            print("No recent chats found in sidebar. Checking if it's already there...")
    except Exception as e:
        print("Error clicking recent chat:", e)
    
    print("Looking for videos on the page...")
    
    video_container_selectors = [
        'div[data-message-id] video',
        'div[data-message-id] .playable-media',
        'button.generated-video-button',
    ]

    download_button_selectors = [
        'button[aria-label="Download"]',
        'button[aria-label="Download video"]',
        'button[jsname][aria-label*="ownload"]',
        'a[download]',
    ]
    
    try:
        msgs = page.query_selector_all('message-content')
        if msgs:
            last = msgs[-1]
            print("Buttons in last message:")
            btns = last.query_selector_all('button')
            for btn in btns:
                label = btn.get_attribute('aria-label')
                title = btn.get_attribute('title')
                print(f"  - Button: aria-label='{label}', title='{title}'")
    except Exception as e:
        print("Error checking buttons:", e)
        
    def test_hover_dl(container, depth=0):
        if not container or depth > 5: return False
        try:
            container.scroll_into_view_if_needed()
            time.sleep(1)
            container.hover()
            time.sleep(2)
            
            print(f"Hovered at depth {depth}. Checking buttons...")
            for sel in download_button_selectors:
                btns = page.query_selector_all(sel)
                for btn in btns:
                    if btn.is_visible():
                        print(f"!!! FOUND VISIBLE DOWNLOAD BUTTON via '{sel}' at depth {depth} !!!")
                        print(f"  ARIA: {btn.get_attribute('aria-label')}")
                        return True
                        
            print("No visible download button yet. Ascending...")
            parent = container.evaluate_handle('el => el.parentElement')
            return test_hover_dl(parent, depth + 1)
        except Exception as e:
            print(f"Error at depth {depth}:", e)
            return False

    found_video = False
    for sel in video_container_selectors:
        containers = page.query_selector_all(sel)
        if containers:
            print(f"Found video using selector: {sel}")
            found_video = True
            test_hover_dl(containers[-1], 0)
            break
            
    if not found_video:
        print("No video found on the page! Test failed.")
        
    b.close()
