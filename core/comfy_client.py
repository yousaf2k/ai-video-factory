import requests
import uuid
import time
import config
import os
from core.logger_config import get_logger


# Get logger for ComfyUI API operations
logger = get_logger(__name__)

# Cache for ComfyUI output directory
_comfy_output_dir = None


def get_comfyui_output_directory():
    """
    Get ComfyUI's actual output directory from the API.

    Returns:
        str: Path to ComfyUI's output directory
    """
    global _comfy_output_dir

    if _comfy_output_dir:
        return _comfy_output_dir

    # First, check if it's manually set in config
    if config.COMFY_OUTPUT_DIR:
        _comfy_output_dir = config.COMFY_OUTPUT_DIR
        logger.info(f"ComfyUI output directory from config: {_comfy_output_dir}")
        return _comfy_output_dir

    logger.info("Attempting to detect ComfyUI output directory from API...")

    try:
        # Try to get ComfyUI settings - this includes path information
        r = requests.get(f"{config.COMFY_URL}/settings", timeout=5)

        if r.status_code == 200:
            settings = r.json()
            logger.debug(f"ComfyUI settings response keys: {list(settings.keys())}")

            # Log the entire settings for debugging (be careful not to log sensitive data)
            logger.debug(f"ComfyUI settings: {settings}")

            # Check for ComfyUI's paths in settings
            # The key might vary depending on ComfyUI version
            possible_keys = ['output_directory', 'outputDir', 'output_dir', 'path_output']

            for key in possible_keys:
                if key in settings:
                    _comfy_output_dir = settings[key]
                    logger.info(f"ComfyUI output directory from API ({key}): {_comfy_output_dir}")
                    return _comfy_output_dir

    except Exception as e:
        logger.warning(f"Could not get ComfyUI settings from API: {e}")

    try:
        # Alternative: Try the system_stats endpoint
        r = requests.get(f"{config.COMFY_URL}/system_stats", timeout=5)

        if r.status_code == 200:
            stats = r.json()
            logger.debug(f"ComfyUI system_stats response: {stats}")

            # Look for path information in various possible fields
            if 'paths' in stats:
                paths = stats['paths']
                logger.debug(f"ComfyUI paths: {paths}")
                if 'output' in paths:
                    _comfy_output_dir = paths['output']
                    logger.info(f"ComfyUI output directory from system_stats: {_comfy_output_dir}")
                    return _comfy_output_dir

    except Exception as e:
        logger.warning(f"Could not get ComfyUI system_stats from API: {e}")

    try:
        # Another approach: Check the extension settings
        r = requests.get(f"{config.COMFY_URL}/extension_manager", timeout=5)

        if r.status_code == 200:
            ext_data = r.json()
            logger.debug(f"ComfyUI extension_manager response: {ext_data}")
            # Some ComfyUI versions include paths in extension manager data
            if 'ComfyUI' in ext_data and 'path' in ext_data['ComfyUI']:
                comfy_path = ext_data['ComfyUI']['path']
                _comfy_output_dir = os.path.join(comfy_path, "output")
                logger.info(f"ComfyUI output directory from extension manager: {_comfy_output_dir}")
                return _comfy_output_dir

    except Exception as e:
        logger.warning(f"Could not get ComfyUI extension manager info: {e}")

    # Fallback: try to detect from COMFY_URL and known locations
    # If ComfyUI is at http://127.0.0.1:8188, it might be installed in various locations
    possible_paths = [
        "C:/ComfyUI/output",  # Common Windows install
        "D:/ComfyUI/output",  # Alternative Windows drive
        os.path.expanduser("~/ComfyUI/output"),  # User home
        "/ComfyUI/output",  # Linux/Mac common location
        "ComfyUI/output",  # Relative path (ComfyUI in project folder)
    ]

    for path in possible_paths:
        if os.path.exists(path):
            _comfy_output_dir = path
            logger.info(f"ComfyUI output directory detected by file existence: {_comfy_output_dir}")
            return _comfy_output_dir

    # Last resort: use the default relative path but warn about it
    _comfy_output_dir = "ComfyUI/output"
    logger.error(f"Could not detect ComfyUI output directory from API or file system!")
    logger.error(f"   Using default relative path: {_comfy_output_dir}")
    logger.error(f"   If ComfyUI is installed elsewhere, set COMFY_OUTPUT_DIR in config.py")
    return _comfy_output_dir

