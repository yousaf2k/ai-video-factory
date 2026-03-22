from playwright.sync_api import sync_playwright
import time

def test_flow_prompt():
    print("Testing Flow Prompt Injection...")
    with sync_playwright() as p:
        try:
            b = p.chromium.launch_persistent_context(
                'e:/output/chrome_profile', 
                headless=False,
                channel='chrome',
                args=['--disable-blink-features=AutomationControlled']
            )
            page = b.new_page()
            page.goto('https://labs.google/fx/tools/flow/project/4afc953f-90d4-4777-b930-25af9c036ab2', wait_until='domcontentloaded')
            
            print('Waiting for page to load for 20 seconds...')
            time.sleep(20)
            
            # Find the main text area (which uses Slate editor and is contenteditable)
            print('Finding text area...')
            text_area = page.locator('div[contenteditable="true"]')
            text_area.wait_for(state='visible', timeout=10000)
            
            print('Clicking text area...')
            text_area.click()
            
            print('Typing prompt...')
            page.keyboard.type('A futuristic city in the clouds, high detail', delay=50)
            time.sleep(2)
            
            print('Finding create button...')
            # The create button has an aria-label or just the text "Create"
            # In the DOM there is a button with a span that says "Create" Next to Video x2
            create_btn = page.locator('button:has(span:has-text("Create"))').last
            
            print('Clicking create button...')
            create_btn.click()
            
            print('Waiting 20 seconds to see the result...')
            time.sleep(20)
            
        except Exception as e:
            print(f'Error: {e}')

if __name__ == '__main__':
    test_flow_prompt()
