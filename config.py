"""
Configuration for AI Film Studio System
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ==========================================
# LLM PROVIDER CONFIGURATION
# ==========================================
# Primary LLM provider (gemini, openai, zhipu, qwen, kimi, ollama, lmstudio)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

# Maximum tokens for LLM responses (increase for large JSON outputs)
# Set higher to avoid truncation when generating many shots
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "16384"))  # Default: 16K tokens

# Batch size for generating shots (process scenes in batches to avoid truncation)
SHOT_GENERATION_BATCH_SIZE = int(os.getenv("SHOT_GENERATION_BATCH_SIZE", "1"))  # Process 1 scene at a time

# Maximum parallel threads for batch processing (only for cloud providers, not local models)
# Higher values = faster processing but more API rate limits
# Recommended: 3-5 for most APIs, 1-2 for free tier accounts
MAX_PARALLEL_BATCH_THREADS = int(os.getenv("MAX_PARALLEL_BATCH_THREADS", "5"))  # Default: 5 parallel threads

# ==========================================
# GEMINI API CONFIGURATION
# ==========================================
# Get your API key from: https://ai.google.dev/
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Text generation model (for story, shots, etc. "gemini-2.0-flash" and "gemini-3-flash-preview" is faster and cheaper, "gemini-3-pro-preview" is higher quality but more expensive)
GEMINI_TEXT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ==========================================
# OPENAI (CHATGPT) CONFIGURATION
# ==========================================
# Get your API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ChatGPT model (gpt-4o is latest, gpt-4o-mini is faster/cheaper)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# ==========================================
# ZHIPU CONFIGURATION
# ==========================================
# Get your API key from Z.AI platform
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")


# ==========================================
# QWEN (ALIBABA CLOUD) CONFIGURATION
# ==========================================
# Get your API key from Alibaba Cloud
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")

# Qwen model (qwen-max is latest)
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-max")

# ==========================================
# KIMI (MOONSHOT) CONFIGURATION
# ==========================================
# Get your API key from Moonshot AI
KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")

# Kimi K2 2.5 model (kimi-labs is recommended)
KIMI_MODEL = os.getenv("KIMI_MODEL", "kimi-labs")

# ==========================================
# OLLAMA CONFIGURATION (Local LLM)
# ==========================================
# Ollama server URL (default: localhost:11434)
# Download Ollama from: https://ollama.com
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Model to use (e.g., llama2, mistral, codellama, qwen2, etc.)
# List available models: ollama list
# Download models: ollama pull <model-name>
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")

# ==========================================
# LM STUDIO CONFIGURATION (Local LLM)
# ==========================================
# LM Studio server URL (default: localhost:1234)
# Download LM Studio from: https://lmstudio.ai
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234")

# Model to use (e.g., lmstudio-community/qwen2, etc.)
# Models are managed in LM Studio application
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "lmstudio-community/qwen2")

# Image generation model (NanoBanana Pro)
GEMINI_IMAGE_MODEL = "gemini-3-pro-image-preview"

# ==========================================
# COMFYUI CONFIGURATION
# ==========================================
# ComfyUI server URL
COMFY_URL = "http://127.0.0.1:8188"

# ComfyUI output directory (where ComfyUI saves generated videos/images)
# Set this if ComfyUI is installed in a different location
# Leave as empty string "" to auto-detect from ComfyUI API
# Examples:
#   COMFY_OUTPUT_DIR = ""  # Auto-detect (recommended)
#   COMFY_OUTPUT_DIR = "C:/ComfyUI/output"  # Manual path for Windows
#   COMFY_OUTPUT_DIR = "/home/user/ComfyUI/output"  # Manual path for Linux/Mac
COMFY_OUTPUT_DIR = "C:/ComfyUI_Portable/ComfyUI/output"

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
DEFAULT_NEGATIVE_PROMPT = "Vibrant colors, overexposed, static, blurry details, subtitles, style, artwork, painting, image, still, overall grayish, worst quality, low quality, JPEG compression residue, ugly, incomplete, extra fingers, poorly drawn hands, poorly drawn faces, deformed, disfigured, distorted limbs, fingers fused together, static image, cluttered background, three legs, many people in the background, walking backwards, blurry, too dark, too bright, too saturated, too sharp, too soft, too high contrast, too bland, too monotonous, too complex, too simple, too abstract, text, logo, watermark, signature"

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

# ==========================================
# IMAGE WORKFLOW CONFIGURATION
# ==========================================
# Active image workflow to use (must exist in IMAGE_WORKFLOWS)
IMAGE_WORKFLOW = "flux"

# Image workflow definitions
# Each workflow has its own node IDs and workflow file path
# Add new workflows here and set IMAGE_WORKFLOW to the desired key
IMAGE_WORKFLOWS = {
    "flux": {
        "workflow_path": "workflow/image/flux.json",
        "text_node_id": "6",           # CLIPTextEncode node for positive prompt
        "neg_text_node_id": None,      # Flux doesn't use negative prompts
        "ksampler_node_id": "13",      # SamplerCustomAdvanced node
        "vae_node_id": "8",            # VAEDecode node
        "save_node_id": "9",           # SaveImage node
        "description": "Flux model for high-quality image generation"
    },
    "flux2": {
        "workflow_path": "workflow/image/flux2.json",
        "text_node_id": "98:6",
        "neg_text_node_id": None,
        "ksampler_node_id": "98:16",
        "vae_node_id": "98:10",
        "save_node_id": "9",
        "description": "Flux2.Dev for high quality images workflow"
    },
    "sdxl": {
        "workflow_path": "workflow/image/sdxl.json",
        "text_node_id": "6",           # CLIPTextEncode node for positive prompt
        "neg_text_node_id": "7",       # CLIPTextEncode node for negative prompt
        "ksampler_node_id": "13",      # KSampler node
        "vae_node_id": "8",            # VAEDecode node
        "save_node_id": "9",           # SaveImage node
        "description": "SDXL model for image generation"
    },
    "hidream": {
        "workflow_path": "workflow/image/hidream.json",
        "text_node_id": "6",
        "neg_text_node_id": None,
        "ksampler_node_id": "13",
        "vae_node_id": "8",
        "save_node_id": "9",
        "description": "HiDream model for image generation"
    },
    "qwen": {
        "workflow_path": "workflow/image/qwen.json",
        "text_node_id": "6",
        "neg_text_node_id": None,
        "ksampler_node_id": "13",
        "vae_node_id": "8",
        "save_node_id": "9",
        "description": "Qwen model for image generation"
    },
    "default": {
        "workflow_path": "workflow/image/image_generation_workflow.json",
        "text_node_id": "6",
        "neg_text_node_id": None,
        "ksampler_node_id": "13",
        "vae_node_id": "8",
        "save_node_id": "9",
        "description": "Default/fallback image generation workflow"
    }
}

# Legacy single workflow settings (deprecated, use IMAGE_WORKFLOWS instead)
# Kept for backward compatibility
IMAGE_WORKFLOW_PATH = "workflow/image/image_generation_workflow.json"
IMAGE_TEXT_NODE_ID = "6"
IMAGE_NEG_TEXT_NODE_ID = None
IMAGE_KSAMPLER_NODE_ID = "13"
IMAGE_VAE_NODE_ID = "8"
IMAGE_SAVE_NODE_ID = "9"

# ==========================================
# VIDEO GENERATION CONFIGURATION
# ==========================================
# Default video length per shot (in seconds)
DEFAULT_SHOT_LENGTH = 6.0

# Maximum number of shots to generate (for testing)
# Set to 0 for no limit (generates all shots from story)
# Recommended for testing: 3-5 shots
DEFAULT_MAX_SHOTS = 0  # 0 = no limit

# ==========================================
# SHOT PLANNING CONFIGURATION
# ==========================================
# Default number of shots to generate per scene (when no max_shots specified)
DEFAULT_SHOTS_PER_SCENE = 1  # 4 shots x 5 scenes = 20 shots total

# Minimum shots per scene (enforced in planning logic)
MIN_SHOTS_PER_SCENE = 3  # Each scene gets at least 3 shots

# Maximum shots per scene (prevents over-generation for long stories)
MAX_SHOTS_PER_SCENE = 8  # No more than 8 shots per scene

# Video framerate (fps)
VIDEO_FPS = 16

# Target total video length (in seconds)
# Set to None to generate based on story length
# Note: If both DEFAULT_MAX_SHOTS and TARGET_VIDEO_LENGTH are set,
#       max_shots will be calculated as: int(TARGET_VIDEO_LENGTH / DEFAULT_SHOT_LENGTH)
TARGET_VIDEO_LENGTH = 600  # or specify like: 60.0 for 60 seconds

# Video rendering timeout (in seconds)
# Maximum time to wait for a single video render to complete
VIDEO_RENDER_TIMEOUT = 1800  # 30 minutes

# LoRA node IDs in the workflow (for camera-based LoRA loading)
# Array of LoRA node pairs - each pair contains HIGH_NOISE_LORA_NODE_ID and LOW_NOISE_LORA_NODE_ID
# This allows up to 4 different camera types to load their LoRAs simultaneously
LORA_NODES = [
    {"HIGH_NOISE_LORA_NODE_ID": "128", "LOW_NOISE_LORA_NODE_ID": "127"},
    {"HIGH_NOISE_LORA_NODE_ID": "130", "LOW_NOISE_LORA_NODE_ID": "131"},
    {"HIGH_NOISE_LORA_NODE_ID": "132", "LOW_NOISE_LORA_NODE_ID": "133"},
    {"HIGH_NOISE_LORA_NODE_ID": "134", "LOW_NOISE_LORA_NODE_ID": "135"},
]

# Legacy single node IDs (for backward compatibility)
LORA_NODE_ID = "127"
LORA_NODE_ID_2 = "128"

# ==========================================
# CAMERA-TO-LORA MAPPING
# ==========================================
# Map camera types to specific LoRA files and trigger keywords for different motion effects
# Camera types from shots.json will be matched to these LoRAs
# Trigger keywords are appended to motion prompts to activate specific LoRA effects
#
# Each shot can have multiple cameras (e.g., "dolly,pan" or ["pan", "drone"])
# When multiple cameras are present, they are assigned to LORA_NODES pairs sequentially:
# - First camera -> LORA_NODES[0]
# - Second camera -> LORA_NODES[1]
# - Third camera -> LORA_NODES[2]
# - Fourth camera -> LORA_NODES[3]
#
# Each camera type has:
# - high_noise_lora: High noise model for more dynamic motion
# - low_noise_lora: Low noise model for more stable/subtle motion
# - trigger_keyword: Text appended to motion prompt to activate LoRA effects
# - strength_low: LoRA strength for low noise model (0.0 to 1.0), required
# - strength_high: LoRA strength for high noise model (0.0 to 1.0), required
CAMERA_LORA_MAPPING = {
    "slow pan": {
        "high_noise_lora": "",
        "low_noise_lora": "",
        "trigger_keyword": "slow pan",
        "strength_low": 0.0,
        "strength_high": 0.0
    },
    "pan": {
        "high_noise_lora": "",
        "low_noise_lora": "",
        "trigger_keyword": "pan",
        "strength_low": 0.0,
        "strength_high": 0.0
    },
    "static": {
        "high_noise_lora": "",
        "low_noise_lora": "",
        "trigger_keyword": "static shot",
        "strength_low": 0.0,
        "strength_high": 0.0
    },
    "dolly": {
        "high_noise_lora": "dolly-zoom-wan22-high.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "dolly-zoom shot",
        "strength_low": 0.0,
        "strength_high": 1.0
    },
    "orbit": {
        "high_noise_lora": "Surround_Camera_S1440.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "ymq",
        "strength_low": 0.0,
        "strength_high": 1.0
    },
    "zoom": {
        "high_noise_lora": "POV_Parkour_high_noise.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "POV Parkour",
        "strength_low": 0.0,
        "strength_high": 1.0
    },
    "tracking": {
        "high_noise_lora": "",
        "low_noise_lora": "",
        "trigger_keyword": "tracking shot",
        "strength_low": 0.0,
        "strength_high": 0.8
    },
    "drone": {
        "high_noise_lora": "wan22-video8-drone-16-sel-2.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "drone shot",
        "strength_low": 0.0,
        "strength_high": 0.9
    },
    "arc": {
        "high_noise_lora": "wan22-video10-arcshot-16-sel-7-high.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "arc shot",
        "strength_low": 0.0,
        "strength_high": 0.8
    },
    "walk": {
        "high_noise_lora": "Walk01_HighWan2_2.safetensors",
        "low_noise_lora": "Walk01_LowWan2_2.safetensors",
        "trigger_keyword": "walking into the direction of the moving camera",
        "strength_low": 0.0,
        "strength_high": 0.9
    },
    "fpv": {
        "high_noise_lora": "wan2.2extremebodycam_000000300_high_noise.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "the viewer runs trought , the hand shows throught camera",
        "strength_low": 0.0,
        "strength_high": 0.9
    },
    "dronedive": {
        "high_noise_lora": "FPV_drone_dive_high_noise.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "Dr0ne Div3",
        "strength_low": 0.0,
        "strength_high": 1.0
    },
    "bullettime": {
        "high_noise_lora": "wan2.2bullet_time_high_noise.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "BULLETTIME",
        "strength_low": 0.0,
        "strength_high": 0.9
    },
    "default": {
        "high_noise_lora": "",
        "low_noise_lora": "",
        "trigger_keyword": "",
        "strength_low": 0.0,
        "strength_high": 0.8
    }
}


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
# Agent files are stored in agents/{type}/{name}.md
# Available agents depend on files in the agents folder

# Story generation agent (default, dramatic, documentary, time_traveler, netflix_documentary, youtube_documentary)
STORY_AGENT = "youtube_documentary"

# Image prompt agent (default, artistic, time_traveler)
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


# ==========================================
# LOGGING CONFIGURATION
# ==========================================
LOG_DIR = "logs"
CONSOLE_LOG_LEVEL = "INFO"
FILE_LOG_LEVEL = "DEBUG"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5


# ==========================================
# CUSTOM PROMPTS FILE CONFIGURATION
# ==========================================
# Default camera type for prompts without explicit camera specification
DEFAULT_CAMERA_FOR_PROMPTS = "static"

# Default motion prompt for shots without explicit motion
DEFAULT_MOTION_FOR_PROMPTS = "Subtle camera movement, slow and smooth"

# Auto-detect camera from prompt text (enabled by default)
AUTO_DETECT_CAMERA_FROM_PROMPTS = True


# Pre-calculate current dimensions
IMAGE_WIDTH, IMAGE_HEIGHT = calculate_image_dimensions()
