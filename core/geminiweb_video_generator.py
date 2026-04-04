"""
GeminiWeb Video Generator - Browser-based video generation via gemini.google.com

Uses Playwright to automate Chrome browser, navigate to Gemini web UI,
upload a reference image, submit video generation prompts (using Veo 3.1), 
and download the resulting video.
"""
import os
import time
import subprocess
from pathlib import Path
from typing import Optional

import config
from core.logger_config import get_logger

logger = get_logger(__name__)

# Global lock removed in favor of worker profile cloning

def generate_video_geminiweb(
    image_path: str,
    motion_prompt: str,
    output_path: str,
    project_title: str = None,
    gemini_mode: str = None
) -> Optional[str]:
    """
    Generate a single video using Gemini web UI via browser automation.

    This method calls a standalone subprocess to handle the Playwright execution.
    This pattern completely isolates Playwright's asyncio event loop from the
    caller's event loop (preventing "Event loop is closed" errors on Windows).
    
    Args:
        image_path: Path to the reference image
        motion_prompt: The prompt describing the video motion/content
        output_path: Where to save the generated video file
        project_title: Optional title for Gemini Web chat persistence
        
    Returns:
        Path to the generated video file, or None if failed
    """
    logger.info("=" * 60)
    logger.info(f"Generating video via Gemini Web UI")
    logger.info(f"Output: {output_path}")
    logger.info("=" * 60)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Make paths absolute
    abs_image_path = os.path.abspath(image_path)
    abs_output_path = os.path.abspath(output_path)

    if not os.path.exists(abs_image_path):
        logger.error(f"Image path does not exist: {abs_image_path}")
        return None

    from core.geminiweb_pool import get_worker_id, release_worker_id
    import shutil
    
    worker_id = get_worker_id()
    try:
        # Determine profile path dynamically to avoid cached GEMINIWEB_CHROME_PROFILE
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
        worker_profile = f"{master_profile}_worker_{worker_id}"
        
        logger.info(f"Checking out {profile_name} worker {worker_id}...")
        
        # Only copy if it doesn't exist to save disk I/O, and ignore heavy cache folders
        if not os.path.exists(worker_profile) and os.path.exists(master_profile):
            ignore_func = shutil.ignore_patterns('*Cache*', '*cache*', 'Service Worker', 'Crashpad', '*OptGuideOnDeviceModel*', '*OptimizationGuide*')
            try:
                shutil.copytree(master_profile, worker_profile, ignore=ignore_func)
            except Exception as e:
                logger.warning(f"Profile copy warning for worker {worker_id}: {e}. "
                               f"This usually means your main browser window is open, locking some files. "
                               f"Close it for full profile replication.")
        elif not os.path.exists(worker_profile):
            os.makedirs(worker_profile, exist_ok=True)
            
        # Crucial: If reusing an existing worker profile, we MUST delete stale Chrome/Firefox locks 
        # otherwise Playwright will crash if the previous run was forcefully killed.
        for lock_file in ['SingletonLock', 'SingletonCookie', 'SingletonSocket', 'parent.lock', '.parentlock', 'lock']:
            lock_path = os.path.join(worker_profile, lock_file)
            if os.path.exists(lock_path):
                try:
                    if os.path.islink(lock_path):
                        os.unlink(lock_path)
                    else:
                        os.remove(lock_path)
                except Exception as e:
                    logger.warning(f"Failed to remove stale lock {lock_file}: {e}")
                    
        logger.debug(f"Starting subprocess with profile: {worker_profile} ...")
        
        cmd = [
            sys.executable,
            "-m",
            "core.geminiweb_video_subprocess",
            abs_image_path,
            motion_prompt,
            abs_output_path,
        ]
        if project_title:
            cmd.append(project_title)
            
        if worker_profile:
            cmd.extend(["--profile-dir", worker_profile])
            
        if gemini_mode:
            cmd.extend(["--gemini-mode", gemini_mode])
        
        try:
            # We use subprocess.run with capture_output=True to cleanly harvest
            # the printed result and avoid console garbling.
            process = subprocess.run(
                cmd,
                cwd=getattr(config, 'PROJECT_ROOT', os.getcwd()),
                capture_output=True,
                text=True,
                check=False  # Don't throw exception on non-zero exit, we handle it below
            )
            
            # Print the stdout line-by-line so it shows in our logger context
            for line in process.stdout.splitlines():
                if line.startswith("SUCCESS:"):
                    # Extract the path from the success marker
                    result_path = line.split("SUCCESS:", 1)[1].strip()
                    logger.info(f"Generating complete: {result_path}")
                    return result_path
                elif line == "FAILED":
                    logger.error("Subprocess reported failure.")
                    return None
                else:
                    logger.debug(f"[Subprocess] {line}")
            
            # Also log stderr if there is any
            if process.stderr:
                for line in process.stderr.splitlines():
                    logger.error(f"[Subprocess ERR] {line}")
            
            if process.returncode != 0:
                logger.error(f"Subprocess exit code {process.returncode}")
                
            return None
            
        except Exception as e:
            logger.error(f"Error launching subprocess: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    finally:
        release_worker_id(worker_id)
