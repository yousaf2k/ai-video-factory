import requests
import uuid
import time
import config
import os
from core.logger_config import get_logger


# Get logger for ComfyUI API operations
logger = get_logger(__name__)

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

    # ComfyUI default output directory
    if subfolder:
        output_path = os.path.join("ComfyUI", "output", subfolder, filename)
    else:
        output_path = os.path.join("ComfyUI", "output", filename)

    abs_path = os.path.abspath(output_path)

    # Log if file doesn't exist
    if not os.path.exists(abs_path):
        logger.warning(f"Output file not found: {abs_path}")
        # Try alternative paths for videos
        if file_type == 'video':
            # ComfyUI saves videos in a 'video' subfolder
            alt_path = os.path.join("ComfyUI", "output", "video", filename)
            if os.path.exists(alt_path):
                logger.info(f"Found video at alternative path: {alt_path}")
                return os.path.abspath(alt_path)
    else:
        logger.debug(f"Output file found: {abs_path}")

    return abs_path