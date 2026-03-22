import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.prompt_compiler import load_workflow
import config

# Test data
wf_path = "workflow/video/wan22_flf2v_api.json"
aspect_ratio = "9:16"

# Load workflow with 9:16 aspect ratio
try:
    wf = load_workflow(wf_path, aspect_ratio=aspect_ratio)
    
    # Check node 150 (WanFirstLastFrameToVideo)
    node_id = "150"
    if node_id in wf:
        node = wf[node_id]
        inputs = node.get('inputs', {})
        width = inputs.get('width')
        height = inputs.get('height')
        print(f"Node {node_id} Dimensions:")
        print(f"  Width: {width}")
        print(f"  Height: {height}")
        
        if width == 720 and height == 1280:
            print("[SUCCESS] Aspect ratio 9:16 applied correctly (720x1280)")
        else:
            print("[FAIL] Aspect ratio NOT applied correctly!")
    else:
        print(f"[ERROR] Node {node_id} not found in output workflow.")

except Exception as e:
    print(f"[ERROR] failed: {e}")
    import traceback
    traceback.print_exc()
