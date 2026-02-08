"""
Configuration for AI Film Studio System
"""
import os

# ==========================================
# GEMINI API CONFIGURATION
# ==========================================
# Get your API key from: https://ai.google.dev/
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Text generation model (for story, shots, etc.)
GEMINI_TEXT_MODEL = "gemini-2.0-flash"

# Image generation model (NanoBanana Pro)
GEMINI_IMAGE_MODEL = "gemini-3-pro-image-preview"

# ==========================================
# COMFYUI CONFIGURATION
# ==========================================
# ComfyUI server URL
COMFY_URL = "http://127.0.0.1:8188"

# Path to your Wan 2.2 workflow template
WORKFLOW_PATH = "workflow/wan22_workflow.json"

# Node IDs in your workflow
# IMPORTANT: Open your workflow in ComfyUI, right-click the LoadImage node → "Node ID for Save"
# Update this value with the actual node ID from your workflow
LOAD_IMAGE_NODE_ID = "97"  # User needs to update this

# Motion prompt node ID (currently node 7 in shot_planner.py)
MOTION_PROMPT_NODE_ID = "93"

# WanImageToVideo node ID (for setting video length)
WAN_VIDEO_NODE_ID = "98"

# ==========================================
# IMAGE GENERATION CONFIGURATION
# ==========================================
# Image generation mode: "gemini" or "comfyui"
IMAGE_GENERATION_MODE = "gemini"  # Options: "gemini", "comfyui"

# Output directory for generated images
IMAGES_OUTPUT_DIR = "output/generated_images"

# Image aspect ratio (options: "1:1", "16:9", "9:16", "4:3", "3:4")
IMAGE_ASPECT_RATIO = "16:9"

# Image resolution (options: "512", "1024", "1280" "2048")
IMAGE_RESOLUTION = "1280"

# ComfyUI image generation workflow path
IMAGE_WORKFLOW_PATH = "workflow/image_generation_workflow.json"

# Node IDs for image generation workflow (ComfyUI mode)
# These need to match your ComfyUI image generation workflow
IMAGE_TEXT_NODE_ID = "6"        # CLIPTextEncode node for positive prompt
IMAGE_NEG_TEXT_NODE_ID = None   # Flux doesn't use negative prompts (set to None)
IMAGE_KSAMPLER_NODE_ID = "13"   # SamplerCustomAdvanced node (Flux uses this, not KSampler)
IMAGE_VAE_NODE_ID = "8"         # VAEDecode node
IMAGE_SAVE_NODE_ID = "9"        # SaveImage node

# ==========================================
# VIDEO GENERATION CONFIGURATION
# ==========================================
# Default video length per shot (in seconds)
DEFAULT_SHOT_LENGTH = 5.0

# Video framerate (fps)
VIDEO_FPS = 24

# Target total video length (in seconds)
# Set to None to generate based on story length
TARGET_VIDEO_LENGTH = None  # or specify like: 60.0 for 60 seconds

# Video rendering timeout (in seconds)
# Maximum time to wait for a single video render to complete
VIDEO_RENDER_TIMEOUT = 1800  # 30 minutes


# ==========================================
# DIMENSION CALCULATION HELPERS
# ==========================================
def calculate_image_dimensions(aspect_ratio=IMAGE_ASPECT_RATIO, resolution=IMAGE_RESOLUTION):
    """
    Calculate image width and height from aspect ratio and resolution.

    Args:
        aspect_ratio: String like "16:9", "9:16", "1:1", "4:3", "3:4"
        resolution: String like "512", "1024", "2048" (width for landscape, height for portrait)

    Returns:
        Tuple of (width, height) as integers
    """
    res = int(resolution)

    # Parse aspect ratio
    if ':' in aspect_ratio:
        parts = aspect_ratio.split(':')
        ar_w = int(parts[0])
        ar_h = int(parts[1])
    else:
        # Default to 1:1 if format is wrong
        ar_w = 1
        ar_h = 1

    # Determine orientation and calculate dimensions
    if ar_w >= ar_h:
        # Landscape or square: resolution is width
        width = res
        height = int(res * ar_h / ar_w)
    else:
        # Portrait: resolution is height
        height = res
        width = int(res * ar_w / ar_h)

    # Ensure dimensions are multiples of 8 (required by most AI models)
    width = (width // 8) * 8
    height = (height // 8) * 8

    return width, height


# Pre-calculate current dimensions
IMAGE_WIDTH, IMAGE_HEIGHT = calculate_image_dimensions()
