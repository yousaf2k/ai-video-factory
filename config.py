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
WORKFLOW_PATH = "workflow/video/wan22_workflow.json"

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
IMAGE_GENERATION_MODE = "comfyui"  # Options: "gemini", "comfyui"

# Default negative prompt for ComfyUI image generation
# Common negative prompts: "blurry, low quality, distorted, deformed"
DEFAULT_NEGATIVE_PROMPT = ""

# Number of images to generate per shot (with different seeds)
# Set to 1 for single image per shot, or higher for multiple variations
# Each image will be named: shot_001_001.png, shot_001_002.png, etc.
IMAGES_PER_SHOT = 1

# Output directory for generated images
IMAGES_OUTPUT_DIR = "output/generated_images"

# Image aspect ratio (options: "1:1", "16:9", "9:16", "4:3", "3:4")
IMAGE_ASPECT_RATIO = "16:9"

# Image resolution (options: "512", "1024", "1280" "2048")
IMAGE_RESOLUTION = "1280"

# ComfyUI image generation workflow path
IMAGE_WORKFLOW_PATH = "workflow/image/image_generation_workflow.json"

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

# Maximum number of shots to generate (for testing)
# Set to 0 for no limit (generates all shots from story)
# Recommended for testing: 3-5 shots
DEFAULT_MAX_SHOTS = 0  # 0 = no limit

# Video framerate (fps)
VIDEO_FPS = 24

# Target total video length (in seconds)
# Set to None to generate based on story length
# Note: If both DEFAULT_MAX_SHOTS and TARGET_VIDEO_LENGTH are set,
#       max_shots will be calculated as: int(TARGET_VIDEO_LENGTH / DEFAULT_SHOT_LENGTH)
TARGET_VIDEO_LENGTH = None  # or specify like: 60.0 for 60 seconds

# Video rendering timeout (in seconds)
# Maximum time to wait for a single video render to complete
VIDEO_RENDER_TIMEOUT = 1800  # 30 minutes

# LoRA node ID in the workflow (for camera-based LoRA loading)
LORA_NODE_ID = "101"  # LoraLoaderModelOnly node to update based on camera type

# ==========================================
# CAMERA-TO-LORA MAPPING
# ==========================================
# Map camera types to specific LoRA files and trigger keywords for different motion effects
# Camera types from shots.json will be matched to these LoRAs
# Trigger keywords are appended to image prompts to activate specific LoRA effects
CAMERA_LORA_MAPPING = {
    "slow pan": {
        "lora_file": "wan2.2_i2v__lightx2v_4steps_lora_v1__high_noise_model.safetensors",
        "trigger_keyword": "slow pan movement"
    },
    "pan": {
        "lora_file": "wan2.2_i2v__lightx2v_4steps_lora_v1__high_noise_model.safetensors",
        "trigger_keyword": "pan movement"
    },
    "static": {
        "lora_file": "wan2.2_i2v__lightx2v_4steps_lora_v1_low_noise_model.safetensors",
        "trigger_keyword": "static shot"
    },
    "dolly": {
        "lora_file": "wan2.2_i2v__lightx2v_4steps_lora_v1__high_noise_model.safetensors",
        "trigger_keyword": "dolly movement"
    },
    "orbit": {
        "lora_file": "wan2.2_i2v__lightx2v_4steps_lora_v1__high_noise_model.safetensors",
        "trigger_keyword": "orbit movement"
    },
    "zoom": {
        "lora_file": "wan2.2_i2v__lightx2v_4steps_lora_v1__high_noise_model.safetensors",
        "trigger_keyword": "zoom in"
    },
    "tracking": {
        "lora_file": "wan2.2_i2v__lightx2v_4steps_lora_v1__high_noise_model.safetensors",
        "trigger_keyword": "tracking shot"
    },
    "default": {
        "lora_file": "wan2.2_i2v__lightx2v_4steps_lora_v1__high_noise_model.safetensors",
        "trigger_keyword": ""
    }
}

# Legacy support: if you prefer simple string mapping, this fallback is used
# The system will automatically use empty trigger keywords for old-style mappings
_LEGACY_CAMERA_LORA_MAPPING = CAMERA_LORA_MAPPING


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


# ==========================================
# WORKFLOW EXECUTION MODE
# ==========================================
# Step progression mode: "auto" or "manual"
# - auto: Automatically proceed to next step after completion
# - manual: Stop after each step, require user to continue or re-execute
AUTO_STEP_MODE = True  # True = auto, False = manual


# ==========================================
# AGENT CONFIGURATION
# ==========================================
# Default agents to use for each step
# Agent files are stored in agents/{type}/{name}.txt
# Available agents depend on files in the agents folder

# Story generation agent (default, dramatic, documentary)
STORY_AGENT = "default"

# Image prompt agent (default, artistic)
IMAGE_AGENT = "default"

# Video motion agent (default, cinematic)
VIDEO_AGENT = "default"

# Narration agent (default, documentary, professional, storytelling)
NARRATION_AGENT = "default"


# ==========================================
# NARRATION/TTS CONFIGURATION
# ==========================================
# Whether to generate narration for videos
GENERATE_NARRATION = False  # Set to True to enable narration by default

# TTS method: "comfyui", "local" (edge-tts), or "elevenlabs"
TTS_METHOD = "local"  # Options: "comfyui", "local", "elevenlabs"

# ComfyUI TTS workflow path
TTS_WORKFLOW_PATH = "workflow/voice/tts_workflow.json"

# ==========================================
# ELEVENLABS API CONFIGURATION
# ==========================================
# Get your API key from: https://elevenlabs.io/app/settings/api-keys
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# Default voice for TTS
# For edge-tts: voice names like "en-US-AriaNeural", "en-GB-SoniaNeural"
# For ComfyUI: depends on your workflow (e.g., "female_01", "male_01")
# For ElevenLabs: voice IDs or names (e.g., "Rachel", "Domi", "21m00Tcm4TlvDq8ikWAM")
TTS_VOICE = "en-US-AriaNeural"

# ElevenLabs model selection
# Options: "eleven_multilingual_v2", "eleven_turbo_v2", "eleven_monolingual_v1"
ELEVENLABS_MODEL = "eleven_multilingual_v2"

# ElevenLabs voice settings
ELEVENLABS_STABILITY = 0.5  # 0.0 to 1.0 (higher = more stable)
ELEVENLABS_SIMILARITY = 0.75  # 0.0 to 1.0 (higher = more similar to original voice)


# Pre-calculate current dimensions
IMAGE_WIDTH, IMAGE_HEIGHT = calculate_image_dimensions()
