"""
Test script to verify Gemini integration setup
"""
import os
import sys
import io

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    try:
        from core.gemini_engine import ask
        print("[PASS] gemini_engine imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import gemini_engine: {e}")
        return False

    try:
        from core.image_generator import generate_image
        print("[PASS] image_generator imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import image_generator: {e}")
        return False

    try:
        import config
        print("[PASS] config imported successfully")
    except Exception as e:
        print(f"[FAIL] Failed to import config: {e}")
        return False

    return True

def test_config():
    """Test configuration values"""
    print("\nTesting configuration...")
    import config

    # Check API key
    if config.GEMINI_API_KEY and config.GEMINI_API_KEY != "your-gemini-api-key-here":
        print(f"[PASS] GEMINI_API_KEY is set ({config.GEMINI_API_KEY[:10]}...)")
    else:
        print("[FAIL] GEMINI_API_KEY is not set. Please set it in config.py")
        return False

    # Check models
    print(f"[INFO] Text model: {config.GEMINI_TEXT_MODEL}")
    print(f"[INFO] Image model: {config.GEMINI_IMAGE_MODEL}")

    # Check ComfyUI settings
    print(f"[INFO] ComfyUI URL: {config.COMFY_URL}")
    print(f"[INFO] Workflow path: {config.WORKFLOW_PATH}")
    print(f"[INFO] LoadImage node ID: {config.LOAD_IMAGE_NODE_ID}")
    print(f"[INFO] Motion prompt node ID: {config.MOTION_PROMPT_NODE_ID}")

    # Check output directory
    print(f"[INFO] Images output dir: {config.IMAGES_OUTPUT_DIR}")
    print(f"[INFO] Image aspect ratio: {config.IMAGE_ASPECT_RATIO}")
    print(f"[INFO] Image resolution: {config.IMAGE_RESOLUTION}")

    return True

def test_gemini_text():
    """Test Gemini text generation"""
    print("\nTesting Gemini text generation...")
    try:
        from core.gemini_engine import ask
        response = ask("Say 'Test successful' in exactly those words.")
        print(f"[PASS] Gemini response: {response}")
        return True
    except Exception as e:
        print(f"[FAIL] Gemini text generation failed: {e}")
        return False

def test_gemini_json():
    """Test Gemini JSON output"""
    print("\nTesting Gemini JSON generation...")
    try:
        from core.gemini_engine import ask
        import json
        response = ask(
            'Return JSON: {"status": "test", "value": 42}',
            response_format="application/json"
        )
        data = json.loads(response)
        print(f"[PASS] Gemini JSON response: {data}")
        return True
    except Exception as e:
        print(f"[FAIL] Gemini JSON generation failed: {e}")
        return False

def test_gemini_image():
    """Test Gemini image generation (optional - costs money)"""
    print("\nTesting Gemini image generation...")
    print("[WARN] This will use API credits. Skip if not needed.")

    response = input("Generate test image? (y/n): ").lower().strip()

    if response != 'y':
        print("[SKIP] Image generation test skipped")
        return True

    try:
        from core.image_generator import generate_image
        output_path = "output/generated_images/test.png"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        result = generate_image("A simple red circle on white background", output_path)

        if result and os.path.exists(result):
            print(f"[PASS] Test image generated: {result}")
            return True
        else:
            print(f"[FAIL] Image generation failed or file not found")
            return False
    except Exception as e:
        print(f"[FAIL] Gemini image generation failed: {e}")
        return False

def test_workflow_file():
    """Test that workflow file exists"""
    print("\nTesting workflow file...")
    import config
    import os

    if os.path.exists(config.WORKFLOW_PATH):
        print(f"[PASS] Workflow file found: {config.WORKFLOW_PATH}")
        return True
    else:
        print(f"[WARN] Workflow file not found: {config.WORKFLOW_PATH}")
        print("  Make sure to place your Wan 2.2 workflow JSON here.")
        return False

def test_input_file():
    """Test that input directory and idea file exist"""
    print("\nTesting input file...")
    idea_path = "input/video_idea.txt"

    if os.path.exists(idea_path):
        with open(idea_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                print(f"[PASS] Video idea file found with content")
                return True
            else:
                print(f"[WARN] Video idea file is empty: {idea_path}")
                return False
    else:
        print(f"[WARN] Video idea file not found: {idea_path}")
        print("  Create this file and add your video idea.")
        return False

def main():
    print("="*60)
    print("AI Film Studio - Gemini Integration Test")
    print("="*60)

    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Workflow File", test_workflow_file),
        ("Input File", test_input_file),
        ("Gemini Text", test_gemini_text),
        ("Gemini JSON", test_gemini_json),
        ("Gemini Image", test_gemini_image),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n[FAIL] Test '{test_name}' crashed: {e}")
            results[test_name] = False

    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: {test_name}")

    total = len(results)
    passed = sum(results.values())

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] All tests passed! System is ready.")
        print("\nNext steps:")
        print("1. Ensure ComfyUI is running at", os.getenv("COMFY_URL", "http://127.0.0.1:8188"))
        print("2. Run: python core/main.py")
    else:
        print("\n[WARNING] Some tests failed. Please fix the issues above.")
        print("See README_GEMINI_SETUP.md for setup instructions.")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
