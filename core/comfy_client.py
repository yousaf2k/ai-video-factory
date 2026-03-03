import requests
import uuid
import time
import config
import os
from core.logger_config import get_logger

# Use a session to pool TCP connections and prevent socket exhaustion (WinError 10055)
http_session = requests.Session()

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
        _comfy_output_dir = os.path.normpath(config.COMFY_OUTPUT_DIR)
        logger.info(f"ComfyUI output directory from config: {_comfy_output_dir}")
        return _comfy_output_dir

    logger.info("Attempting to detect ComfyUI output directory from API...")

    try:
        # Try to get ComfyUI settings - this includes path information
        r = http_session.get(f"{config.COMFY_URL}/settings", timeout=5)

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
        r = http_session.get(f"{config.COMFY_URL}/system_stats", timeout=5)

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
        r = http_session.get(f"{config.COMFY_URL}/extension_manager", timeout=5)

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

    r = http_session.post(
        f"{config.COMFY_URL}/prompt",
        json=payload,
        timeout=10
    )

    if r.status_code != 200:
        logger.error(f"ComfyUI returned status {r.status_code}: {r.text}")
        raise Exception(f"ComfyUI returned status {r.status_code}: {r.text}")

    result = r.json()
    prompt_id = result.get('prompt_id')
    logger.info(f"Workflow submitted: prompt_id={prompt_id}")
    return result


