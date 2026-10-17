"""
FlowWeb Image Generator - Browser-based image generation via flow.google.com

Google Flow (https://flow.google.com/) project automation: reuses the
project's Flow workspace (creates it on first use, opens it by clicking its
card afterwards), aligns the Image-mode settings (aspect ratio, model,
outputs; Agent stays off), submits the prompt and downloads the result.

Runs Playwright in an isolated subprocess (see flowweb_image_subprocess.py)
and clones worker profiles from the shared GeminiWeb Chrome profile, so the
Google login persists and parallel workers don't lock the master profile.
"""
import os
import subprocess
import sys
from typing import Optional

import config
from core.logger_config import get_logger

logger = get_logger(__name__)


def generate_image_flowweb(
    prompt: str,
    output_path: str,
    aspect_ratio: str = None,
    resolution: str = None,
    seed: int = None,
    project_title: str = None,
    reference_image_path=None,
    model: str = None,
    outputs: str = None,
) -> Optional[str]:
    """
    Generate a single image using Google Flow (flow.google.com) via browser
    automation.

    Args:
        prompt: Text description of the image to generate
        output_path: Full path where the image will be saved
        aspect_ratio: Optional aspect ratio override ("16:9", "4:3", "1:1",
            "3:4", "9:16" — the ratios Flow's settings popover offers)
        resolution: Not used for FlowWeb mode (kept for API consistency)
        seed: Not used for FlowWeb mode (kept for API consistency)
        project_title: Title used to reuse the project's Flow workspace
        reference_image_path: Optional path (or list of paths) uploaded as
            Flow ingredients before generating
        model: Optional Flow image model override; defaults to
            config.FLOW_IMAGE_MODEL ("Nano Banana 2.1")
        outputs: Optional outputs-per-prompt override; defaults to
            config.FLOW_IMAGE_OUTPUTS ("x1"). Agent mode is always left off.

    Returns:
        Path to the generated image file, or None if failed
    """
    logger.info(f"Generating image (FlowWeb): {output_path}")
    logger.debug(f"  Prompt: {prompt[:100]}...")
    logger.debug(f"  Aspect ratio: {aspect_ratio or config.IMAGE_ASPECT_RATIO}")

    timeout = getattr(config, 'FLOWWEB_TIMEOUT', 300)

    from core.geminiweb_pool import get_worker_id, release_worker_id

    worker_id = get_worker_id()
    try:
        # Determine master profile path dynamically (mirror geminiweb generator)
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

        logger.info(f"Checking out {profile_name} worker {worker_id} for Flow...")

        import shutil
        if not os.path.exists(worker_profile) and os.path.exists(master_profile):
            ignore_func = shutil.ignore_patterns(
                '*Cache*', '*cache*', 'Service Worker', 'Crashpad',
                '*OptGuideOnDeviceModel*', '*OptimizationGuide*')
            try:
                shutil.copytree(master_profile, worker_profile, ignore=ignore_func)
            except Exception as e:
                logger.warning(f"Profile copy warning for worker {worker_id}: {e}. "
                               "Close the main browser window for full profile replication.")
        elif not os.path.exists(worker_profile):
            os.makedirs(worker_profile, exist_ok=True)

        # Remove stale browser locks so Playwright can attach to the profile
        for lock_file in ['SingletonLock', 'SingletonCookie', 'SingletonSocket',
                          'parent.lock', '.parentlock', 'lock']:
            lock_path = os.path.join(worker_profile, lock_file)
            if os.path.exists(lock_path):
                try:
                    if os.path.islink(lock_path):
                        os.unlink(lock_path)
                    else:
                        os.remove(lock_path)
                except Exception as e:
                    logger.warning(f"Failed to remove stale lock {lock_file}: {e}")

        cmd = [
            sys.executable,
            "-m",
            "core.flowweb_image_subprocess",
            prompt,
            output_path,
        ]
        if aspect_ratio:
            cmd.extend(["--aspect-ratio", aspect_ratio])
        if project_title:
            cmd.extend(["--project-title", project_title])
        if reference_image_path:
            if isinstance(reference_image_path, (list, tuple)):
                for img in reference_image_path:
                    cmd.extend(["--reference-image", img])
            else:
                cmd.extend(["--reference-image", reference_image_path])
        if worker_profile:
            cmd.extend(["--profile-dir", worker_profile])
        if model:
            cmd.extend(["--model", model])
        if outputs:
            cmd.extend(["--outputs", outputs])

        logger.info(f"Launching FlowWeb subprocess (Worker {worker_id})")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 180,  # buffer for navigation + settings + download
            cwd=os.path.dirname(os.path.dirname(__file__)),
        )

        logger.debug(f"Subprocess stdout: {result.stdout[:500]}")
        if result.stderr:
            logger.debug(f"Subprocess stderr: {result.stderr[:500]}")

        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.startswith('SUCCESS:'):
                    generated_path = line[len('SUCCESS:'):].strip()
                    if os.path.exists(generated_path):
                        file_size = os.path.getsize(generated_path)
                        logger.info(f"Generated (FlowWeb): {generated_path} ({file_size:,} bytes)")
                        print(f"[PASS] Generated (FlowWeb): {generated_path}")
                        return generated_path

            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logger.info(f"Generated (FlowWeb): {output_path} ({file_size:,} bytes)")
                print(f"[PASS] Generated (FlowWeb): {output_path}")
                return output_path

            logger.error("FlowWeb subprocess exited 0 but no image file found")
            return None
        else:
            logger.error(f"FlowWeb subprocess failed (exit code {result.returncode})")
            logger.error(f"stdout: {result.stdout}")
            logger.error(f"stderr: {result.stderr}")
            print(f"[FAIL] FlowWeb subprocess failed")
            return None

    except subprocess.TimeoutExpired:
        logger.error(f"FlowWeb subprocess timed out after {timeout + 180}s")
        print("[FAIL] FlowWeb: Subprocess timed out")
        return None
    except Exception as e:
        import traceback
        logger.error(f"Failed to generate image (FlowWeb): {e}\n{traceback.format_exc()}")
        print(f"[FAIL] Failed to generate image (FlowWeb): {e}")
        return None
    finally:
        release_worker_id(worker_id)
