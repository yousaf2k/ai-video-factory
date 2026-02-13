import json
import copy
import os
import config

def load_workflow(path, video_length_seconds=None):
    """Load workflow and optionally set video length and dimensions"""
    with open(path,"r",encoding="utf-8") as f:
        workflow = json.load(f)

    # Get dimensions from config
    width, height = config.calculate_image_dimensions()

    # Check if workflow is in UI format (has "nodes" array) or API format (node IDs as keys)
    if "nodes" in workflow:
        # Build a link lookup table: link_id -> [source_node_id, source_slot]
        link_lookup = {}
        if "links" in workflow:
            for link in workflow["links"]:
                # Link format: [link_id, source_node_id, source_slot, target_node_id, target_slot, type]
                if len(link) >= 3:
                    link_lookup[str(link[0])] = [str(link[1]), link[2]]

        # Convert from UI format to API format for ComfyUI
        api_format = {}
        for node in workflow["nodes"]:
            node_id = str(node["id"])
            node_data = {
                "class_type": node.get("type", ""),
                "inputs": {}
            }

            # Add inputs from the node's input connections
            if "inputs" in node:
                for input_def in node["inputs"]:
                    input_name = input_def["name"]
                    # If there's a link, it's a connection between nodes
                    if "link" in input_def and input_def["link"] is not None:
                        # Convert link ID to [source_node_id, source_slot]
                        link_id = str(input_def["link"])
                        if link_id in link_lookup:
                            node_data["inputs"][input_name] = link_lookup[link_id]
                        else:
                            # Fallback
                            node_data["inputs"][input_name] = [str(input_def["link"])]
                    # Otherwise it might be a widget value
                    elif "widget" in input_def:
                        # Will be processed in widgets_values section below
                        pass

            # Add widgets_values as inputs (for non-connected inputs)
            if "widgets_values" in node:
                widgets = node["widgets_values"]
                node_type = node.get("type", "")

                # Specialized handling for each node type based on their input structure
                # For LoadImage, widgets_values contains [filename, subtype]
                if node_type == "LoadImage" and len(widgets) >= 1:
                    node_data["inputs"]["image"] = widgets[0]
                # For CLIPTextEncode, widgets_values contains the text
                elif node_type == "CLIPTextEncode" and len(widgets) >= 1:
                    node_data["inputs"]["text"] = widgets[0]
                # For SaveVideo, widgets_values contains [fps, codec, format, filename_prefix, save_output]
                elif node_type == "SaveVideo" and len(widgets) >= 4:
                    node_data["inputs"]["fps"] = widgets[0]
                    node_data["inputs"]["codec"] = widgets[1]
                    node_data["inputs"]["format"] = widgets[2]
                    node_data["inputs"]["filename_prefix"] = widgets[3]
                    if len(widgets) >= 5:
                        node_data["inputs"]["save_output"] = widgets[4]
                # For WanImageToVideo, widgets_values contains [width, height, frames, batch_size]
                elif node_type == "WanImageToVideo" and len(widgets) >= 4:
                    # Use config dimensions instead of hardcoded values
                    node_data["inputs"]["width"] = width
                    node_data["inputs"]["height"] = height
                    node_data["inputs"]["batch_size"] = widgets[3]
                    frames = widgets[2]
                    # Set video length if specified
                    if video_length_seconds and node_id == config.WAN_VIDEO_NODE_ID:
                        frames = int(video_length_seconds * config.VIDEO_FPS)
                        node_data["inputs"]["length"] = frames
                        print(f"[INFO] Set video length: {video_length_seconds}s ({frames} frames at {config.VIDEO_FPS}fps)")
                        print(f"[INFO] Set dimensions: {width}x{height} ({config.IMAGE_ASPECT_RATIO} aspect ratio)")
                    else:
                        node_data["inputs"]["length"] = frames
                # For CLIPLoader
                elif node_type == "CLIPLoader" and len(widgets) >= 3:
                    node_data["inputs"]["clip_name1"] = widgets[0]
                    node_data["inputs"]["clip_name2"] = widgets[1]
                    node_data["inputs"]["type"] = widgets[2]
                # For VAELoader
                elif node_type == "VAELoader" and len(widgets) >= 1:
                    node_data["inputs"]["vae_name"] = widgets[0]
                # For UNETLoader
                elif node_type == "UNETLoader" and len(widgets) >= 1:
                    node_data["inputs"]["unet_name"] = widgets[0]
                    if len(widgets) >= 2:
                        node_data["inputs"]["weight_dtype"] = widgets[1]
                # For UnetLoaderGGUF
                elif node_type == "UnetLoaderGGUF" and len(widgets) >= 1:
                    node_data["inputs"]["unet_name"] = widgets[0]
                # For LoraLoaderModelOnly
                elif node_type == "LoraLoaderModelOnly" and len(widgets) >= 2:
                    node_data["inputs"]["lora_name"] = widgets[0]
                    node_data["inputs"]["strength_model"] = widgets[1]
                # For ModelSamplingSD3
                elif node_type == "ModelSamplingSD3" and len(widgets) >= 1:
                    node_data["inputs"]["shift"] = widgets[0]
                # For CreateVideo
                elif node_type == "CreateVideo" and len(widgets) >= 1:
                    node_data["inputs"]["fps"] = widgets[0]
                # For KSamplerAdvanced - skip this one, we'll handle it differently below
                elif node_type != "KSamplerAdvanced":
                    # For other simple nodes, just pass the widgets_values array
                    node_data["inputs"]["widgets_values"] = widgets

            # Special handling for KSamplerAdvanced - map by input definition
            if node.get("type") == "KSamplerAdvanced" and "widgets_values" in node:
                # Map widgets to inputs based on the node's input definitions
                if "inputs" in node:
                    widget_idx = 0
                    for input_def in node["inputs"]:
                        input_name = input_def["name"]
                        # Skip if this input has a link (connected to another node)
                        if "link" in input_def and input_def["link"] is not None:
                            continue
                        # Otherwise, use the next widget value
                        if widget_idx < len(node["widgets_values"]):
                            node_data["inputs"][input_name] = node["widgets_values"][widget_idx]
                            widget_idx += 1

            api_format[node_id] = node_data

        return api_format
    else:
        # Already in API format - set dimensions and video length
        wf = copy.deepcopy(workflow)

        # Set dimensions in WanImageToVideo node
        if config.WAN_VIDEO_NODE_ID in wf:
            wan_node = wf[config.WAN_VIDEO_NODE_ID]
            if wan_node.get('class_type') == 'WanImageToVideo':
                wan_node['inputs']['width'] = width
                wan_node['inputs']['height'] = height

                # Set video length if specified
                if video_length_seconds:
                    frames = int(video_length_seconds * config.VIDEO_FPS)
                    wan_node['inputs']['length'] = frames
                    print(f"[INFO] Set video length: {video_length_seconds}s ({frames} frames at {config.VIDEO_FPS}fps)")
                    print(f"[INFO] Set dimensions: {width}x{height} ({config.IMAGE_ASPECT_RATIO} aspect ratio)")

        return wf

