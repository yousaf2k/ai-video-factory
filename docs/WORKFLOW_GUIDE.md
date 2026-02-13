# Workflow Guide

## Overview

The AI Video Factory follows a structured 7-step pipeline to transform ideas into fully rendered videos with narration. This guide explains each step and how to customize the workflow.

## Pipeline Steps

```
Step 1: Idea
  ↓
Step 2: Story Generation
  ↓
Step 3: Scene Graph
  ↓
Step 4: Shot Planning
  ↓
Step 4.5: Image Generation
  ↓
Step 5: Video Rendering
  ↓
Step 6: Narration (optional)
```

## Step Details

### Step 1: Idea

**Input:** Video idea (text)
**Output:** Raw idea text
**File:** `input/story.txt` or command line argument

The idea is the starting point for your video. It can be:
- A brief concept: "A beautiful sunset over the ocean"
- A detailed description: "An elderly woman named Anna tends her garden at sunset, remembering her late husband through the flowers they planted together"

**How to provide idea:**
```bash
# Command line
python main.py --idea "Your video idea here"

# From file
echo "Your video idea" > input/story.txt
python main.py
```

### Step 2: Story Generation

**Input:** Idea
**Output:** Structured story with character descriptions, setting, and narrative arc
**Module:** `core/story_engine.py`
**Agent:** `agents/story/{STORY_AGENT}.txt`

The story is expanded into a full narrative including:
- **Title**: Video title
- **Logline**: One-sentence summary
- **Characters**: Character descriptions with physical details
- **Setting**: Time, place, atmosphere
- **Story Arc**: Beginning, middle, end structure
- **Themes**: Key themes and motifs

**Output file:** `output/sessions/{session}/story.json`

### Step 3: Scene Graph

**Input:** Story
**Output:** Visual scene breakdown with characters, locations, and visual elements
**Module:** `core/scene_graph.py`
**Agent:** `agents/scene_graph/default.txt`

The scene graph organizes the story into visual scenes:
- **Scene Number**: Sequential scene identifier
- **Location**: Where the scene takes place
- **Characters Present**: Who appears in the scene
- **Key Visual Elements**: Important objects, lighting, mood
- **Time of Day**: Lighting conditions
- **Action Summary**: What happens visually

**Output file:** `output/sessions/{session}/scene_graph.json`

### Step 4: Shot Planning

**Input:** Story + Scene Graph
**Output:** Detailed shot list with camera movements and prompts
**Module:** `core/shot_planner.py`
**Agent:** `agents/shots/{VIDEO_AGENT}.txt`

Shots are planned with complete specifications:
- **Shot Number**: Sequential shot identifier
- **Scene**: Which scene this shot belongs to
- **Image Prompt**: Detailed description for image generation
- **Motion Prompt**: Camera movement and action description
- **Camera**: Camera type(s) for LoRA selection
- **Duration**: Length of shot in seconds

**Camera types include:** static, pan, dolly, zoom, orbit, tracking, drone, arc, walk (and combinations)

**Output file:** `output/sessions/{session}/shots.json`

### Step 4.5: Image Generation

**Input:** Shot list
**Output:** Generated images for each shot
**Module:** `core/image_generator.py`
**Modes:** Gemini API or ComfyUI (Flux/SDXL)

Images are generated from the image prompts:
- **Multiple variations**: Generate multiple images per shot with different seeds
- **Consistent style**: All images use same model and settings
- **Organized output**: Named as `shot_001_001.png`, `shot_001_002.png`, etc.

**Output directory:** `output/sessions/{session}/images/`

**Configuration:**
```python
# In config.py
IMAGE_GENERATION_MODE = "gemini"  # or "comfyui"
IMAGES_PER_SHOT = 1              # Number of variations
IMAGE_ASPECT_RATIO = "16:9"
IMAGE_RESOLUTION = "1280"
```

### Step 5: Video Rendering

**Input:** Generated images + Shot specifications
**Output:** Rendered video clips
**Module:** `core/comfy_client.py`
**Workflow:** ComfyUI Wan 2.2 workflow

Videos are rendered by:
1. Loading each image into ComfyUI
2. Injecting motion prompt (enhanced with camera trigger keywords)
3. Loading camera-specific LoRAs
4. Rendering with Wan 2.2 video model
5. Saving output video

**Output directory:** `output/sessions/{session}/videos/`

**Configuration:**
```python
# In config.py
DEFAULT_SHOT_LENGTH = 6.0      # Seconds per shot
VIDEO_FPS = 16                 # Frames per second
VIDEO_RENDER_TIMEOUT = 1800    # Max wait time (30 min)
```

**Multi-Camera LoRA System:**
- Each shot can have multiple cameras: `"drone, orbit"` or `["dolly", "zoom"]`
- Cameras are assigned sequentially to LORA_NODES pairs
- Trigger keywords are appended to motion prompts

**See:** [Camera LoRA Guide](CAMERA_LORA_GUIDE.md)

### Step 6: Narration (Optional)

**Input:** Story + Shot list
**Output:** Narration audio track
**Module:** `core/narration_generator.py`
**TTS:** Local (Edge TTS), ComfyUI, or ElevenLabs

Narration is generated from the story:
- **Narration script**: Text narration based on story and scenes
- **Voice synthesis**: Convert script to audio using TTS
- **Timing**: Sync narration with video timing

**Output directory:** `output/sessions/{session}/narration/`

