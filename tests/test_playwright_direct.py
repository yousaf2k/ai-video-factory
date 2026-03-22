import asyncio
import sys
import os

# Add AI folder to sys.path if not there
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "")))

from core.geminiweb_image_generator import generate_image_geminiweb

async def test():
    try:
        print("Testing geminiweb generator...")
        # Run it via to_thread just like the web server does
        result = await asyncio.to_thread(
            generate_image_geminiweb,
            "A test image of a futuristic city",
            "output/test_direct.png",
            "16:9"
        )
        print("Result:", result)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
