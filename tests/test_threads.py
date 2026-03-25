import asyncio
import traceback
from core.geminiweb_image_generator import _get_browser_context
from core.logger_config import get_logger

logger = get_logger(__name__)

def request_1():
    try:
        print("Request 1 starting...")
        ctx = _get_browser_context()
        print("Request 1 got ctx:", ctx)
        page = ctx.new_page()
        page.close()
    except Exception as e:
        print(f"Request 1 error: {repr(e)}")
        traceback.print_exc()

def request_2():
    try:
        print("Request 2 starting...")
        ctx = _get_browser_context()
        print("Request 2 got ctx:", ctx)
        page = ctx.new_page()
        page.close()
    except Exception as e:
        print(f"Request 2 error: {repr(e)}")
        traceback.print_exc()

async def main():
    print("Simulating web server thread pool issue...")
    
    # 1. First request runs in Thread A
    await asyncio.to_thread(request_1)
    
    # Wait a bit
    await asyncio.sleep(2)
    
    # 2. Force second request to run in Thread B by spinning up another thread concurrently
    # asyncio.to_thread reuses threads, so we might need to block the first thread
    # to force issue. But wait, `request_1` finished, so `asyncio.to_thread(request_2)` 
    # might reuse the same thread!
    # Let's see if we can force different threads.
    import threading
    def t2_wrapper():
        request_2()
    
    t2 = threading.Thread(target=t2_wrapper)
    t2.start()
    t2.join()

if __name__ == "__main__":
    asyncio.run(main())