**Configuration:**
```python
# In config.py
GENERATE_NARRATION = False
TTS_METHOD = "local"           # "local", "comfyui", or "elevenlabs"
TTS_VOICE = "en-US-AriaNeural"
```

## Session Management

### Session Structure

Each video generation creates a session:

```
output/sessions/session_YYYYMMDD_HHMMSS/
├── story.json
├── scene_graph.json
├── shots.json
├── images/
│   ├── shot_001_001.png
│   ├── shot_002_001.png
│   └── ...
├── videos/
│   ├── shot_001.mp4
│   ├── shot_002.mp4
│   └── ...
├── narration/
│   ├── narration.txt
│   └── narration.mp3
└── session.json
```

### Session Tracking

The `session.json` file tracks progress:

```json
{
  "session_id": "session_20260210_174844",
  "idea": "A beautiful sunset over the ocean",
  "status": "completed",
  "steps_completed": ["story", "scene_graph", "shots", "images", "videos"],
  "total_shots": 5,
  "images_generated": 5,
  "videos_rendered": 5,
  "start_time": "2026-02-10T17:48:44",
  "end_time": "2026-02-10T18:15:30"
}
```

## Execution Modes

### Auto Mode (Default)

Automatically proceeds through all steps:

```python
# In config.py
AUTO_STEP_MODE = True
```

### Manual Mode

Stop after each step for review:

```python
# In config.py
AUTO_STEP_MODE = False
```

Resume from specific step:
```bash
python main.py --session session_20260210_174844 --step 4
```

## Regeneration

Regenerate specific components:

```bash
# Regenerate images only
python regenerate.py --session session_20260210_174844 --images

# Regenerate videos only
python regenerate.py --session session_20260210_174844 --videos

# Regenerate specific shots
python regenerate.py --session session_20260210_174844 --shots 1,2,3
```

## Customization

### Custom Agents

Create custom prompt templates in `agents/`:

```bash
# Create custom story agent
echo "Your custom story prompt..." > agents/story/cinematic.txt

# Use custom agent
python main.py --story-agent cinematic
```

### Custom Workflows

Modify ComfyUI workflows in `workflow/`:

```
workflow/
├── video/
│   └── wan22_workflow.json      # Main video generation
├── image/
│   └── image_generation_workflow.json  # Image generation
└── voice/
    └── tts_workflow.json        # Text-to-speech
```

### Custom Node IDs

Update node IDs in `config.py` to match your workflow:

```python
# After modifying your ComfyUI workflow
LOAD_IMAGE_NODE_ID = "97"     # Update to your LoadImage node ID
MOTION_PROMPT_NODE_ID = "93"  # Update to your CLIPTextEncode node ID
WAN_VIDEO_NODE_ID = "98"      # Update to your WanImageToVideo node ID
```

## Command-Line Options

```bash
# Basic usage
python main.py --idea "Your video idea"

# Specify max shots
python main.py --idea "Your idea" --max-shots 3

# Specify shot length
python main.py --idea "Your idea" --shot-length 10

# Continue from session
python main.py --session session_20260210_174844

# Start from specific step
python main.py --session session_20260210_174844 --step 4

# Use custom agents
python main.py --story-agent dramatic --image-agent artistic

# Enable narration
python main.py --generate-narration --tts-voice en-GB-SoniaNeural
```

## Error Handling

### Crash Recovery

If the pipeline crashes, it can resume:

```bash
# Automatically resume last session
python main.py

# Or specify session
python main.py --session session_20260210_174844
```

### Failed Shots

Failed video renders are tracked and can be regenerated:

```bash
# View failed shots in session summary
python main.py --session session_20260210_174844

# Regenerate failed shots only
python regenerate.py --session session_20260210_174844 --videos --failed-only
```

## Performance Optimization

### Parallel Processing

Images are generated sequentially, but you can adjust:
- `IMAGES_PER_SHOT`: More variations = longer generation time
- `DEFAULT_MAX_SHOTS`: Limit shots for faster testing

### Video Rendering

- Reduce `DEFAULT_SHOT_LENGTH` for faster renders
- Lower resolution: `IMAGE_RESOLUTION = "1024"` instead of `"1280"`
- Use faster FPS: `VIDEO_FPS = 16` (recommended for Wan 2.2)

### API Rate Limits

Gemini API has rate limits. If you hit them:
- Reduce `IMAGES_PER_SHOT`
- Reduce `DEFAULT_MAX_SHOTS`
- Add delays between requests

## Troubleshooting

### Step Fails

Check the error message and:
1. Verify API keys are set correctly
2. Ensure ComfyUI is running (for video rendering)
3. Check file permissions in `output/`
4. Review logs in session directory

### Video Rendering Hangs

If video rendering exceeds timeout:
```python
# Increase timeout in config.py
VIDEO_RENDER_TIMEOUT = 3600  # 60 minutes
```

Check ComfyUI console for errors.

### Image Generation Fails

- Ensure API key is valid: `echo $GEMINI_API_KEY`
- Check internet connection
- Verify `IMAGE_GENERATION_MODE` setting
- Try switching between "gemini" and "comfyui"

## See Also

- [Configuration Guide](CONFIGURATION.md)
- [Camera LoRA Guide](CAMERA_LORA_GUIDE.md)
- [API Reference](API_REFERENCE.md)
- [Quick Start](QUICK_START.md)
