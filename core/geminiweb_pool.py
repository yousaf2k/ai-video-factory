"""
Thread-safe pool for GeminiWeb Worker Profile IDs.
Allows multiple Playwright instances to run concurrently without
locking the master Chrome profile.
"""
import queue
import config

_worker_queue = queue.LifoQueue()
_limit = getattr(config, 'CONCURRENT_GEMINIWEB_LIMIT', 5)

# Initialize the queue with worker IDs in reverse order so ID 1 is visited first
for i in range(_limit, 0, -1):  # Match exact concurrency limit
    _worker_queue.put(i)

# Pre-warm worker profiles in a background thread so the user doesn't face
# a 5-10 second disk-copy latency the very first time they generate something.
def _prewarm_workers():
    import os
    import shutil
    import time
    time.sleep(2)  # Wait for main server to boot properly
    
    # Determine profile path dynamically to avoid cached GEMINIWEB_CHROME_PROFILE on startup
    browser_type_name = getattr(config, 'PLAYWRIGHT_BROWSER', 'chromium').lower()
    profile_name = "chrome_profile"
    if browser_type_name == "firefox":
        profile_name = "firefox_profile"
    elif browser_type_name == "webkit":
        profile_name = "webkit_profile"
    else:
        channel = getattr(config, 'PLAYWRIGHT_CHANNEL', 'chrome')
        if channel and "msedge" in channel:
            profile_name = "edge_profile"
            
    output_dir = getattr(config, 'OUTPUT_DIR', 'output')
    master_profile = os.path.abspath(os.path.join(output_dir, profile_name))
    if not os.path.exists(master_profile):
        return
        
    ignore_func = shutil.ignore_patterns('*Cache*', '*cache*', 'Service Worker', 'Crashpad', '*OptGuideOnDeviceModel*', '*OptimizationGuide*')
    
    for i in range(1, _limit + 1):
        worker_profile = f"{master_profile}_worker_{i}"
        if not os.path.exists(worker_profile):
            try:
                shutil.copytree(master_profile, worker_profile, ignore=ignore_func)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Startup prewarm failed for {profile_name} worker {i}: {e}")

import threading
threading.Thread(target=_prewarm_workers, daemon=True).start()

def get_worker_id() -> int:
    """Acquire an available worker ID. Blocks until one is available."""
    return _worker_queue.get()

def release_worker_id(worker_id: int):
    """Release a worker ID back to the pool."""
    _worker_queue.put(worker_id)
