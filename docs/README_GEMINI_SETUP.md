# AI Film Studio - Gemini Integration Setup Guide

## Overview

This system has been upgraded to use Google Gemini for both text generation and image generation. Images are pre-generated using Gemini NanoBanana Pro, then passed to ComfyUI's Wan 2.2 workflow for video generation.

## Setup Steps

### 1. Install Dependencies

```bash
cd C:\AI\ai_video_factory
pip install -r requirements.txt
```

### 2. Get Gemini API Key

1. Go to https://ai.google.dev/
2. Sign in with your Google account
3. Click "Get API Key"
4. Copy your API key

### 3. Configure System

Edit `config.py` and update the following:

```python
# REQUIRED - Your Gemini API key
GEMINI_API_KEY = "your-actual-api-key-here"

# OPTIONAL - Adjust these based on your ComfyUI workflow
LOAD_IMAGE_NODE_ID = "10"  # IMPORTANT: Open your workflow in ComfyUI,
                            # right-click the LoadImage node → "Node ID for Save"
                            # Update this with the actual ID

MOTION_PROMPT_NODE_ID = "7"  # Verify this matches your workflow

WORKFLOW_PATH = "workflow/wan22_workflow.json"  # Path to your Wan 2.2 template
```

### 4. Verify Your ComfyUI Workflow

1. Open ComfyUI
2. Load your Wan 2.2 workflow template
3. **Find the LoadImage node** (this will receive your pre-generated images)
4. Right-click the LoadImage node → "Node ID for Save"
5. Update `LOAD_IMAGE_NODE_ID` in `config.py` with this value
6. **Find the KSampler/CLIPTextEncode node** that receives motion_prompt
7. Right-click it → "Node ID for Save"
8. Update `MOTION_PROMPT_NODE_ID` in `config.py` with this value

### 5. Test Gemini Connectivity

```bash
python -c "from core.gemini_engine import ask; print(ask('Test connection'))"
```

### 6. Test Image Generation

```bash
python -c "from core.image_generator import generate_image; generate_image('A beautiful sunset', 'test_output.png')"
```

## Pipeline Flow

1. **STEP 1: Idea** - Read from `input/video_idea.txt`
2. **STEP 2: Story** - Generate narrative via Gemini (`gemini-2.0-flash-exp`)
3. **STEP 3: Scene Graph** - Structure into scenes
4. **STEP 4: Shot Planning** - Create prompts via Gemini (JSON format)
5. **STEP 4.5: Image Generation** - Generate images via Gemini (`gemini-2.0-flash-exp-image-generation`)
6. **STEP 5: Rendering** - Compile workflow with image paths, submit to ComfyUI
7. **Monitor** - Wait for completion

## Directory Structure

```
C:\AI\ai_video_factory\
├── config.py                    # Configuration (API keys, node IDs)
├── requirements.txt             # Python dependencies
├── core\
│   ├── main.py                 # Main pipeline (includes STEP 4.5)
│   ├── gemini_engine.py        # Gemini text generation
│   ├── image_generator.py      # Gemini image generation
│   ├── story_engine.py         # Story generation (uses Gemini)
│   ├── scene_graph.py          # Scene structuring
│   ├── shot_planner.py         # Shot planning with JSON output
│   ├── prompt_compiler.py      # Injects image paths to LoadImage node
│   ├── comfy_client.py         # Submits workflows to ComfyUI
│   ├── render_monitor.py       # Monitors rendering progress
│   └── llm_engine.py           # BACKUP (OpenAI - not used)
├── workflow\
│   └── wan22_workflow.json     # Your Wan 2.2 template
├── input\
│   └── video_idea.txt          # Your video idea
└── output\
    └── generated_images\       # Generated images stored here
        └── session_YYYYMMDD_HHMMSS\
            ├── shot_001.png
            ├── shot_002.png
            └── ...
```

## Configuration Options

### Image Generation

Edit these in `config.py`:

```python
IMAGE_ASPECT_RATIO = "16:9"  # Options: "1:1", "16:9", "9:16", "4:3", "3:4"
IMAGE_RESOLUTION = "1024"    # Options: "512", "1024", "2048"
```

### Text Generation

```python
GEMINI_TEXT_MODEL = "gemini-2.0-flash-exp"  # Fast text generation
```

### Image Generation

```python
GEMINI_IMAGE_MODEL = "gemini-2.0-flash-exp-image-generation"  # NanoBanana Pro
```

## Running the System

1. Add your video idea to `input/video_idea.txt`
2. Ensure ComfyUI is running (`http://127.0.0.1:8188`)
3. Run the pipeline:

```bash
python core/main.py
```

## Troubleshooting

### "No images were successfully generated"

- Check your `GEMINI_API_KEY` is correct
- Verify you have API credits/quota
- Check internet connection

### "LoadImage node not found"

- Open your workflow in ComfyUI
- Right-click LoadImage node → "Node ID for Save"
- Update `LOAD_IMAGE_NODE_ID` in `config.py`

### Images not appearing in workflow

- Verify the node ID matches exactly (as a string: "10" not 10)
- Check ComfyUI console for errors
- Ensure image paths are correct

### Cost

Approximately **$0.08 per image** at 2K resolution via Gemini NanoBanana Pro.

## API References

- [Gemini Text Generation](https://ai.google.dev/gemini-api/docs/text-generation)
- [Gemini Image Generation](https://ai.google.dev/gemini-api/docs/image-generation)

## Migration Notes

- **Old**: OpenAI for text → ComfyUI for image+video
- **New**: Gemini for text → Gemini for images → ComfyUI for video only

The `llm_engine.py` file is kept as backup but is no longer used.
