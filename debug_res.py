
import json
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config
from core.prompt_compiler import load_workflow

def test_resolution():
    workflow_path = "workflow/video/wan22_flf2v_10s_vfi_sr.json"
    aspect_ratio = "9:16"  # Portrait like the user's JSON
    resolution = "480p"
    
    print(f"Testing workflow: {workflow_path}")
    print(f"Target Resolution: {resolution}")
    
    # Load and process
    try:
        wf = load_workflow(workflow_path, aspect_ratio=aspect_ratio, resolution=resolution)
        
        # Check node 150
        node_150 = wf.get("150")
        if node_150:
            width = node_150["inputs"].get("width")
            height = node_150["inputs"].get("height")
            print(f"Node 150 Width: {width}")
            print(f"Node 150 Height: {height}")
            if width == 480 and height == 848:
                print("SUCCESS: Resolution injected correctly.")
            else:
                print(f"FAILURE: Resolution is {width}x{height}, expected 480x848")
        else:
            print("FAILURE: Node 150 not found in processed workflow.")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_resolution()
