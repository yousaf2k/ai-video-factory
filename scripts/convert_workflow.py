#!/usr/bin/env python3
"""
Helper script to convert ComfyUI UI format workflows to API format
and validate node IDs match config.py requirements.
"""
import json
import sys
from pathlib import Path

def convert_ui_to_api(workflow_data):
    """
    Convert ComfyUI UI format to API format.

    UI format has "nodes" array with link lookup
    API format uses node IDs as keys with direct connections
    """
    if "nodes" not in workflow_data:
        print("Already in API format (no 'nodes' array found)")
        return workflow_data

    nodes = workflow_data["nodes"]
    links = workflow_data.get("links", [])

    # Build link lookup: link_id -> [source_node_id, source_slot]
    link_lookup = {}
    for link in links:
        if len(link) >= 3:
            link_lookup[str(link[0])] = [str(link[1]), link[2]]

    api_format = {}

    for node in nodes:
        node_id = str(node["id"])
        node_data = {
            "class_type": node.get("type", ""),
            "inputs": {}
        }

        # Process input connections
        if "inputs" in node:
            for input_def in node["inputs"]:
                input_name = input_def["name"]
                if "link" in input_def and input_def["link"] is not None:
                    link_id = str(input_def["link"])
                    if link_id in link_lookup:
                        node_data["inputs"][input_name] = link_lookup[link_id]

        # Process widgets_values
        if "widgets_values" in node:
            widgets = node["widgets_values"]
            node_type = node.get("type", "")

            if node_type == "LoadImage" and len(widgets) >= 1:
                node_data["inputs"]["image"] = widgets[0]
            elif node_type == "CLIPTextEncode" and len(widgets) >= 1:
                node_data["inputs"]["text"] = widgets[0]
            elif node_type == "SaveImage" and len(widgets) >= 1:
                node_data["inputs"]["filename_prefix"] = widgets[0]
            elif node_type == "UNETLoader" and len(widgets) >= 2:
                node_data["inputs"]["unet_name"] = widgets[0]
                node_data["inputs"]["weight_dtype"] = widgets[1]
            elif node_type == "DualCLIPLoader" and len(widgets) >= 3:
                node_data["inputs"]["clip_name1"] = widgets[0]
                node_data["inputs"]["clip_name2"] = widgets[1]
                node_data["inputs"]["type"] = widgets[2]
            elif node_type == "VAELoader" and len(widgets) >= 1:
                node_data["inputs"]["vae_name"] = widgets[0]
            elif node_type == "EmptyFlux2LatentImage" and len(widgets) >= 3:
                node_data["inputs"]["width"] = widgets[0]
                node_data["inputs"]["height"] = widgets[1]
                node_data["inputs"]["batch_size"] = widgets[2]
            elif node_type == "SamplerCustomAdvanced":
                # Map widgets to inputs by name
                if "inputs" in node:
                    widget_idx = 0
                    for input_def in node["inputs"]:
                        if "link" not in input_def or input_def["link"] is None:
                            if widget_idx < len(widgets):
                                input_name = input_def["name"]
                                node_data["inputs"][input_name] = widgets[widget_idx]
                                widget_idx += 1
            elif node_type == "IPAdapter":
                # IPAdapter has many parameters, handle carefully
                if len(widgets) >= 1:
                    node_data["inputs"]["weight"] = widgets[0]
                if len(widgets) >= 2:
                    node_data["inputs"]["ipadapter_file"] = widgets[1]

        api_format[node_id] = node_data

    return api_format


def validate_workflow_nodes(workflow_data, workflow_name):
    """
    Validate that workflow has required nodes with correct IDs.
    """
    required_nodes = {
        "flux_ipadapter_then": {
            "1": "LoadImage",
            "2": "UNETLoader",
            "3": "DualCLIPLoader",
            "5": "IPAdapter",
            "6": "CLIPTextEncode",
            "8": "VAEDecode",
            "9": "SaveImage",
            "10": "EmptyFlux2LatentImage",
            "13": "SamplerCustomAdvanced",
            "14": "VAELoader"
        },
        "flux_ipadapter_now": {
            "1": "LoadImage",
            "2": "UNETLoader",
            "3": "DualCLIPLoader",
            "5": "IPAdapter",
            "6": "CLIPTextEncode",
            "8": "VAEDecode",
            "9": "SaveImage",
            "10": "EmptyFlux2LatentImage",
            "13": "SamplerCustomAdvanced",
            "14": "VAELoader"
        },
        "flux_background": {
            "2": "UNETLoader",
            "3": "DualCLIPLoader",
            "6": "CLIPTextEncode",
            "8": "VAEDecode",
            "9": "SaveImage",
            "10": "EmptyFlux2LatentImage",
            "13": "SamplerCustomAdvanced",
            "14": "VAELoader"
        }
    }

    if workflow_name not in required_nodes:
        print(f"Warning: Unknown workflow type '{workflow_name}'")
        return True

    required = required_nodes[workflow_name]
    errors = []

    for node_id, expected_type in required.items():
        if node_id not in workflow_data:
            errors.append(f"Missing node {node_id} ({expected_type})")
        else:
            actual_type = workflow_data[node_id].get("class_type", "")
            if actual_type != expected_type:
                errors.append(f"Node {node_id} is {actual_type}, expected {expected_type}")

    if errors:
        print(f"\n❌ Validation errors in {workflow_name}:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print(f"✅ {workflow_name}: All required nodes present with correct IDs")
        return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_workflow.py <workflow.json> [workflow_name]")
        print("\nExample:")
        print("  python convert_workflow.py workflow/image/flux_ipadapter_then.json flux_ipadapter_then")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    workflow_name = sys.argv[2] if len(sys.argv) > 2 else input_path.stem

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    # Load workflow
    print(f"Loading: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        workflow_data = json.load(f)

    # Convert if needed
    if "nodes" in workflow_data:
        print("Converting from UI format to API format...")
        api_format = convert_ui_to_api(workflow_data)

        # Save converted version
        output_path = input_path.parent / f"{input_path.stem}_api.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(api_format, f, indent=2)
        print(f"Saved API format: {output_path}")

        workflow_data = api_format

    # Validate nodes
    validate_workflow_nodes(workflow_data, workflow_name)

    # Print node summary
    print(f"\n📊 Node Summary ({workflow_name}):")
    print(f"  Total nodes: {len(workflow_data)}")
    print("\n  Nodes:")
    for node_id in sorted(workflow_data.keys(), key=int):
        node = workflow_data[node_id]
        print(f"    {node_id}: {node.get('class_type', 'Unknown')}")


if __name__ == "__main__":
    main()
