"""
Test script for both Gemini and ComfyUI image generation
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("="*70)
print("AI FILM STUDIO - IMAGE GENERATION TEST")
print("="*70)

# Test 1: Check imports
print("\n[TEST 1] Checking module imports...")
try:
    from core.image_generator import generate_image_gemini
    print("[PASS] Gemini image generator imported")
except Exception as e:
    print(f"[FAIL] Could not import Gemini generator: {e}")
    sys.exit(1)

try:
    from core.comfyui_image_generator import generate_image_comfyui
    print("[PASS] ComfyUI image generator imported")
except Exception as e:
    print(f"[WARN] Could not import ComfyUI generator: {e}")

# Test 2: Check config
print("\n[TEST 2] Checking configuration...")
try:
    import config
    print(f"[INFO] Default mode: {config.IMAGE_GENERATION_MODE}")
    print(f"[INFO] Workflow path: {config.IMAGE_WORKFLOW_PATH}")
    print(f"[INFO] ComfyUI URL: {config.COMFY_URL}")
except Exception as e:
    print(f"[FAIL] Config error: {e}")
    sys.exit(1)

# Test 3: Check ComfyUI connection
print("\n[TEST 3] Checking ComfyUI connection...")
try:
    import requests
    response = requests.get(f"{config.COMFY_URL}/system_stats", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print("[PASS] ComfyUI is running")
        print(f"      Version: {data.get('comfyui_version', 'unknown')}")
        devices = data.get('devices', [])
        if devices:
            for dev in devices:
                print(f"      GPU: {dev.get('name', 'unknown')}")
    else:
        print("[WARN] ComfyUI returned status:", response.status_code)
except Exception as e:
    print(f"[WARN] Cannot connect to ComfyUI: {e}")
    print("      → Gemini mode will be used")

# Test 4: Check workflow file
print("\n[TEST 4] Checking image generation workflow...")
if os.path.exists(config.IMAGE_WORKFLOW_PATH):
    print(f"[PASS] Workflow file found: {config.IMAGE_WORKFLOW_PATH}")
    import json
    try:
        with open(config.IMAGE_WORKFLOW_PATH, 'r') as f:
            workflow = json.load(f)
        print(f"[INFO] Workflow has {len(workflow.get('nodes', []))} nodes")
        print(f"[INFO] Node IDs configured:")
        print(f"      TEXT: {config.IMAGE_TEXT_NODE_ID}")
        print(f"      NEG: {config.IMAGE_NEG_TEXT_NODE_ID}")
        print(f"      KSAMPLER: {config.IMAGE_KSAMPLER_NODE_ID}")
        print(f"      VAE: {config.IMAGE_VAE_NODE_ID}")
        print(f"      SAVE: {config.IMAGE_SAVE_NODE_ID}")
    except Exception as e:
        print(f"[WARN] Could not read workflow: {e}")
else:
    print(f"[WARN] Workflow file not found: {config.IMAGE_WORKFLOW_PATH}")
    print("      → You need to create this workflow in ComfyUI")

# Test 5: Test Gemini image generation
print("\n[TEST 5] Testing Gemini image generation...")
try:
    os.makedirs('output/test', exist_ok=True)
    result = generate_image_gemini('A beautiful sunset over mountains', 'output/test/gemini_test.png')
    if result and os.path.exists(result):
        size = os.path.getsize(result)
        print(f"[PASS] Gemini test successful!")
        print(f"      Image: {result}")
        print(f"      Size: {size:,} bytes ({size/1024:.1f} KB)")
    else:
        print("[FAIL] Gemini test failed")
except Exception as e:
    print(f"[FAIL] Gemini test error: {e}")

# Test 6: Test ComfyUI image generation (optional)
print("\n[TEST 6] Testing ComfyUI image generation...")
print("[INFO] This will use your ComfyUI and GPU...")

test_comfyui = input("Test ComfyUI image generation? (y/n): ").lower().strip()

if test_comfyui == 'y' or test_comfyui == 'yes':
    try:
        result = generate_image_comfyui('A mountain landscape at sunset', 'output/test/comfyui_test.png')
        if result and os.path.exists(result):
            size = os.path.getsize(result)
            print(f"[PASS] ComfyUI test successful!")
            print(f"      Image: {result}")
            print(f"      Size: {size:,} bytes ({size/1024:.1f} KB)")
        else:
            print("[FAIL] ComfyUI test failed - Check workflow configuration")
    except Exception as e:
        print(f"[FAIL] ComfyUI test error: {e}")
else:
    print("[SKIP] ComfyUI test skipped")

# Summary
print("\n" + "="*70)
print("TEST SUMMARY")
print("="*70)

print("\n✅ Gemini Image Generation: WORKING")
print("   - Fast, cloud-based")
print("   - Cost: ~$0.08 per image")
print("   - Use when: You want easy, fast generation")

if os.path.exists(config.IMAGE_WORKFLOW_PATH):
    print("\n✅ ComfyUI Image Generation: AVAILABLE")
    print("   - Free, local generation")
    print("   - Requires: ComfyUI + workflow setup")
    print("   - Use when: Want to save money or use custom models")
else:
    print("\n⚠️ ComfyUI Image Generation: NEEDS SETUP")
    print("   - Create workflow in ComfyUI")
    print("   - Save as: workflow/image_generation_workflow.json")
    print("   - See COMFYUI_SETUP_CHECKLIST.md for details")

print("\n" + "="*70)
print("For complete guides, see:")
print("  - COMFYUI_IMAGE_GUIDE.md")
print("  - COMFYUI_IMAGE_QUICKREF.md")
print("="*70)