def compile_workflow(template, shot, video_length_seconds=None):

    wf = copy.deepcopy(template)

    # Inject motion prompt (will be enhanced with trigger keywords below)
    motion_node_id = config.MOTION_PROMPT_NODE_ID
    base_motion_prompt = shot.get("motion_prompt", "")

    # ==========================================
    # MULTI-CAMERA LORA SYSTEM
    # ==========================================
    # Parse camera field - can be:
    # - Single camera as string: "drone"
    # - Multiple cameras as comma-separated string: "drone, zoom"
    # - Multiple cameras as list: ["drone", "zoom"]

    camera_field = shot.get("camera", "default")
    camera_types = []

    if isinstance(camera_field, list):
        # Already a list
        camera_types = [c.lower().strip() for c in camera_field]
    elif isinstance(camera_field, str):
        # Split by comma if present
        if ',' in camera_field:
            camera_types = [c.lower().strip() for c in camera_field.split(',')]
        else:
            camera_types = [camera_field.lower().strip()]
    else:
        # Fallback to default
        camera_types = ["default"]

    lora_mapping = config.CAMERA_LORA_MAPPING
    lora_nodes = getattr(config, 'LORA_NODES', [])

    # Collect all trigger keywords from all cameras
    all_trigger_keywords = []

    # Process each camera type and assign to LORA_NODES pairs sequentially
    for camera_index, camera_type in enumerate(camera_types):
        if not camera_type:
            continue

        # Skip if we've run out of available node pairs
        if camera_index >= len(lora_nodes):
            print(f"[WARN] Camera '{camera_type}' skipped - no available LoRA node pairs (max 4 cameras)")
            continue

        # Get the node pair for this camera
        node_pair = lora_nodes[camera_index]
        high_noise_node_id = node_pair.get("HIGH_NOISE_LORA_NODE_ID")
        low_noise_node_id = node_pair.get("LOW_NOISE_LORA_NODE_ID")

        # Find matching camera configuration
        camera_config = None

        # Try exact match first
        if camera_type in lora_mapping:
            camera_config = lora_mapping[camera_type]
        else:
            # Try partial match
            for key, value in lora_mapping.items():
                if key != "default" and key in camera_type:
                    camera_config = value
                    break

            # Fall back to default
            if camera_config is None:
                camera_config = lora_mapping.get("default", {})

        if not isinstance(camera_config, dict):
            continue

        # Get LoRA configuration for this camera
        trigger_keyword = camera_config.get("trigger_keyword", "")
        high_noise_lora = camera_config.get("high_noise_lora")
        low_noise_lora = camera_config.get("low_noise_lora")
        strength_low = camera_config.get("strength_low")
        strength_high = camera_config.get("strength_high")

        # Collect trigger keyword
        if trigger_keyword:
            all_trigger_keywords.append(trigger_keyword)

        # Use global defaults if camera-specific strengths not provided
        if strength_low is None:
            strength_low = getattr(config, 'LORA_STRENGTH_LOW', 0.8)
        if strength_high is None:
            strength_high = getattr(config, 'LORA_STRENGTH_HIGH', 0.8)

        print(f"\n[LORA] Processing camera {camera_index + 1}/{len(camera_types)}: '{camera_type}' -> Pair {camera_index}")

        # Update low noise LoRA node if configured
        if low_noise_node_id and low_noise_lora:
            if low_noise_node_id in wf:
                old_lora = wf[low_noise_node_id]["inputs"].get("lora_name", "")
                old_strength = wf[low_noise_node_id]["inputs"].get("strength_model", "")

                wf[low_noise_node_id]["inputs"]["lora_name"] = low_noise_lora
                wf[low_noise_node_id]["inputs"]["strength_model"] = strength_low

                print(f"  Low Node {low_noise_node_id}: {low_noise_lora} (strength: {strength_low})")
                if old_lora and old_lora != low_noise_lora:
                    print(f"    (was: {old_lora})")
        elif low_noise_lora == "":
            print(f"  Low Node {low_noise_node_id}: SKIPPED (empty filename)")

        # Update high noise LoRA node if configured
        if high_noise_node_id and high_noise_lora:
            if high_noise_node_id in wf:
                old_lora = wf[high_noise_node_id]["inputs"].get("lora_name", "")
                old_strength = wf[high_noise_node_id]["inputs"].get("strength_model", "")

                wf[high_noise_node_id]["inputs"]["lora_name"] = high_noise_lora
                wf[high_noise_node_id]["inputs"]["strength_model"] = strength_high

                print(f"  High Node {high_noise_node_id}: {high_noise_lora} (strength: {strength_high})")
                if old_lora and old_lora != high_noise_lora:
                    print(f"    (was: {old_lora})")
        elif high_noise_lora == "":
            print(f"  High Node {high_noise_node_id}: SKIPPED (empty filename)")

    # Append all trigger keywords to motion prompt
    if all_trigger_keywords:
        enhanced_prompt = base_motion_prompt
        for keyword in all_trigger_keywords:
            if keyword and keyword not in enhanced_prompt:
                enhanced_prompt += f", {keyword}"

        # Inject enhanced motion prompt
        if motion_node_id in wf:
            wf[motion_node_id]["inputs"]["text"] = enhanced_prompt

        print(f"\n[TRIGGERS] Added: {', '.join(all_trigger_keywords)}")

    # Inject base motion prompt if no triggers
    elif motion_node_id in wf and base_motion_prompt:
        wf[motion_node_id]["inputs"]["text"] = base_motion_prompt

    # Inject image path to LoadImage node if available
    if "image_path" in shot and shot["image_path"]:
        load_node_id = config.LOAD_IMAGE_NODE_ID
        if load_node_id in wf:
            image_path = shot["image_path"]
            # Convert to absolute path if relative (ComfyUI requires absolute paths)
            if image_path and not os.path.isabs(image_path):
                image_path = os.path.abspath(image_path)
            # Normalize to use forward slashes (ComfyUI handles this better)
            image_path = image_path.replace('\\', '/')
            wf[load_node_id]["inputs"]["image"] = image_path

    # Set video length in WanImageToVideo node if specified
    if video_length_seconds and config.WAN_VIDEO_NODE_ID in wf:
        wan_node = wf[config.WAN_VIDEO_NODE_ID]
        # Check if it's API format (inputs has direct values) or UI format (has widgets_values)
        if "length" in wan_node.get("inputs", {}):
            # API format - set length directly
            frames = int(video_length_seconds * config.VIDEO_FPS)
            wan_node["inputs"]["length"] = frames
        elif "widgets_values" in wan_node["inputs"]:
            # UI format - update widgets_values array
            widgets = wan_node["inputs"]["widgets_values"]
            frames = int(video_length_seconds * config.VIDEO_FPS)
            wan_node["inputs"]["widgets_values"] = [widgets[0], widgets[1], frames, widgets[3]]

    return wf