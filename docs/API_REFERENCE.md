# API Reference

## Overview

This document provides detailed API documentation for all modules in the AI Video Factory system.

## Core Modules

### story_engine.py

```python
build_story(idea: str, agent: str = "default") -> dict
```

Builds a complete story from a video idea.

**Parameters:**
- `idea` (str): The video concept or idea
- `agent` (str): Name of the agent template to use (default: "default")

**Returns:**
- `dict`: Story object with keys:
  - `title` (str): Story title
  - `logline` (str): One-sentence summary
  - `characters` (list): List of character descriptions
  - `setting` (dict): Setting details (time, place, atmosphere)
  - `story_arc` (dict): Beginning, middle, end structure
  - `themes` (list): Key themes

**Example:**
```python
from core.story_engine import build_story

story = build_story("A sunset over the ocean")
print(story['title'])  # "Eternal Horizons"
```

---

### scene_graph.py

```python
build_scene_graph(story: dict, agent: str = "default") -> list
```

Creates a visual scene breakdown from the story.

**Parameters:**
- `story` (dict): Story object from `build_story()`
- `agent` (str): Name of the agent template to use

**Returns:**
- `list`: List of scene objects, each with:
  - `scene_number` (int): Sequential scene ID
  - `location` (str): Where the scene takes place
  - `characters_present` (list): Characters in the scene
  - `key_visual_elements` (list): Important visual elements
  - `time_of_day` (str): Lighting conditions
  - `action_summary` (str): What happens visually

**Example:**
```python
from core.scene_graph import build_scene_graph

scenes = build_scene_graph(story)
for scene in scenes:
    print(f"Scene {scene['scene_number']}: {scene['location']}")
```

---

### shot_planner.py

```python
plan_shots(story: dict, scene_graph: list, agent: str = "default") -> list
```

Plans detailed shots with camera movements and prompts.

**Parameters:**
- `story` (dict): Story object
- `scene_graph` (list): Scene graph from `build_scene_graph()`
- `agent` (str): Name of the agent template to use

**Returns:**
- `list`: List of shot objects, each with:
  - `shot` (int): Shot number
  - `scene` (int): Scene number this shot belongs to
  - `image_prompt` (str): Detailed description for image generation
  - `motion_prompt` (str): Camera movement and action
  - `camera` (str): Camera type(s) for LoRA
  - `duration` (float): Length in seconds

**Example:**
```python
from core.shot_planner import plan_shots

shots = plan_shots(story, scenes)
for shot in shots:
    print(f"Shot {shot['shot']}: {shot['camera']}")
```

---

### image_generator.py

```python
generate_image(
    prompt: str,
    output_path: str,
    aspect_ratio: str = None,
    resolution: str = None,
    mode: str = None,
    seed: int = None
) -> str
```

Generate a single image from a prompt.

**Parameters:**
- `prompt` (str): Text description of the image
- `output_path` (str): Full path to save the image
- `aspect_ratio` (str, optional): Override config aspect ratio
- `resolution` (str, optional): Override config resolution
- `mode` (str, optional): "gemini" or "comfyui" (None uses config)
- `seed` (int, optional): Random seed for reproducibility

**Returns:**
- `str`: Path to generated image, or None if failed

**Example:**
```python
from core.image_generator import generate_image

image_path = generate_image(
    prompt="A sunset over the ocean",
    output_path="output/sunset.png",
    aspect_ratio="16:9",
    resolution="1280"
)
```

---

```python
generate_image_variations(
    prompt: str,
    output_dir: str,
    count: int = 1,
    mode: str = None,
    negative_prompt: str = "",
    shot_idx: int = 1
) -> list
```

Generate multiple image variations with different seeds.

**Parameters:**
- `prompt` (str): Text description
- `output_dir` (str): Directory to save images
- `count` (int): Number of variations to generate
- `mode` (str): "gemini" or "comfyui"
- `negative_prompt` (str): Negative prompt for ComfyUI
- `shot_idx` (int): Shot index for naming

**Returns:**
- `list`: List of generated image paths

**Example:**
```python
from core.image_generator import generate_image_variations

paths = generate_image_variations(
    prompt="A sunset over the ocean",
    output_dir="output/images",
    count=3,
    shot_idx=1
)
# Returns: ["shot_001_001.png", "shot_001_002.png", "shot_001_003.png"]
```

---

```python
generate_images_for_shots(
    shots: list,
    output_dir: str,
    mode: str = None,
    negative_prompt: str = "",
    images_per_shot: int = 1
) -> list
```

Generate images for all shots in the list.

**Parameters:**
- `shots` (list): List of shot dictionaries with 'image_prompt'
- `output_dir` (str): Directory to save images
- `mode` (str): "gemini" or "comfyui"
- `negative_prompt` (str): Negative prompt for ComfyUI
- `images_per_shot` (int): Number of variations per shot

