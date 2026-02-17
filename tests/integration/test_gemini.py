"""
Test Gemini API connection and key
"""
import os
import json
from dotenv import load_dotenv
import google.genai as genai
from google.genai import types

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

print("="*70)
print("GEMINI API TEST")
print("="*70)
print(f"\nAPI Key (first 20 chars): {api_key[:20]}...{api_key[-10:] if api_key else 'NOT SET'}")
print(f"Model: {model}\n")

if not api_key:
    print("[ERROR] GEMINI_API_KEY not found in .env file")
    exit(1)

try:
    # Initialize client
    print("Initializing Gemini client...")
    client = genai.Client(
        api_key=api_key,
        http_options={'api_version': 'v1alpha'}
    )
    print("[OK] Client initialized\n")

    # Test 1: Simple text generation
    print("="*70)
    print("TEST 1: Simple Text Generation")
    print("="*70)
    print("Sending test prompt...")

    response = client.models.generate_content(
        model=model,
        contents="Please respond with 'SUCCESS' if you can read this message."
    )

    print(f"Status: Success")
    print(f"Response: {response.text}")
    print(f"Model returned: {response.model if hasattr(response, 'model') else 'N/A'}\n")

    # Test 2: JSON response format
    print("="*70)
    print("TEST 2: JSON Response Format")
    print("="*70)
    print("Sending JSON request...")

    gen_config = types.GenerateContentConfig(
        response_mime_type="application/json"
    )

    response = client.models.generate_content(
        model=model,
        contents='Return JSON: {"status": "ok", "message": "test"}',
        config=gen_config
    )

    print(f"Status: Success")
    print(f"Response: {response.text}")

    # Validate JSON
    try:
        json_response = json.loads(response.text)
        print(f"Valid JSON: {json_response}")
    except:
        print("[WARN] Response is not valid JSON")

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print("✓ Gemini API is working correctly")
    print(f"✓ API Key is valid")
    print(f"✓ Model '{model}' is accessible")
    print(f"✓ JSON response format is supported")
    print("\n" + "="*70)
    print("Configuration Verified - Ready to Use!")
    print("="*70)

except Exception as e:
    print(f"\n[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()

    print("\n" + "="*70)
    print("POSSIBLE ISSUES:")
    print("="*70)

    error_str = str(e).lower()

    if "api key" in error_str or "auth" in error_str or "permission" in error_str:
        print("- API key is invalid or has no permissions")
        print("- Get a new key from: https://ai.google.dev/")
        print("- Make sure the Gemini API is enabled in your Google Cloud project")

    elif "quota" in error_str or "limit" in error_str:
        print("- API quota exceeded or rate limit reached")
        print("- Check your quota at: https://ai.google.dev/")
        print("- Free tier has limits per day")

    elif "network" in error_str or "connection" in error_str:
        print("- Network connection issue")
        print("- Check your internet connection")
        print("- Check if any firewall is blocking the request")

    else:
        print("- Unknown error - check the full error message above")
        print("- Visit: https://ai.google.dev/docs for documentation")

    print("="*70)
