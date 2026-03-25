
import os
import sys
import subprocess
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import config

def launch_native():
    profile_path = getattr(config, 'GEMINIWEB_CHROME_PROFILE', None)
    os.makedirs(profile_path, exist_ok=True)
    
    print(f"Using Profile Path: {profile_path}")
    print("-" * 50)
    print("IMPORTANT: Close ALL other browser windows (Chrome/Edge/Firefox) before running this!")
    print("Login here, then CLOSE this browser window before running the AI.")
    print("-" * 50)

    # Try to find Chrome or Edge on Windows
    # Common paths for Chrome
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    
    # Common paths for Edge
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]

    # Common paths for Firefox
    firefox_paths = [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Mozilla Firefox\firefox.exe"),
    ]

    # --- Playwright Browser Discovery ---
    playwright_root = os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright")
    pw_firefox_paths = []
    pw_chromium_paths = []
    
    if os.path.exists(playwright_root):
        import glob
        pw_firefox_paths = glob.glob(os.path.join(playwright_root, "firefox-*", "firefox", "firefox.exe"))
        pw_chromium_paths = glob.glob(os.path.join(playwright_root, "chromium-*", "chrome-win", "chrome.exe"))
        # Sort to get the latest version
        pw_firefox_paths.sort(reverse=True)
        pw_chromium_paths.sort(reverse=True)

    print(f"Discovered Playwright Firefox: {pw_firefox_paths}")
    print(f"Discovered Playwright Chromium: {pw_chromium_paths}")

    browser_exe = None
    
    # Check config for preference
    browser_type_name = getattr(config, 'PLAYWRIGHT_BROWSER', 'chromium').lower()
    channel = getattr(config, 'PLAYWRIGHT_CHANNEL', 'chrome').lower()
    
    print(f"Configured Browser: {browser_type_name}")
    print(f"Configured Channel: {channel}")
    
    search_list = []
    if browser_type_name == "firefox":
        # Prioritize system Firefox for the most "native" login experience
        search_list = firefox_paths + pw_firefox_paths + chrome_paths + edge_paths
    elif 'edge' in channel:
        search_list = edge_paths + pw_chromium_paths + chrome_paths + firefox_paths
    else:
        # Prio: System Chrome -> Playwright Chrome -> Edge -> Firefox
        search_list = chrome_paths + pw_chromium_paths + edge_paths + firefox_paths
        
    for path in search_list:
        if os.path.exists(path):
            browser_exe = path
            break
            
    if not browser_exe:
        print("Could not find Chrome, Edge, or Firefox automatically.")
        print("Searched paths:")
        for p in search_list:
            print(f"  - {p}")
        return

    print(f"Selected Browser: {browser_exe}")
    
    # Launch with the correct profile flag
    # Firefox uses -profile, Chromium uses --user-data-dir
    if "firefox.exe" in browser_exe.lower():
        # Space separation is more robust for Firefox CLI
        cmd = [
            browser_exe,
            "-profile",
            str(profile_path),
            "-no-remote",
            "https://gemini.google.com/app"
        ]
    else:
        cmd = [
            browser_exe,
            f"--user-data-dir={profile_path}",
            "--new-window",
            "https://gemini.google.com/app"
        ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        subprocess.Popen(cmd)
        print("\nBrowser launched. Login and then close it completely.")
    except Exception as e:
        print(f"Error launching browser: {e}")

if __name__ == "__main__":
    launch_native()
