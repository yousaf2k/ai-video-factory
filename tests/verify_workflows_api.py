import sys
import os
import asyncio
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

async def verify_workflows():
    try:
        from web_ui.backend.api.config import get_config
        
        # Call the get_config function directly
        config_data = await get_config()
        
        print("Available Video Workflows:")
        for wf in config_data.get("available_video_workflows", []):
            print(f"- {wf}")
            
        print("\nAvailable Image Workflows:")
        for wf in config_data.get("available_image_workflows", []):
            print(f"- {wf}")
            
        expected_video_workflows = ["wan22", "wan22_fix_slowmotion", "wan22_walk", "wan22_walk_full", "wan22_lora", "wan22_park", "wan22_pusa", "default"]
        expected_image_workflows = ["flux", "flux2", "flux2_hq", "flux2_api", "hidream_dev", "hidream_full", "turbo", "sdxl", "default"]
        
        missing_video = [wf for wf in expected_video_workflows if wf not in config_data.get("available_video_workflows", [])]
        missing_image = [wf for wf in expected_image_workflows if wf not in config_data.get("available_image_workflows", [])]
        
        success = True
        if missing_video:
            print(f"\nVerification FAILED: Missing video workflows: {missing_video}")
            success = False
        if missing_image:
            print(f"\nVerification FAILED: Missing image workflows: {missing_image}")
            success = False
            
        if success:
            print("\nVerification SUCCESS: All expected workflows are present.")
            
    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    asyncio.run(verify_workflows())
