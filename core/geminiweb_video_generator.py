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

import threading
_generation_lock = threading.Lock()

def generate_video_geminiweb(
    image_path: str,
    motion_prompt: str,
    output_path: str,
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

    # We use a global lock to strictly enforce ONE browser running at a time
    with _generation_lock:
        logger.debug("Acquired generation lock. Starting subprocess...")
        
        args = [
            "python",
            "-m",
            "core.geminiweb_video_subprocess",
            abs_image_path,
            motion_prompt,
            abs_output_path
        ]
        
        try:
            # We use subprocess.run with capture_output=True to cleanly harvest
            # the printed result and avoid console garbling.
            process = subprocess.run(
                args,
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