def interrupt_generation():
    """Interrupt the currently running generation in ComfyUI."""
    try:
        r = http_session.post(f"{config.COMFY_URL}/interrupt", timeout=5)
        logger.info(f"ComfyUI interrupt sent, status: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        logger.error(f"Failed to interrupt ComfyUI: {e}")
        return False


def clear_queue():
    """Clear all pending items from the ComfyUI queue."""
    try:
        r = http_session.post(
            f"{config.COMFY_URL}/queue",
            json={"clear": True},
            timeout=5
        )
        logger.info(f"ComfyUI queue clear sent, status: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        logger.error(f"Failed to clear ComfyUI queue: {e}")
        return False


def cancel_all():
    """Interrupt current generation and clear the queue."""
    interrupted = interrupt_generation()
    cleared = clear_queue()
    return interrupted or cleared


def wait_for_prompt_completion_with_progress(prompt_id, progress_callback=None, timeout=1800):
    """
    Wait for a specific prompt to complete using WebSockets to get real-time progress.
    
    Args:
        prompt_id: The prompt ID to wait for
        progress_callback: Function called with (current_step, total_steps)
        timeout: Maximum time to wait in seconds
    """
    import asyncio
    import json
    import websockets
    from urllib.parse import urlparse

    # Convert http://... to ws://...
    parsed_url = urlparse(config.COMFY_URL)
    ws_url = f"ws://{parsed_url.netloc}/ws?clientId={str(uuid.uuid4())}"

    # First, check if it's already in history (fast execution)
    from core.comfy_client import wait_for_prompt_completion
    try:
        check_response = http_session.get(f"{config.COMFY_URL}/history/{prompt_id}", timeout=2)
        if check_response.status_code == 200:
            history = check_response.json()
            if prompt_id in history:
                logger.debug(f"Prompt {prompt_id} already in history, skipping WS progress.")
                if progress_callback:
                    progress_callback(100, 100)
                return wait_for_prompt_completion(prompt_id, timeout=10)
    except Exception as e:
        logger.debug(f"Initial history check failed: {e}")

    async def _listen():
        logger.info(f"Connecting to ComfyUI WebSocket: {ws_url}")
        try:
            async with websockets.connect(ws_url) as websocket:
                start_time = time.time()
                last_history_check = time.time()
                our_prompt_is_executing = False  # Only true when OUR prompt is actively running
                another_prompt_is_executing = False  # True when we've confirmed another prompt is running
                execution_start_time = None  # Track when our prompt actually starts
                currently_executing_prompt_id = None  # Track what prompt is executing right now
                
                while True:
                    current_time = time.time()
                    
                    # Use execution_start_time for timeout if our prompt has started,
                    # otherwise use a generous queue timeout
                    if our_prompt_is_executing and execution_start_time:
                        if current_time - execution_start_time > timeout:
                            return {'success': False, 'error': f'Timeout after {timeout}s of execution', 'outputs': []}
                    else:
                        # While queued, use a very generous timeout (e.g., 1 hour)
                        queue_timeout = max(timeout, 3600)
                        if current_time - start_time > queue_timeout:
                            return {'success': False, 'error': f'Queue timeout after {int(current_time - start_time)}s', 'outputs': []}

                    # Occasionally check history manually as fallback
                    if current_time - last_history_check > 5.0:
                        last_history_check = current_time
                        try:
                            hist_result = await asyncio.to_thread(http_session.get, f"{config.COMFY_URL}/history/{prompt_id}", timeout=2)
                            if hist_result.status_code == 200:
                                history = hist_result.json()
                                if prompt_id in history:
                                    logger.info(f"Prompt {prompt_id} completed (found via history poll)")
                                    if progress_callback:
                                        progress_callback(100, 100)
                                    return wait_for_prompt_completion(prompt_id, timeout=5)
                        except:
                            pass

                    try:
                        message_raw = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        message = json.loads(message_raw)
                        
                        msg_type = message.get("type")
                        data = message.get("data", {})
                        


                        if msg_type == "executing":
                            msg_prompt_id = data.get("prompt_id")
                            node = data.get("node")
                            
                            # Update global tracker for what's currently running
                            if msg_prompt_id:
                                currently_executing_prompt_id = msg_prompt_id
                                
                            if msg_prompt_id == prompt_id:
                                if node is None:
                                    # Our prompt finished execution
                                    logger.info(f"Prompt {prompt_id} execution finished (via WS)")
                                    if progress_callback:
                                        progress_callback(100, 100)
                                    return wait_for_prompt_completion(prompt_id, timeout=10)
                                else:
                                    # Our prompt started or is executing a node
                                    if not our_prompt_is_executing:
                                        logger.info(f"Prompt {prompt_id} started executing")
                                        our_prompt_is_executing = True
                                        execution_start_time = time.time()
                            else:
                                our_prompt_is_executing = False

                        elif msg_type == "progress":
                            # Progress messages in newer ComfyUI versions include prompt_id
                            prog_prompt_id = data.get("prompt_id")
                            
                            is_our_progress = False
                            # 1. Direct match (best)
                            if prog_prompt_id == prompt_id:
                                is_our_progress = True
                            # 2. Fallback to global execution state tracker
                            elif prog_prompt_id is None:
                                if currently_executing_prompt_id == prompt_id:
                                    is_our_progress = True

                            if is_our_progress and progress_callback:
                                value = data.get("value", 0)
                                max_val = data.get("max", 0)
                                progress_callback(value, max_val)


                    except asyncio.TimeoutError:
                        continue
        except Exception as e:
            logger.error(f"WebSocket error in comfy_client: {e}")
            # Fallback to polling if WebSocket fails
            return wait_for_prompt_completion(prompt_id, timeout=timeout)

    # Run the async listener
    try:
        return asyncio.run(_listen())
    except Exception as e:
        logger.error(f"Error running asyncio loop in comfy_client: {e}")
        # Always fallback to standard polling
        return wait_for_prompt_completion(prompt_id, timeout=timeout)


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
                queue_response = http_session.get(f"{config.COMFY_URL}/queue", timeout=5)
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
            response = http_session.get(f"{config.COMFY_URL}/history/{prompt_id}", timeout=10)

            if response.status_code != 200:
                time.sleep(2)
                continue

            history = response.json()

            if prompt_id not in history:
                # If it's not in history, check if it's still in the queue.
                # If it's in neither, it was likely canceled/interrupted.
                try:
                    queue_resp = http_session.get(f"{config.COMFY_URL}/queue", timeout=5)
                    if queue_resp.status_code == 200:
                        queue_data = queue_resp.json()
                        queue_running = queue_data.get("queue_running", [])
                        queue_pending = queue_data.get("queue_pending", [])
                        
                        is_in_queue = False
                        for item in queue_running + queue_pending:
                            if len(item) > 1 and item[1] == prompt_id:
                                is_in_queue = True
                                break
                                
                        if not is_in_queue:
                            logger.info(f"Prompt {prompt_id} not found in history or queue. Assuming canceled.")
                            return {
                                'success': False,
                                'error': f'Prompt {prompt_id} was canceled or removed from queue.',
                                'outputs': []
                            }
                except Exception as e:
                    logger.debug(f"Failed to check queue status: {e}")

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