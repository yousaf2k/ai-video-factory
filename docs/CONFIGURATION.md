# Configuration Guide

## Overview

The AI Video Factory is configured through `config.py`, which contains all settings for API keys, model choices, workflow paths, and generation parameters.

## Configuration File Location

```
config.py (root directory)
```

## Configuration Sections

### 1. Gemini API Configuration

```python
# Get your API key from: https://ai.google.dev/
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_api_key_here")

# Text generation model (for story, shots, etc.)
GEMINI_TEXT_MODEL = "gemini-2.0-flash"

# Image generation model (NanoBanana Pro)
GEMINI_IMAGE_MODEL = "gemini-3-pro-image-preview"
```

**Settings:**
- `GEMINI_API_KEY`: Your Google Gemini API key
- `GEMINI_TEXT_MODEL`: Model for text generation (story, scene graph, shots)
- `GEMINI_IMAGE_MODEL`: Model for image generation

### 2. ComfyUI Configuration

```python
# ComfyUI server URL
COMFY_URL = "http://127.0.0.1:8188"

# Path to your Wan 2.2 workflow template
WORKFLOW_PATH = "workflow/video/wan22_workflow.json"

# Node IDs in your workflow
LOAD_IMAGE_NODE_ID = "97"
MOTION_PROMPT_NODE_ID = "93"
WAN_VIDEO_NODE_ID = "98"
```

**Important:** These node IDs must match your actual ComfyUI workflow. To find node IDs:
1. Open your workflow in ComfyUI
2. Right-click on a node → "Node ID for Save"
3. Update the corresponding ID in config.py

### 3. Image Generation Configuration

```python
# Image generation mode: "gemini" or "comfyui"
IMAGE_GENERATION_MODE = "gemini"

# Active image workflow (for ComfyUI mode)
IMAGE_WORKFLOW = "flux"

# Default negative prompt for ComfyUI image generation
DEFAULT_NEGATIVE_PROMPT = "blurry, low quality, distorted, deformed, ..."

# Number of images to generate per shot (with different seeds)
IMAGES_PER_SHOT = 1

# Output directory for generated images
IMAGES_OUTPUT_DIR = "output/generated_images"

# Image aspect ratio (options: "1:1", "16:9", "9:16", "4:3", "3:4")
IMAGE_ASPECT_RATIO = "16:9"

# Image resolution (options: "512", "1024", "1280", "2048")
IMAGE_RESOLUTION = "1280"
```

#### Image Workflows System

The `IMAGE_WORKFLOWS` configuration allows you to define multiple ComfyUI image generation workflows and easily switch between them:

```python
IMAGE_WORKFLOWS = {
    "flux": {
        "workflow_path": "workflow/image/flux.json",
        "text_node_id": "6",
        "neg_text_node_id": None,
        "ksampler_node_id": "13",
        "vae_node_id": "8",
        "save_node_id": "9",
        "description": "Flux model for high-quality image generation"
    },
    "sdxl": {
        "workflow_path": "workflow/image/sdxl.json",
        "text_node_id": "6",
        "neg_text_node_id": "7",
        "ksampler_node_id": "13",
        "vae_node_id": "8",
        "save_node_id": "9",
        "description": "SDXL model for image generation"
    }
}
```

**Workflow Parameters:**
- `workflow_path`: Path to the ComfyUI workflow JSON file
- `text_node_id`: Node ID for positive prompt (CLIPTextEncode)
- `neg_text_node_id`: Node ID for negative prompt (or None if not used)
- `ksampler_node_id`: Node ID for the sampler (KSampler/SamplerCustomAdvanced)
- `vae_node_id`: Node ID for VAE decoder
- `save_node_id`: Node ID for SaveImage node
- `description`: Human-readable description of the workflow

**To switch workflows:**
```python
# In config.py
IMAGE_WORKFLOW = "flux"  # or "sdxl", "flux2", etc.
```

**Adding a new workflow:**
1. Create your ComfyUI workflow and save it to `workflow/image/`
2. Find the node IDs (right-click node → "Node ID for Save")
3. Add entry to `IMAGE_WORKFLOWS` in config.py
4. Set `IMAGE_WORKFLOW` to your new workflow name

**Modes:**
- `gemini`: Use Gemini API for image generation
- `comfyui`: Use ComfyUI with Flux/SDXL models

**Aspect Ratios:**
- `16:9`: Widescreen landscape (1920x1080, 1280x720, etc.)
- `9:16`: Portrait vertical (1080x1920, 720x1280, etc.)
- `1:1`: Square (1024x1024, 512x512, etc.)
- `4:3`: Standard landscape
- `3:4`: Standard portrait

### 4. Video Generation Configuration

```python
# Default video length per shot (in seconds)
DEFAULT_SHOT_LENGTH = 6.0

# Maximum number of shots to generate (for testing)
# Set to 0 for no limit
DEFAULT_MAX_SHOTS = 0

# Video framerate (fps)
VIDEO_FPS = 16

# Target total video length (in seconds)
TARGET_VIDEO_LENGTH = None

# Video rendering timeout (in seconds)
VIDEO_RENDER_TIMEOUT = 1800  # 30 minutes
```

**Settings:**
- `DEFAULT_SHOT_LENGTH`: Length of each video clip in seconds
- `DEFAULT_MAX_SHOTS`: Limit shots for testing (0 = unlimited)
- `VIDEO_FPS`: Frames per second (16 recommended for Wan 2.2)
- `VIDEO_RENDER_TIMEOUT`: Maximum wait time for video rendering

