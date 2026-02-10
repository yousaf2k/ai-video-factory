"""
ComfyUI Image Generation Module
Generates images using ComfyUI workflows (SDXL, Flux, etc.)
"""
import requests
import json
import copy
import config
import os


def generate_image_comfyui(prompt: str, output_path: str, negative_prompt: str = "", seed: int = None):
    """
    Generate a single image using ComfyUI workflow.

    Args:
        prompt: Text description of the image to generate
        output_path: Full path where the image will be saved
        negative_prompt: Optional negative prompt for better quality
        seed: Optional random seed for reproducibility

    Returns:
        Path to the generated image file, or None if failed
    """
    try:
        # Load the image generation workflow
        with open(config.IMAGE_WORKFLOW_PATH, 'r', encoding='utf-8') as f:
            workflow = json.load(f)

        # Get dimensions from config
        width, height = config.calculate_image_dimensions()

        # Inject prompts into the workflow
        # The workflow structure needs to be converted to API format
        api_format = _convert_workflow_to_api_format(workflow, width=width, height=height)

        # Set the text prompts
        if config.IMAGE_TEXT_NODE_ID in api_format:
            api_format[config.IMAGE_TEXT_NODE_ID]["inputs"]["text"] = prompt

        if config.IMAGE_NEG_TEXT_NODE_ID in api_format and negative_prompt:
            api_format[config.IMAGE_NEG_TEXT_NODE_ID]["inputs"]["text"] = negative_prompt

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

        # Set output filename for SaveImage node
        if config.IMAGE_SAVE_NODE_ID in api_format:
            # Extract just the filename from the full path
            filename = os.path.basename(output_path)
            api_format[config.IMAGE_SAVE_NODE_ID]["inputs"]["filename_prefix"] = os.path.splitext(filename)[0]

        # Submit to ComfyUI
        payload = {
            "prompt": api_format
        }

        response = requests.post(
            f"{config.COMFY_URL}/prompt",
            json=payload
        )

        if response.status_code != 200:
            print(f"[ERROR] ComfyUI returned status {response.status_code}: {response.text}")
            return None

        result = response.json()
        prompt_id = result.get("prompt_id")

        if not prompt_id:
            print("[ERROR] No prompt_id in response")
            return None

        # Wait for completion and get the result
        return _wait_for_image(prompt_id, output_path)

    except Exception as e:
        print(f"[ERROR] ComfyUI image generation failed: {e}")
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


def _wait_for_image(prompt_id, output_path, timeout=300):
    """Wait for ComfyUI to finish generating the image"""
    import time

    start_time = time.time()

    while True:
        if time.time() - start_time > timeout:
            print("[ERROR] Timeout waiting for image generation")
            return None

        try:
            # Check queue status
            response = requests.get(f"{config.COMFY_URL}/history/{prompt_id}")

            if response.status_code != 200:
                time.sleep(1)
                continue

            history = response.json()

            if prompt_id not in history:
                time.sleep(1)
                continue

            # Check if processing is complete
            status = history[prompt_id].get("status", {})

            if status.get("completed", False):
                # Get the output image
                outputs = history[prompt_id].get("outputs", {})

                for node_id, node_output in outputs.items():
                    if "images" in node_output and len(node_output["images"]) > 0:
                        image_info = node_output["images"][0]
                        image_filename = image_info.get("filename", "")
                        subfolder = image_info.get("subfolder", "")

                        # Construct the URL to download the image
                        if subfolder:
                            url = f"{config.COMFY_URL}/view?filename={image_filename}&subfolder={subfolder}&type=output"
                        else:
                            url = f"{config.COMFY_URL}/view?filename={image_filename}&type=output"

                        # Download the image
                        img_response = requests.get(url)

                        if img_response.status_code == 200:
                            # Save to output path
                            os.makedirs(os.path.dirname(output_path), exist_ok=True)

                            with open(output_path, 'wb') as f:
                                f.write(img_response.content)

                            print(f"[PASS] Generated: {output_path}")
                            return output_path
                        else:
                            print(f"[ERROR] Failed to download image: {img_response.status_code}")
                            return None

            # If still processing, wait
            if status.get("status", "") in ["queued", "processing"]:
                time.sleep(1)
                continue
            else:
                # Error status
                print(f"[ERROR] ComfyUI error: {status}")
                return None

        except Exception as e:
            print(f"[ERROR] Error waiting for image: {e}")
            time.sleep(1)
            continue


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
    print(f"\nGenerating {len(shots)} images using ComfyUI...")

    # Get and display dimensions
    width, height = config.calculate_image_dimensions()
    print(f"[INFO] Image dimensions: {width}x{height} ({config.IMAGE_ASPECT_RATIO} aspect ratio)")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    for idx, shot in enumerate(shots, start=1):
        # Generate filename
        filename = f"shot_{idx:03d}.png"
        output_path = os.path.join(output_dir, filename)

        # Generate image
        image_prompt = shot.get('image_prompt', '')
        if not image_prompt:
            print(f"[SKIP] Shot {idx}: No image_prompt")
            shot['image_path'] = None
            continue

        print(f"[{idx}/{len(shots)}] Generating via ComfyUI: {image_prompt[:60]}...")

        image_path = generate_image_comfyui(image_prompt, output_path, negative_prompt)

        # Add image_path to shot dictionary
        shot['image_path'] = image_path

    print(f"\n[INFO] Image generation complete via ComfyUI")

    return shots
