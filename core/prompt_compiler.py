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

    # Inject motion prompt
    motion_node_id = config.MOTION_PROMPT_NODE_ID
    if motion_node_id in wf:
        if "text" not in wf[motion_node_id]["inputs"]:
            wf[motion_node_id]["inputs"]["text"] = shot["motion_prompt"]
        else:
            # Update existing text
            wf[motion_node_id]["inputs"]["text"] = shot["motion_prompt"]

    # Inject camera-based LoRA
    camera_type = shot.get("camera", "default").lower()
    lora_mapping = config.CAMERA_LORA_MAPPING

    # Find the matching LoRA configuration (use exact match first, then partial match, then default)
    lora_config = None
    trigger_keyword = ""

    # Check if mapping is old-style (string) or new-style (dict)
    if camera_type in lora_mapping:
        mapping = lora_mapping[camera_type]
        if isinstance(mapping, dict):
            # New-style dict with lora_file and trigger_keyword
            lora_config = mapping
            lora_name = mapping.get("lora_file")
            trigger_keyword = mapping.get("trigger_keyword", "")
        else:
            # Old-style string (just the lora filename)
            lora_name = mapping
            lora_config = {"lora_file": mapping, "trigger_keyword": ""}
    else:
        # Try partial match (e.g., "slow pan" matches "pan")
        for key, value in lora_mapping.items():
            if key != "default" and key in camera_type:
                if isinstance(value, dict):
                    lora_name = value.get("lora_file")
                    trigger_keyword = value.get("trigger_keyword", "")
                else:
                    lora_name = value
                    break
        # Fall back to default if no match found
        if lora_name is None:
            default_mapping = lora_mapping.get("default", {})
            if isinstance(default_mapping, dict):
                lora_name = default_mapping.get("lora_file", list(default_mapping.values())[0])
                trigger_keyword = default_mapping.get("trigger_keyword", "")
            else:
                lora_name = default_mapping
                trigger_keyword = ""

    # Update LoRA node if configured
    if hasattr(config, 'LORA_NODE_ID') and config.LORA_NODE_ID and lora_name:
        lora_node_id = config.LORA_NODE_ID
        if lora_node_id in wf:
            old_lora = wf[lora_node_id]["inputs"].get("lora_name", "")
            wf[lora_node_id]["inputs"]["lora_name"] = lora_name
            print(f"[LORA] Camera '{camera_type}' -> LoRA: {lora_name}")
            if old_lora != lora_name:
                print(f"       (was: {old_lora})")

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