### 5. Camera-to-LoRA Mapping

```python
LORA_NODES = [
    {"HIGH_NOISE_LORA_NODE_ID": "128", "LOW_NOISE_LORA_NODE_ID": "127"},
    {"HIGH_NOISE_LORA_NODE_ID": "130", "LOW_NOISE_LORA_NODE_ID": "131"},
    {"HIGH_NOISE_LORA_NODE_ID": "132", "LOW_NOISE_LORA_NODE_ID": "133"},
    {"HIGH_NOISE_LORA_NODE_ID": "134", "LOW_NOISE_LORA_NODE_ID": "135"},
]

CAMERA_LORA_MAPPING = {
    "drone": {
        "high_noise_lora": "wan22-video8-drone-16-sel-2.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "drone footage aerial",
        "strength_low": 0.7,
        "strength_high": 0.9
    },
    # ... more camera types
}
```

**See Also:** [Camera LoRA Guide](CAMERA_LORA_GUIDE.md)

### 6. Agent Configuration

```python
# Story generation agent
STORY_AGENT = "default"

# Image prompt agent
IMAGE_AGENT = "default"

# Video motion agent
VIDEO_AGENT = "default"

# Narration agent
NARRATION_AGENT = "default"
```

**Agents** are prompt templates stored in `agents/{type}/{name}.txt`

Available agents depend on files in the agents folder.

### 7. Narration/TTS Configuration

```python
# Whether to generate narration for videos
GENERATE_NARRATION = False

# TTS method: "comfyui", "local" (edge-tts), or "elevenlabs"
TTS_METHOD = "local"
```

**TTS Methods:**
- `local`: Edge TTS (free, no API key needed)
- `comfyui`: ComfyUI TTS workflow
- `elevenlabs`: ElevenLabs API (requires API key)

### 8. ElevenLabs Configuration

```python
# Get your API key from: https://elevenlabs.io/app/settings/api-keys
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# Default voice for TTS
TTS_VOICE = "en-US-AriaNeural"

# ElevenLabs model selection
ELEVENLABS_MODEL = "eleven_multilingual_v2"

# ElevenLabs voice settings
ELEVENLABS_STABILITY = 0.5   # 0.0 to 1.0
ELEVENLABS_SIMILARITY = 0.75 # 0.0 to 1.0
```

### 9. Workflow Execution Mode

```python
# Step progression mode: "auto" or "manual"
AUTO_STEP_MODE = True  # True = auto, False = manual
```

- `auto`: Automatically proceed to next step after completion
- `manual`: Stop after each step, require user to continue

## Helper Functions

### calculate_image_dimensions()

Calculates image width and height from aspect ratio and resolution.

```python
def calculate_image_dimensions(aspect_ratio=IMAGE_ASPECT_RATIO, resolution=IMAGE_RESOLUTION):
    """
    Returns: (width, height) as integers
    Dimensions are multiples of 8 (required by most AI models)
    """
```

**Example:**
```python
width, height = calculate_image_dimensions("16:9", "1280")
# Returns: (1280, 720)

width, height = calculate_image_dimensions("9:16", "720")
# Returns: (408, 720)
```

## Environment Variables

Some settings can be overridden with environment variables:

```bash
# Gemini API
export GEMINI_API_KEY="your_api_key"

# ElevenLabs API
export ELEVENLABS_API_KEY="your_api_key"
```

## Common Configuration Tasks

### Change Image Aspect Ratio

```python
# In config.py
IMAGE_ASPECT_RATIO = "9:16"  # Portrait for TikTok/Reels
IMAGE_RESOLUTION = "720"     # Height for portrait
```

### Increase Video Length

```python
# In config.py
DEFAULT_SHOT_LENGTH = 10.0  # 10 seconds per shot
```

### Limit Shots for Testing

```python
# In config.py
DEFAULT_MAX_SHOTS = 3  # Only generate first 3 shots
```

### Switch to ComfyUI Image Generation

```python
# In config.py
IMAGE_GENERATION_MODE = "comfyui"
```

### Enable Narration

```python
# In config.py
GENERATE_NARRATION = True
TTS_METHOD = "local"
TTS_VOICE = "en-US-AriaNeural"
```

## Configuration Validation

The system automatically validates dimensions and prints settings:

```
[INFO] Set video length: 5.0s (80 frames at 16fps)
[INFO] Set dimensions: 1280x720 (16:9 aspect ratio)
```

## Troubleshooting

### Invalid Dimensions

If you see dimension errors, ensure:
1. Aspect ratio uses format "W:H" (e.g., "16:9")
2. Resolution is a string number (e.g., "1280")
3. Calculated dimensions are multiples of 8

### API Key Errors

```
[ERROR] Invalid API key
```

**Solution:** Set environment variable or update in config.py:
```bash
export GEMINI_API_KEY="your_key"
```

### ComfyUI Connection Failed

```
[ERROR] Failed to connect to ComfyUI
```

**Solution:** Ensure ComfyUI is running:
```bash
# Check if ComfyUI is accessible
curl http://127.0.0.1:8188/system_stats
```

## Default Configuration

A complete default configuration is maintained in `config.py`. Create a copy for custom configurations:

```bash
cp config.py config_custom.py
```

Then modify as needed.

## See Also

- [Camera LoRA Guide](CAMERA_LORA_GUIDE.md)
- [Workflow Guide](WORKFLOW_GUIDE.md)
- [Quick Start](QUICK_START.md)