**Returns:**
- `list`: Updated shots list with 'image_paths' field added

**Example:**
```python
from core.image_generator import generate_images_for_shots

shots = generate_images_for_shots(
    shots=shots,
    output_dir="output/session/images",
    images_per_shot=2
)
```

---

### prompt_compiler.py

```python
load_workflow(path: str, video_length_seconds: float = None) -> dict
```

Load ComfyUI workflow from JSON file and optionally set video length.

**Parameters:**
- `path` (str): Path to workflow JSON file
- `video_length_seconds` (float, optional): Video length in seconds

**Returns:**
- `dict`: Workflow in ComfyUI API format

**Example:**
```python
from core.prompt_compiler import load_workflow

workflow = load_workflow("workflow/video/wan22_workflow.json", video_length_seconds=5.0)
```

---

```python
compile_workflow(
    template: dict,
    shot: dict,
    video_length_seconds: float = None
) -> dict
```

Compile workflow with shot-specific parameters (LoRAs, prompts, image).

**Parameters:**
- `template` (dict): Base workflow template
- `shot` (dict): Shot object with:
  - `image_path` (str): Path to input image
  - `camera` (str): Camera type(s) for LoRA loading
  - `motion_prompt` (str): Motion description
- `video_length_seconds` (float, optional): Override shot duration

**Returns:**
- `dict`: Compiled workflow ready for ComfyUI

**Multi-Camera Support:**
- Single camera: `"drone"`
- Multiple cameras: `"drone, orbit"` or `["dolly", "zoom"]`
- Sequential assignment to LORA_NODES pairs

**Example:**
```python
from core.prompt_compiler import compile_workflow

compiled = compile_workflow(
    template=workflow,
    shot={
        "image_path": "output/shot_001.png",
        "camera": "drone, orbit",
        "motion_prompt": "Flying over mountains"
    },
    video_length_seconds=6.0
)
```

---

### comfy_client.py

```python
submit(workflow: dict, filename: str = None) -> str
```

Submit workflow to ComfyUI for execution.

**Parameters:**
- `workflow` (dict): ComfyUI workflow in API format
- `filename` (str, optional): Custom filename for output

**Returns:**
- `str`: Prompt ID (for tracking)

**Example:**
```python
from core.comfy_client import submit

prompt_id = submit(compiled_workflow, filename="my_video")
```

---

```python
wait_for_prompt_completion(
    prompt_id: str,
    timeout: int = 1800,
    check_interval: float = 0.5
) -> dict
```

Wait for ComfyUI to finish rendering and retrieve output.

**Parameters:**
- `prompt_id` (str): Prompt ID from `submit()`
- `timeout` (int): Maximum wait time in seconds
- `check_interval` (float): Polling interval in seconds

**Returns:**
- `dict`: Result with keys:
  - `success` (bool): Whether rendering succeeded
  - `outputs` (list): List of output file paths
  - `error` (str): Error message if failed

**Example:**
```python
from core.comfy_client import wait_for_prompt_completion

result = wait_for_prompt_completion(prompt_id, timeout=1800)
if result['success']:
    print(f"Video saved: {result['outputs'][0]}")
```

---

```python
get_video_path(prompt_id: str) -> str
```

Get the output video file path for a prompt.

**Parameters:**
- `prompt_id` (str): Prompt ID from `submit()`

**Returns:**
- `str`: Path to video file, or None if not found

**Example:**
```python
from core.comfy_client import get_video_path

video_path = get_video_path(prompt_id)
```

---

### session_manager.py

```python
class SessionManager:
    def __init__(self, base_dir: str = "output/sessions")
    def create_session(self, idea: str) -> str
    def save_step(self, session_id: str, step: str, data: dict)
    def load_step(self, session_id: str, step: str) -> dict
    def update_status(self, session_id: str, status: str)
    def get_session_info(self, session_id: str) -> dict
    def list_sessions(self) -> list
```

Manages session creation, storage, and retrieval.

**Methods:**

**`create_session(idea: str) -> str`**
- Creates a new session
- Returns session ID

**`save_step(session_id: str, step: str, data: dict)`**
- Saves step data to session
- Steps: "story", "scene_graph", "shots", "images", "videos"

**`load_step(session_id: str, step: str) -> dict`**
- Loads step data from session

**`update_status(session_id: str, status: str)`**
- Updates session status
- Statuses: "in_progress", "completed", "failed"

**`get_session_info(session_id: str) -> dict`**
- Returns complete session information

**`list_sessions() -> list`**
- Lists all sessions

**Example:**
```python
from core.session_manager import SessionManager

sm = SessionManager()
session_id = sm.create_session("A sunset over the ocean")
sm.save_step(session_id, "story", story_data)
info = sm.get_session_info(session_id)
```