def submit(workflow):
    """
    Submit a workflow to ComfyUI and return the response.

    Returns:
        dict with 'prompt_id' and 'number' of the prompt in queue
    """
    payload = {
        "prompt": workflow,
        "client_id": str(uuid.uuid4())
    }

    r = requests.post(
        f"{config.COMFY_URL}/prompt",
        json=payload
    )

    if r.status_code != 200:
        logger.error(f"ComfyUI returned status {r.status_code}: {r.text}")
        raise Exception(f"ComfyUI returned status {r.status_code}: {r.text}")

    result = r.json()
    prompt_id = result.get('prompt_id')
    logger.info(f"Workflow submitted: prompt_id={prompt_id}")
    return result


def wait_for_prompt_completion(prompt_id, timeout=1800):
    """
    Wait for a specific prompt to complete and check for errors.

    Args:
        prompt_id: The prompt ID to wait for
        timeout: Maximum time to wait in seconds (default: 30 minutes)

    Returns:
        dict with 'success' (bool), 'outputs' (list of output files), 'error' (str if failed)
    """
    logger.info(f"Waiting for prompt {prompt_id} completion (timeout: {timeout}s)")
    start_time = time.time()
    last_status_check = 0

    while True:
        elapsed = time.time() - start_time

        if elapsed > timeout:
            # Check queue status before giving up
            try:
                queue_response = requests.get(f"{config.COMFY_URL}/queue")
                if queue_response.status_code == 200:
                    queue_data = queue_response.json()
                    queue_running = queue_data.get("queue_running", [])
                    queue_pending = queue_data.get("queue_pending", [])
                    return {
                        'success': False,
                        'error': f'Timeout after {int(elapsed)}s. Queue running: {len(queue_running)}, pending: {len(queue_pending)}',
                        'outputs': []
                    }
            except:
                pass

            return {
                'success': False,
                'error': f'Timeout waiting for prompt {prompt_id} after {int(elapsed)}s',
                'outputs': []
            }

        try:
            # Check prompt status
            response = requests.get(f"{config.COMFY_URL}/history/{prompt_id}")

            if response.status_code != 200:
                time.sleep(2)
                continue

            history = response.json()

            if prompt_id not in history:
                time.sleep(2)
                continue

            prompt_data = history[prompt_id]
            status = prompt_data.get("status", {})

            # Print status every 30 seconds
            if elapsed - last_status_check > 30:
                last_status_check = elapsed
                status_str = status.get("status", "unknown")
                logger.debug(f"Prompt {prompt_id[:8]}... status: {status_str} ({int(elapsed)}s elapsed)")
                print(f"       [STATUS] {status_str} ({int(elapsed)}s elapsed)")

            # Check if completed
            if status.get("completed", False):
                # Get outputs
                outputs = prompt_data.get("outputs", {})
                output_files = []

                # Extract output files from all nodes
                for node_id, node_output in outputs.items():
                    # Check for video outputs
                    if "video" in node_output and len(node_output["video"]) > 0:
                        for video_info in node_output["video"]:
                            filename = video_info.get("filename", "")
                            subfolder = video_info.get("subfolder", "")
                            output_files.append({
                                'type': 'video',
                                'filename': filename,
                                'subfolder': subfolder
                            })

                    # Check for images - but filter for video files (.mp4, .webm, etc.)
                    # ComfyUI's SaveVideo node sometimes outputs to the "images" field
                    if "images" in node_output and len(node_output["images"]) > 0:
                        for img_info in node_output["images"]:
                            filename = img_info.get("filename", "")
                            subfolder = img_info.get("subfolder", "")

                            # Check if it's actually a video file
                            if any(filename.lower().endswith(ext) for ext in ['.mp4', '.webm', '.avi', '.mov', '.mkv']):
                                output_files.append({
                                    'type': 'video',
                                    'filename': filename,
                                    'subfolder': subfolder
                                })
                            else:
                                # Regular image
                                output_files.append({
                                    'type': 'image',
                                    'filename': filename,
                                    'subfolder': subfolder
                                })

                logger.info(f"Prompt {prompt_id[:8]}... completed successfully with {len(output_files)} output(s)")

                # Log details of each output file for debugging
                for i, output in enumerate(output_files):
                    logger.debug(f"  Output {i+1}: type={output['type']}, filename={output['filename']}, subfolder='{output.get('subfolder', '')}'")
                    if output['type'] == 'video':
                        print(f"  [VIDEO] Found: {output['filename']} (subfolder: '{output.get('subfolder', '')}')")

                return {
                    'success': True,
                    'outputs': output_files,
                    'error': None
                }

            # Check for errors
            if status.get("status", "") == "error":
                error_details = status.get("message", "Unknown error")
                logger.error(f"Prompt {prompt_id[:8]}... failed: {error_details}")
                # Try to get more error details
                if "node_errors" in prompt_data:
                    node_errors = prompt_data["node_errors"]
                    error_details += f" | Nodes with errors: {list(node_errors.keys())}"
                return {
                    'success': False,
                    'error': f'ComfyUI error: {error_details}',
                    'outputs': []
                }

            # Still processing
            if status.get("status", "") in ["queued", "processing"]:
                time.sleep(2)
                continue

        except Exception as e:
            time.sleep(2)
            continue


