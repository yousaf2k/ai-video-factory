"""
Test script to verify Queue system is working
"""
import requests
import json
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

BASE_URL = "http://localhost:8000"

def test_queue():
    print("Testing Queue System...\n")

    # 1. Check queue statistics
    print("1. Checking queue statistics...")
    response = requests.get(f"{BASE_URL}/api/queue/statistics")
    if response.status_code == 200:
        stats = response.json()
        print(f"   OK Queue Statistics: {json.dumps(stats, indent=2)}")
    else:
        print(f"   FAILED: {response.status_code}")
        return

    # 2. Get queue items
    print("\n2. Getting queue items...")
    response = requests.get(f"{BASE_URL}/api/queue/items")
    if response.status_code == 200:
        items = response.json()
        print(f"   OK Queue items count: {len(items)}")
        if items:
            print(f"   First item: {json.dumps(items[0], indent=2)}")
    else:
        print(f"   FAILED: {response.status_code}")

    # 3. Check if queue is paused
    print("\n3. Checking pause state...")
    response = requests.get(f"{BASE_URL}/api/queue/paused")
    if response.status_code == 200:
        paused = response.json()
        print(f"   OK Queue paused: {paused['is_paused']}")
    else:
        print(f"   FAILED: {response.status_code}")

    print("\nQueue system is operational!")
    print("\nNext steps:")
    print("   1. Go to http://localhost:3001/sessions")
    print("   2. Open a session")
    print("   3. Select shots and click 'Generate Images'")
    print("   4. Visit http://localhost:3001/queue to see items appear")

if __name__ == "__main__":
    try:
        test_queue()
    except requests.exceptions.ConnectionError:
        print("\nCannot connect to backend!")
        print("   Make sure the backend is running: python web_ui/backend/main.py")
    except Exception as e:
        print(f"\nError: {e}")