---

### narration_generator.py

```python
generate_narration(story: dict, shots: list, agent: str = "default") -> dict
```

Generate narration script from story and shots.

**Parameters:**
- `story` (dict): Story object
- `shots` (list): List of shot objects
- `agent` (str): Agent template to use

**Returns:**
- `dict`: Narration object with:
  - `script` (str): Full narration text
  - `segments` (list): Per-shot narration segments

---

```python
generate_narration_audio(
    narration: dict,
    output_path: str,
    method: str = "local",
    voice: str = None
) -> str
```

Convert narration script to audio using TTS.

**Parameters:**
- `narration` (dict): Narration object
- `output_path` (str): Path to save audio
- `method` (str): "local", "comfyui", or "elevenlabs"
- `voice` (str): Voice name or ID

**Returns:**
- `str`: Path to generated audio file

---

### video_regenerator.py

```python
regenerate_videos(
    session_id: str,
    shot_numbers: list = None,
    failed_only: bool = False
) -> dict
```

Regenerate videos for a session.

**Parameters:**
- `session_id` (str): Session to regenerate
- `shot_numbers` (list, optional): Specific shots to regenerate
- `failed_only` (bool): Only regenerate failed videos

**Returns:**
- `dict`: Regeneration results

---

```python
regenerate_images(
    session_id: str,
    shot_numbers: list = None,
    failed_only: bool = False
) -> dict
```

Regenerate images for a session.

**Parameters:**
- `session_id` (str): Session to regenerate
- `shot_numbers` (list, optional): Specific shots to regenerate
- `failed_only` (bool): Only regenerate failed images

**Returns:**
- `dict`: Regeneration results

---

## Configuration Module

All configuration is centralized in `config.py`:

```python
import config

# API Configuration
api_key = config.GEMINI_API_KEY
model = config.GEMINI_TEXT_MODEL

# ComfyUI Configuration
comfy_url = config.COMFY_URL
workflow_path = config.WORKFLOW_PATH

# Image Generation
mode = config.IMAGE_GENERATION_MODE
aspect_ratio = config.IMAGE_ASPECT_RATIO
resolution = config.IMAGE_RESOLUTION

# Video Generation
shot_length = config.DEFAULT_SHOT_LENGTH
fps = config.VIDEO_FPS

# Camera LoRA System
lora_nodes = config.LORA_NODES
camera_mapping = config.CAMERA_LORA_MAPPING

# Dimensions
width, height = config.calculate_image_dimensions("16:9", "1280")
```

---

## Helper Functions

### Main Pipeline Functions

```python
def enhance_motion_prompts_with_triggers(shots: list) -> list
```

Append camera trigger keywords to motion prompts.

**Parameters:**
- `shots` (list): List of shot objects

**Returns:**
- `list`: Updated shots with enhanced motion prompts

---

```python
def get_idea(args: argparse.Namespace) -> str
```

Get video idea from command line or file.

**Parameters:**
- `args`: Parsed command-line arguments

**Returns:**
- `str`: Video idea

---

## Command-Line Interface

```bash
python main.py [OPTIONS]
```

**Options:**
- `--idea TEXT`: Video idea
- `--session TEXT`: Resume from session
- `--step N`: Start from step (2-7)
- `--max-shots N`: Limit number of shots
- `--shot-length SECONDS`: Video length per shot
- `--story-agent NAME`: Story agent template
- `--image-agent NAME`: Image prompt agent
- `--video-agent NAME`: Video motion agent
- `--generate-narration`: Enable narration
- `--tts-method METHOD`: TTS method (local/comfyui/elevenlabs)
- `--tts-voice VOICE`: TTS voice name

**Example:**
```bash
python main.py \
  --idea "A sunset over the ocean" \
  --max-shots 5 \
  --shot-length 6 \
  --video-agent cinematic \
  --generate-narration \
  --tts-voice en-US-AriaNeural
```

---

## Error Handling

Most functions return `None` or an error dict on failure:

```python
result = wait_for_prompt_completion(prompt_id)
if not result['success']:
    print(f"Error: {result['error']}")

image_path = generate_image(prompt, output_path)
if image_path is None:
    print("Image generation failed")
```

---

## Type Hints

The codebase uses Python type hints. Key types:

```python
from typing import Dict, List, Optional, Union

Shot = Dict[str, Any]
Story = Dict[str, Any]
SceneGraph = List[Dict[str, Any]]
SessionID = str
PromptID = str
```

---

## See Also

- [Configuration Guide](CONFIGURATION.md)
- [Camera LoRA Guide](CAMERA_LORA_GUIDE.md)
- [Workflow Guide](WORKFLOW_GUIDE.md)
