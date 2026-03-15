"""
ComfyUI Image Generation Module
Generates images using ComfyUI workflows (SDXL, Flux, etc.)
"""
import requests
import json
import copy
import config
import os
import time
import uuid
from core.logger_config import get_logger
from core.comfy_client import http_session

# Get logger for ComfyUI image generation
logger = get_logger(__name__)


def generate_image_comfyui(prompt: str, output_path: str, negative_prompt: str = "", seed: int = None, workflow_name: str = None, aspect_ratio: str = None, progress_callback=None, reference_image_path: str = None):
    """
    Generate a single image using ComfyUI workflow.

    Args:
        prompt: Text description of the image to generate
        output_path: Full path where the image will be saved
        negative_prompt: Optional negative prompt for better quality
        seed: Optional random seed for reproducibility
        workflow_name: Optional workflow name from IMAGE_WORKFLOWS (uses config.IMAGE_WORKFLOW if not specified)
        aspect_ratio: Optional aspect ratio override (uses config.IMAGE_ASPECT_RATIO if not specified)
        progress_callback: Optional callback for progress updates (current, total)
        reference_image_path: Optional path to reference image for IP-Adapter

    Returns:
        Path to the generated image file, or None if failed
    """
    try:
        # Get workflow configuration
        if workflow_name is None:
            workflow_name = config.IMAGE_WORKFLOW

        # Get workflow config from IMAGE_WORKFLOWS
        workflows = getattr(config, 'IMAGE_WORKFLOWS', {})

        if workflow_name not in workflows:
            logger.warning(f"Workflow '{workflow_name}' not found in IMAGE_WORKFLOWS, using 'default'")
            workflow_name = 'default'

        if workflow_name not in workflows:
            logger.warning(f"Default workflow not found, falling back to legacy config")
            workflow_config = {
                'workflow_path': config.IMAGE_WORKFLOW_PATH,
                'text_node_id': config.IMAGE_TEXT_NODE_ID,
                'neg_text_node_id': config.IMAGE_NEG_TEXT_NODE_ID,
                'ksampler_node_id': config.IMAGE_KSAMPLER_NODE_ID,
                'vae_node_id': config.IMAGE_VAE_NODE_ID,
                'save_node_id': config.IMAGE_SAVE_NODE_ID
            }
        else:
            workflow_config = workflows[workflow_name]

        workflow_path = workflow_config['workflow_path']
        text_node_id = workflow_config.get('text_node_id')
        neg_text_node_id = workflow_config.get('neg_text_node_id')
        ksampler_node_id = workflow_config.get('ksampler_node_id')
        vae_node_id = workflow_config.get('vae_node_id')
        save_node_id = workflow_config.get('save_node_id')
        load_reference_node_id = workflow_config.get('load_reference_node_id')

        logger.info(f"Using workflow: {workflow_name} ({workflow_config.get('description', 'No description')})")
        logger.debug(f"Workflow file: {workflow_path}")

        # Log IP-Adapter usage if reference image provided
        if reference_image_path:
            if load_reference_node_id:
                logger.info(f"Using IP-Adapter with reference image: {reference_image_path}")
            else:
                logger.warning(f"Reference image provided but workflow '{workflow_name}' doesn't have load_reference_node_id configured")

        # Load the image generation workflow
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)

        # Get dimensions from config
        if aspect_ratio is None:
            aspect_ratio = config.IMAGE_ASPECT_RATIO
        width, height = config.calculate_image_dimensions(aspect_ratio=aspect_ratio)

        # Inject prompts into the workflow
        # The workflow structure needs to be converted to API format
        api_format = _convert_workflow_to_api_format(workflow, width=width, height=height)

        # If it was already in API format, we still need to inject dimensions into specific nodes
        if "nodes" not in workflow:
            # Detect Flux v1 workflows and clamp width to 1440
            node_classes = {nd.get("class_type", "") for nd in api_format.values()}
            is_flux_v1 = ("ModelSamplingFlux" in node_classes or "EmptySD3LatentImage" in node_classes) \
                         and "EmptyFlux2LatentImage" not in node_classes \
                         and "Flux2Scheduler" not in node_classes
            if is_flux_v1 and width > 1440:
                logger.info(f"Flux v1 detected: clamping width from {width} to 1440")
                height = int(height * (1440 / width))
                width = 1440

            for node_id, node_data in api_format.items():
                class_type = node_data.get("class_type", "")
                if class_type == "EmptySD3LatentImage":
                    node_data["inputs"]["width"] = width
                    node_data["inputs"]["height"] = height
                elif class_type == "ModelSamplingFlux":
                    node_data["inputs"]["width"] = width
                    node_data["inputs"]["height"] = height
                elif class_type == "EmptyFlux2LatentImage":
                    node_data["inputs"]["width"] = width
                    node_data["inputs"]["height"] = height
                elif class_type == "Flux2Scheduler":
                    node_data["inputs"]["width"] = width
                    node_data["inputs"]["height"] = height

        # Set the text prompts using workflow-specific node IDs
        if text_node_id and text_node_id in api_format:
            api_format[text_node_id]["inputs"]["text"] = prompt

        if neg_text_node_id and neg_text_node_id in api_format and negative_prompt:
            api_format[neg_text_node_id]["inputs"]["text"] = negative_prompt

        # Inject reference image for IP-Adapter if provided
        if reference_image_path and load_reference_node_id and load_reference_node_id in api_format:
            # Convert to absolute path and normalize
            ref_path = config.resolve_path(reference_image_path).replace('\\', '/')
            api_format[load_reference_node_id]["inputs"]["image"] = ref_path
            logger.debug(f"Injected reference image into node {load_reference_node_id}: {ref_path}")

        # Set random seed if provided
        if seed is not None:
            # Find KSampler or RandomNoise node to set seed
            for node_id, node_data in api_format.items():
                class_type = node_data.get("class_type", "")
                if class_type in ["KSampler", "KSamplerAdvanced"]:
                    if "seed" in node_data.get("inputs", {}):
                        api_format[node_id]["inputs"]["seed"] = seed
                elif class_type == "RandomNoise":
                    if "noise_seed" in node_data.get("inputs", {}):
                        api_format[node_id]["inputs"]["noise_seed"] = seed

        # Set output filename for SaveImage node using workflow-specific node ID
        actual_prefix = ""
        if save_node_id and save_node_id in api_format:
            # Extract just the filename from the full path
            filename = os.path.basename(output_path)
            base_name = os.path.splitext(filename)[0]

            # Add unique prefix to prevent ComfyUI filename collisions
            # ComfyUI may append _001, _002 etc. if files with same name exist
            unique_id = f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
            actual_prefix = f"{unique_id}_{base_name}"
            api_format[save_node_id]["inputs"]["filename_prefix"] = actual_prefix

        # Submit to ComfyUI
        payload = {
            "prompt": api_format
        }

        response = http_session.post(
            f"{config.COMFY_URL}/prompt",
            json=payload
        )

        if response.status_code != 200:
            logger.error(f"ComfyUI returned status {response.status_code}: {response.text}")
            return None

        result = response.json()
        prompt_id = result.get("prompt_id")

        if not prompt_id:
            logger.error("No prompt_id in response")
            return None

        # Wait for completion and get the result
        return _wait_for_image(prompt_id, output_path, progress_callback=progress_callback)

    except Exception as e:
        logger.error(f"ComfyUI image generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def _convert_workflow_to_api_format(workflow, width=None, height=None):
    """
    Convert ComfyUI workflow from UI format to API format.

    Args:
        workflow: ComfyUI workflow in UI format
        width: Optional width override (uses config if not specified)
        height: Optional height override (uses config if not specified)
    """
    if width is None or height is None:
        width, height = config.calculate_image_dimensions()

    if "nodes" in workflow:
        # Build a link lookup table: link_id -> [source_node_id, source_slot]
        link_lookup = {}
        if "links" in workflow:
            for link in workflow["links"]:
                # Link format: [link_id, source_node_id, source_slot, target_node_id, target_slot, type]
                if len(link) >= 3:
                    link_lookup[str(link[0])] = [str(link[1]), link[2]]

        api_format = {}
        for node in workflow["nodes"]:
            # Skip disabled nodes (mode 2) and muted nodes (mode 4)
            if node.get("mode", 0) in [2, 4]:
                continue

            node_id = str(node["id"])
            node_data = {
                "class_type": node.get("type", ""),
                "inputs": {}
            }

            # Track which input indices have been used from widgets_values
            used_widget_indices = set()

            # Add inputs from the node's input connections
            if "inputs" in node:
                for input_def in node["inputs"]:
                    input_name = input_def["name"]
                    if "link" in input_def and input_def["link"] is not None:
                        # Convert link ID to [source_node_id, source_slot]
                        link_id = str(input_def["link"])
                        if link_id in link_lookup:
                            node_data["inputs"][input_name] = link_lookup[link_id]
                        else:
                            # Fallback if link not found
                            node_data["inputs"][input_name] = [str(input_def["link"])]
                    elif "widget" in input_def:
                        # This input has a widget value - will be processed below
                        pass

            # Handle widgets_values based on node type
            if "widgets_values" in node:
                widgets = node["widgets_values"]
                node_type = node.get("type", "")

                # Special handling for known node types
                if node_type == "CLIPTextEncode":
                    if len(widgets) >= 1:
                        node_data["inputs"]["text"] = widgets[0]
                elif node_type == "SaveImage":
                    if len(widgets) >= 1:
                        node_data["inputs"]["filename_prefix"] = widgets[0]
                elif node_type == "KSampler":
                    if len(widgets) >= 1:
                        node_data["inputs"]["seed"] = widgets[0]
                elif node_type == "KSamplerSelect":
                    if len(widgets) >= 1:
                        node_data["inputs"]["sampler_name"] = widgets[0]
                elif node_type == "BasicScheduler":
                    if len(widgets) >= 3:
                        node_data["inputs"]["scheduler"] = widgets[0]
                        node_data["inputs"]["steps"] = widgets[1]
                        node_data["inputs"]["denoise"] = widgets[2]
                elif node_type == "RandomNoise":
                    if len(widgets) >= 1:
                        node_data["inputs"]["noise_seed"] = widgets[0]
                elif node_type == "EmptySD3LatentImage":
                    if len(widgets) >= 3:
                        # Use config dimensions instead of hardcoded values
                        node_data["inputs"]["width"] = width
                        node_data["inputs"]["height"] = height
                        node_data["inputs"]["batch_size"] = widgets[2]
                elif node_type == "ModelSamplingFlux":
                    if len(widgets) >= 4:
                        node_data["inputs"]["base_shift"] = widgets[0]
                        node_data["inputs"]["max_shift"] = widgets[1]
                        # Use config dimensions instead of hardcoded values
                        node_data["inputs"]["width"] = width
                        node_data["inputs"]["height"] = height
                elif node_type == "FluxGuidance":
                    if len(widgets) >= 1:
                        node_data["inputs"]["guidance"] = widgets[0]
                elif node_type == "VAELoader":
                    if len(widgets) >= 1:
                        node_data["inputs"]["vae_name"] = widgets[0]
                elif node_type == "UNETLoader":
                    if len(widgets) >= 1:
                        node_data["inputs"]["unet_name"] = widgets[0]
                    if len(widgets) >= 2:
                        node_data["inputs"]["weight_dtype"] = widgets[1]
                elif node_type == "DualCLIPLoader":
                    if len(widgets) >= 3:
                        node_data["inputs"]["clip_name1"] = widgets[0]
                        node_data["inputs"]["clip_name2"] = widgets[1]
                        node_data["inputs"]["type"] = widgets[2]
                    if len(widgets) >= 4:
                        node_data["inputs"]["device"] = widgets[3]
                elif node_type == "UnetLoaderGGUF":
                    if len(widgets) >= 1:
                        node_data["inputs"]["unet_name"] = widgets[0]
                elif node_type == "DualCLIPLoaderGGUF":
                    if len(widgets) >= 3:
                        node_data["inputs"]["clip_name1"] = widgets[0]
                        node_data["inputs"]["clip_name2"] = widgets[1]
                        node_data["inputs"]["type"] = widgets[2]

            api_format[node_id] = node_data

        return api_format
    else:
        return workflow


def _wait_for_image(prompt_id, output_path, timeout=300, progress_callback=None):
    """Wait for ComfyUI to finish generating the image"""
    import shutil
    from core.comfy_client import get_output_file_path, get_comfyui_output_directory, wait_for_prompt_completion_with_progress

    if progress_callback:
        wait_result = wait_for_prompt_completion_with_progress(prompt_id, progress_callback=progress_callback, timeout=timeout)
    else:
        from core.comfy_client import wait_for_prompt_completion
        wait_result = wait_for_prompt_completion(prompt_id, timeout=timeout)

    if not wait_result or not wait_result.get('success'):
        logger.error(f"ComfyUI prompt failed or timed out: {wait_result}")
        return None

    logger.debug(f"Prompt {prompt_id} wait success, extracting results...")

    # Get the history to extract outputs
    try:
        response = http_session.get(f"{config.COMFY_URL}/history/{prompt_id}", timeout=10)
        if response.status_code != 200:
            logger.error(f"Failed to get history for prompt {prompt_id}")
            return None
        
        history = response.json()
        if prompt_id not in history:
            logger.error(f"Prompt {prompt_id} not found in history")
            return None

        prompt_data = history[prompt_id]
        outputs = prompt_data.get("outputs", {})
        image_info = None

        # Look for image outputs across all nodes
        for node_id, node_output in outputs.items():
            if "images" in node_output and len(node_output["images"]) > 0:
                image_info = node_output["images"][0]
                image_info['node_id'] = node_id
                break

        if not image_info:
            logger.error(f"No image outputs found for prompt {prompt_id}. History: {prompt_data.get('outputs')}")
            return None

        image_filename = image_info.get("filename", "")
        subfolder = image_info.get("subfolder", "")
        
        logger.info(f"Image generation complete: {image_filename}. Retrieving file...")

        # STEP 1: Try to get the file via local filesystem if possible (faster/more reliable)
        try:
            comfy_output_dir = get_comfyui_output_directory()
            if comfy_output_dir:
                if subfolder:
                    local_source = os.path.join(comfy_output_dir, subfolder, image_filename)
                else:
                    local_source = os.path.join(comfy_output_dir, image_filename)
                
                if os.path.exists(local_source):
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    shutil.copy2(local_source, output_path)
                    logger.info(f"Retrieved image from local filesystem: {output_path}")
                    return output_path
        except Exception as e:
            logger.debug(f"Failed to retrieve image via local filesystem: {e}")

        # STEP 2: Fallback to /view API if local retrieval failed
        try:
            if subfolder:
                url = f"{config.COMFY_URL}/view?filename={image_filename}&subfolder={subfolder}&type=output"
            else:
                url = f"{config.COMFY_URL}/view?filename={image_filename}&type=output"

            img_response = http_session.get(url, timeout=30)
            if img_response.status_code == 200:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(img_response.content)
                logger.info(f"Retrieved image from API: {output_path}")
                return output_path
        except Exception as e:
            logger.error(f"Error during API image download: {e}")

    except Exception as e:
        logger.error(f"Error retrieving image: {e}")

    return None


def generate_images_for_shots_comfyui(shots: list, output_dir: str, negative_prompt: str = ""):
    """
    Generate images for all shots using ComfyUI.

    Args:
        shots: List of shot dictionaries, each containing 'image_prompt'
        output_dir: Directory to save generated images
        negative_prompt: Optional negative prompt

    Returns:
        Updated list of shots with 'image_path' field added
    """
    logger.info(f"Generating {len(shots)} images using ComfyUI...")

    # Get and display dimensions
    width, height = config.calculate_image_dimensions()
    logger.info(f"Image dimensions: {width}x{height} ({config.IMAGE_ASPECT_RATIO} aspect ratio)")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    for idx, shot in enumerate(shots, start=1):
        # Generate filename
        filename = f"shot_{idx:03d}.png"
        output_path = os.path.join(output_dir, filename)

        # Generate image
        image_prompt = shot.get('image_prompt', '')
        if not image_prompt:
            logger.warning(f"Shot {idx}: No image_prompt, skipping")
            shot['image_path'] = None
            continue

        logger.info(f"[{idx}/{len(shots)}] Generating image for prompt: {image_prompt[:60]}...")
        
        # 1st time generation for a shot uses seed 1
        image_path = generate_image_comfyui(image_prompt, output_path, negative_prompt, seed=1)

        # Add image_path to shot dictionary
        shot['image_path'] = image_path

    logger.info("Image generation complete via ComfyUI")

    return shots