def get_output_file_path(output_info):
    """
    Get the full local path for a ComfyUI output file.

    Args:
        output_info: dict with 'filename', 'subfolder', 'type'

    Returns:
        Full path to the output file
    """
    filename = output_info['filename']
    subfolder = output_info.get('subfolder', '')
    file_type = output_info.get('type', 'unknown')

    logger.debug(f"Getting output file path: {filename} (subfolder: '{subfolder}', type: {file_type})")

    # Get ComfyUI's actual output directory
    comfy_output_dir = get_comfyui_output_directory()

    # List of paths to try, in order
    candidate_paths = []

    # ComfyUI default output directory
    if subfolder:
        candidate_paths.append(os.path.join(comfy_output_dir, subfolder, filename))
    else:
        candidate_paths.append(os.path.join(comfy_output_dir, filename))

    # For videos, try alternative paths
    if file_type == 'video':
        # ComfyUI saves videos in a 'video' subfolder
        candidate_paths.append(os.path.join(comfy_output_dir, "video", filename))

        # Try without the trailing underscore if filename ends with one
        if filename.endswith('_'):
            filename_without_underscore = filename[:-1]
            candidate_paths.append(os.path.join(comfy_output_dir, filename_without_underscore))
            candidate_paths.append(os.path.join(comfy_output_dir, "video", filename_without_underscore))

    # Try each candidate path
    for path in candidate_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            logger.debug(f"Output file found: {abs_path}")
            return abs_path

    # If none of the exact paths work, try searching for files with similar names
    if file_type == 'video':
        logger.warning(f"Video not found at expected paths, searching for similar files...")
        # Extract the base part of the filename (before the frame count)
        # Example: 1771452785243_86b45e92_shot_003_00001_.mp4 -> 1771452785243_86b45e92_shot_003
        import re
        base_match = re.match(r'^(.*_shot_\d+)_\d+_(\.)?mp4$', filename)
        if base_match:
            base_name = base_match.group(1)
            # Search for any files starting with this base name
            if os.path.exists(comfy_output_dir):
                for file in os.listdir(comfy_output_dir):
                    if file.startswith(base_name) and file.endswith('.mp4'):
                        found_path = os.path.join(comfy_output_dir, file)
                        logger.info(f"Found video with similar name: {found_path}")
                        return os.path.abspath(found_path)

    # Log the expected path even if not found
    logger.warning(f"Output file not found at any expected path")
    logger.warning(f"  ComfyUI output dir: {comfy_output_dir}")
    logger.warning(f"  Tried paths: {candidate_paths}")

    # Return the primary expected path (even though it doesn't exist)
    return os.path.abspath(candidate_paths[0])