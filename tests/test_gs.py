import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "")))

from web_ui.backend.services.generation_service import GenerationService

async def test():
    gs = GenerationService()
    print("Testing GenerationService directly...")
    try:
        result = await gs.regenerate_shot_image(
            session_id="session_20260226_135450", 
            shot_index=11, 
            force=True, 
            image_mode="geminiweb"
        )
        print("Result:", result)
    except Exception as e:
        import traceback
        print("EXCEPTION CAUGHT DIRECTLY:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
