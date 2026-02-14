# AI Video Factory
**Create stunning AI-generated videos from simple text ideas. The AI Video Factory is a complete pipeline that transforms your concepts into cinematic videos with custom imagery, motion, and narration.**
<br><br>
![Create stunning AI-generated videos from simple text ideas. The AI Video Factory is a complete pipeline that transforms your concepts into cinematic videos with custom imagery, motion, and narration](https://repository-images.githubusercontent.com/1152487184/341c4b55-bcdb-4d80-a0e7-9838ed32571f)
## Features

- 🎬 **End-to-End Pipeline**: From idea to final video in 7 automated steps
- 🎨 **Dual Image Generation**: Gemini API or ComfyUI (Flux/SDXL) support
- 🎥 **Advanced Video Generation**: Wan 2.2 model with ComfyUI integration
- 🚁 **Multi-Camera LoRA System**: Combine multiple camera movements (drone, orbit, dolly, zoom, etc.)
- 🎤 **Narration Support**: Optional TTS with multiple voice options
- 💾 **Session Management**: Crash recovery and selective regeneration
- 🔧 **Highly Configurable**: Customize every aspect of generation

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set your Gemini API key
export GEMINI_API_KEY="your_api_key_here"

# Start ComfyUI with Wan 2.2 workflow
# (ComfyUI must be running on http://127.0.0.1:8188)

# Generate a video
python main.py --idea "A beautiful sunset over the ocean"
```

## Requirements

- Python 3.10+
- Gemini API key ([Get one here](https://ai.google.dev/))
- ComfyUI with Wan 2.2 video model
- Optional: ElevenLabs API key for premium TTS

## Documentation

Comprehensive documentation is available in the `docs/` folder:

### Getting Started

| Document | Description |
|----------|-------------|
| [Quick Start](docs/QUICK_START.md) | Get started in 5 minutes |
| [Setup Checklist](docs/SETUP_CHECKLIST.md) | Complete setup guide |
| [ComfyUI Setup](docs/COMFYUI_SETUP_CHECKLIST.md) | ComfyUI installation |
| [Gemini Setup](docs/README_GEMINI_SETUP.md) | Gemini API configuration |

### Configuration

| Document | Description |
|----------|-------------|
| [Configuration Guide](docs/CONFIGURATION.md) | All config.py settings |
| [Camera LoRA Guide](docs/CAMERA_LORA_GUIDE.md) | Multi-camera LoRA system |
| [Image Generation Guide](docs/COMFYUI_IMAGE_GUIDE.md) | ComfyUI image generation |

### Workflow

| Document | Description |
|----------|-------------|
| [Workflow Guide](docs/WORKFLOW_GUIDE.md) | Complete pipeline overview |
| [Session Guide](docs/SESSION_GUIDE.md) | Session management |
| [Video Regeneration](docs/VIDEO_REGENERATION_GUIDE.md) | Regenerate failed shots |

### Reference

| Document | Description |
|----------|-------------|
| [API Reference](docs/API_REFERENCE.md) | Complete API documentation |
| [Features Overview](docs/COMPLETE_FEATURE_OVERVIEW.md) | All features explained |
| [DOCS_INDEX](docs/DOCS_INDEX.md) | Complete documentation index |

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AI VIDEO FACTORY PIPELINE                       │
└─────────────────────────────────────────────────────────────────────┘

Step 1: Idea
   Input: "A beautiful sunset over the ocean"
   ↓
Step 2: Story Generation
   Output: Structured narrative with characters, setting, themes
   ↓
Step 3: Scene Graph
   Output: Visual scene breakdown with locations, characters, elements
   ↓
Step 4: Shot Planning
   Output: Detailed shots with camera movements and prompts
   ↓
Step 4.5: Image Generation
   Output: High-quality images for each shot (Gemini or ComfyUI)
   ↓
Step 5: Video Rendering
   Output: Animated videos using Wan 2.2 with camera LoRAs
   ↓
Step 6: Narration (Optional)
   Output: Voice narration synced to video
```

## Example Usage

### Basic Video Generation

```bash
python main.py --idea "An elderly woman tends her garden at sunset"
```

### With Custom Settings

```bash
python main.py \
  --idea "Epic drone footage of mountain landscapes" \
  --max-shots 10 \
  --shot-length 8 \
  --video-agent cinematic
```

### Enable Narration

```bash
python main.py \
  --idea "A story about friendship" \
  --generate-narration \
  --tts-voice en-US-AriaNeural
```

### Resume from Session

```bash
# View all sessions
python sessions.py --list

# Resume specific session
python main.py --session session_20260210_174844
```

## Multi-Camera System

Combine multiple camera movements for complex shots:

```python
# In shots.json
{
  "shot": 1,
  "camera": "drone, orbit",  # Two cameras combined
  "motion_prompt": "Epic reveal of the castle"
}
```

Supported cameras: `static`, `pan`, `dolly`, `zoom`, `orbit`, `tracking`, `drone`, `arc`, `walk`

See [Camera LoRA Guide](docs/CAMERA_LORA_GUIDE.md) for details.

## Project Structure

```
ai_video_factory/
├── README.md                    # This file
├── config.py                    # Configuration settings
├── main.py                      # Main pipeline entry point
├── regenerate.py                # Regeneration utility
├── sessions.py                  # Session management CLI
│
├── core/                        # Core modules
│   ├── main.py                  # Pipeline orchestration
│   ├── story_engine.py          # Story generation
│   ├── scene_graph.py           # Scene breakdown
│   ├── shot_planner.py          # Shot planning
│   ├── image_generator.py       # Image generation
│   ├── comfy_client.py          # ComfyUI interface
│   ├── prompt_compiler.py       # Workflow compilation
│   ├── session_manager.py       # Session management
│   └── ...
│
├── agents/                      # Prompt templates
│   ├── story/                   # Story generation agents
│   ├── image_prompt/            # Image prompt agents
│   ├── video_motion/            # Video motion agents
│   └── narration/               # Narration agents
│
├── workflow/                    # ComfyUI workflows
│   ├── video/                   # Video generation workflows
│   ├── image/                   # Image generation workflows
│   └── voice/                   # TTS workflows
│
├── docs/                        # Documentation
│   ├── CONFIGURATION.md
│   ├── CAMERA_LORA_GUIDE.md
│   ├── WORKFLOW_GUIDE.md
│   ├── API_REFERENCE.md
│   └── ...
│
├── input/                       # Input files
│   └── story.txt                # Default idea input
│
└── output/                      # Output files
    └── sessions/                # Session folders
        └── session_YYYYMMDD_HHMMSS/
            ├── story.json
            ├── scene_graph.json
            ├── shots.json
            ├── images/
            ├── videos/
            └── narration/
```

## Configuration

Key settings in `config.py`:

```python
# API Keys
GEMINI_API_KEY = "your_api_key"

# Image Generation
IMAGE_GENERATION_MODE = "gemini"  # or "comfyui"
IMAGE_ASPECT_RATIO = "16:9"
IMAGE_RESOLUTION = "1280"
IMAGES_PER_SHOT = 1

# Video Generation
DEFAULT_SHOT_LENGTH = 6.0
VIDEO_FPS = 16
DEFAULT_MAX_SHOTS = 0  # 0 = unlimited

# Camera LoRA System
LORA_NODES = [
    {"HIGH_NOISE_LORA_NODE_ID": "128", "LOW_NOISE_LORA_NODE_ID": "127"},
    # ... up to 4 pairs
]
```

See [Configuration Guide](docs/CONFIGURATION.md) for all settings.

## Session Management

Each video generation creates a session with full tracking:

```bash
# List all sessions
python sessions.py --list

# View session details
python sessions.py --show session_20260210_174844

# Regenerate failed videos
python regenerate.py --session session_20260210_174844 --videos --failed-only

# Regenerate specific shots
python regenerate.py --session session_20260210_174844 --shots 1,3,5
```

## Troubleshooting

### ComfyUI Connection Failed

```
[ERROR] Failed to connect to ComfyUI
```

**Solution:** Ensure ComfyUI is running:
```bash
cd ComfyUI
python main.py --listen 0.0.0.0
```

### Invalid API Key

```
[ERROR] Invalid API key
```

**Solution:** Set your Gemini API key:
```bash
export GEMINI_API_KEY="your_api_key"
```

### Video Rendering Timeout

Increase timeout in `config.py`:
```python
VIDEO_RENDER_TIMEOUT = 3600  # 60 minutes
```

## Contributing

Contributions welcome! Areas for improvement:
- Additional camera LoRAs
- New agent templates
- TTS method integrations
- Performance optimizations

## License

MIT License - see LICENSE file for details

## Acknowledgments

- **Gemini API** - Text and image generation
- **ComfyUI** - Video generation interface
- **Wan 2.2** - Video generation model
- **Edge TTS** - Text-to-speech (local mode)

## Support

- Documentation: See `docs/` folder
- Issues: Check existing issues or create new one
- Community: Share your creations and tips

---

**Made with ❤️ for AI video creators**
