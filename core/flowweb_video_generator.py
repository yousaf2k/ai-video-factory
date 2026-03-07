import os
import subprocess
import threading
import time
from config import OUTPUT_DIR, PROJECT_ROOT

# Lock for sequential generation to avoid browser profile conflicts
flow_generation_lock = threading.Lock()

def generate_video_flowweb(image_path, prompt, output_path, aspect_ratio="16:9"):
    """
    Interface for Google Flow video generation.
    - image_path: Local path to the source image
    - prompt: Visual/Motion prompt for the video
    - output_path: Destination path for the generated .mp4
    - aspect_ratio: '16:9' or '9:16'
    """
    with flow_generation_lock:
        print(f"--- Google Flow Video Generation Start ---")
        print(f"Image: {image_path}")
        print(f"Prompt: {prompt}")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        subprocess_script = os.path.join(PROJECT_ROOT, "core", "flowweb_video_subprocess.py")
        
        cmd = [
            "python", subprocess_script,
            "--image", image_path,
            "--prompt", prompt,
            "--output", output_path,
            "--aspect_ratio", aspect_ratio
        ]
        
        try:
            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout)
            
            if os.path.exists(output_path):
                print(f"SUCCESS: Google Flow video generated and saved: {output_path}")
                return output_path
            else:
                print(f"ERROR: Google Flow subprocess finished but output file missing: {output_path}")
                print(f"Subprocess Output Extra: {result.stderr}")
                return None
                
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Google Flow subprocess failed with exit code {e.returncode}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            return None
        except Exception as e:
            print(f"ERROR: Unexpected exception during Google Flow generation: {e}")
            return None
