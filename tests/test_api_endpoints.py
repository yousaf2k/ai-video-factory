import urllib.request
import json
import sys

def test_endpoint(url):
    print(f"Testing {url}...")
    try:
        response = urllib.request.urlopen(url, timeout=5)
        status = response.getcode()
        content = response.read().decode('utf-8')
        print(f"SUCCESS: Status {status}")
        try:
            data = json.loads(content)
            print(f"JSON Items: {len(data) if isinstance(data, list) else 'Dict'}")
        except:
             print("Content is not JSON or empty")
        return True
    except urllib.error.HTTPError as e:
        print(f"HTTP ERROR: {e.code} - {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"URL ERROR: {e.reason}")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    base_url = "http://127.0.0.1:8000"
    
    # Test Root
    test_endpoint(f"{base_url}/")
    
    # Test Sessions
    test_endpoint(f"{base_url}/api/sessions")
    
    # Test Queue Items
    test_endpoint(f"{base_url}/api/queue/items")
