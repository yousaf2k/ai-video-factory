# AI Film Studio - Workflow Architecture

## System Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AI FILM STUDIO SYSTEM                        │
│                     Gemini Integration v2.0                         │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│   INPUT          │
│  video_idea.txt  │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: READ IDEA                                                │
│   - Read video idea from input file                              │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: STORY GENERATION                                        │
│   Module: story_engine.py                                       │
│   Engine: gemini_engine.py                                      │
│   Model: gemini-2.0-flash-exp                                   │
│   Output: JSON with title, style, scenes                        │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: SCENE GRAPH                                             │
│   Module: scene_graph.py                                        │
│   Action: Structure story into scenes                           │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: SHOT PLANNING                                           │
│   Module: shot_planner.py                                       │
│   Engine: gemini_engine.py (JSON mode)                          │
│   Model: gemini-2.0-flash-exp                                   │
│   Output: List of shots with image_prompt, motion_prompt        │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4.5: IMAGE GENERATION (NEW!)                               │
│   Module: image_generator.py                                    │
│   Engine: Gemini Image Generation                               │
│   Model: gemini-2.0-flash-exp-image-generation                  │
│   Action: Generate image for each shot                          │
│   Output: {                                                     │
│     session_20250207_143000/                                    │
│       ├─ shot_001.png                                           │
│       ├─ shot_002.png                                           │
│       └─ ...                                                    │
│   }                                                             │
│   Result: Add 'image_path' to each shot                         │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: RENDERING                                               │
│   Module: prompt_compiler.py + comfy_client.py                  │
│   Action: For each shot with valid image_path:                  │
│                                                                  │
│   1. Load workflow template (wan22_workflow.json)               │
│   2. Compile workflow:                                          │
│      - Inject image_path → LoadImage node (ID: 10)              │
│      - Inject motion_prompt → Motion node (ID: 7)               │
│   3. Submit to ComfyUI server                                   │
│                                                                  │
│   ComfyUI Workflow:                                             │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│   │  LoadImage   │────▶│   Wan 2.2    │────▶│   Save Video │   │
│   │  (Node 10)   │     │   Generator  │     │   Output     │   │
│   └──────────────┘     └──────────────┘     └──────────────┘   │
│          ▲                                             │        │
│          │ image_path                                   │        │
│          └─────────────────────────────────────────────┘        │
│                              video file                          │
└────────┬────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ MONITOR                                                          │
│   Module: render_monitor.py                                     │
│   Action: Wait for all renders to complete                      │
│   Output: "ALL RENDERS COMPLETE"                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Example

### Input
```
video_idea.txt:
"A peaceful forest with sunlight streaming through trees"
```

### Step 2: Story (Gemini Text)
```json
{
  "title": "Forest Serenity",
  "style": "cinematic nature documentary",
  "scenes": [
    {
      "location": "ancient forest",
      "characters": "none",
      "action": "sunlight piercing through canopy",
      "emotion": "peaceful"
    }
  ]
}
```

### Step 4: Shots (Gemini Text + JSON)
```json
[
  {
    "image_prompt": "Ancient forest with tall trees, sunlight beams streaming through green canopy, moss covered ground, cinematic lighting, 8k ultra detailed",
    "motion_prompt": "slow gentle camera pan from left to right, dolly movement forward",
    "camera": "slow pan"
  }
]
```

### Step 4.5: Images (Gemini Image)
```
output/generated_images/session_20250207_143000/
└── shot_001.png
    (Actual image file generated by Gemini)
```

### Step 5: ComfyUI Workflow Injection
```json
{
  "10": {
    "class_type": "LoadImage",
    "inputs": {
      "image": "output/generated_images/session_20250207_143000/shot_001.png"
    }
  },
  "7": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "text": "slow gentle camera pan from left to right, dolly movement forward"
    }
  }
}
```

### Output
```
ComfyUI/output/
└── forest_serenity_00001.mp4
    (Animated video using the pre-generated image)
```

---

## Component Interaction

```
┌─────────────────────────────────────────────────────────────┐
│                    GEMINI API                                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  gemini-2.0-flash-exp (Text)                                │
│    ├─ story_engine.py ─────────────────┐                    │
│    └─ shot_planner.py ─────────────────┤                    │
│                                          │                    │
│  gemini-2.0-flash-exp-image-generation  │                    │
│    └─ image_generator.py ───────────────┤                    │
│                                          │                    │
└──────────────────────────────────────────┼──────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL SYSTEM                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  main.py (Pipeline Orchestrator)                            │
│    ├─ Calls story_engine                                    │
│    ├─ Calls scene_graph                                     │
│    ├─ Calls shot_planner                                    │
│    ├─ Calls image_generator ◄───────┐                       │
│    └─ Calls prompt_compiler         │                       │
│                                    │                        │
│  prompt_compiler.py                │                        │
│    └─ Injects image_path ──────────┘                       │
│         into workflow                                       │
│                                    │                        │
│  comfy_client.py                   │                        │
│    └─ Submits to ComfyUI ──────────┘                       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    COMFYUI SERVER                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  LoadImage Node                                              │
│    └─ Reads: output/generated_images/session_XXX/shot_001   │
│         │                                                     │
│         ▼                                                     │
│  Wan 2.2 Video Generator                                    │
│    ├─ Input: Pre-generated image                            │
│    ├─ Input: Motion prompt                                  │
│    └─ Output: Animated video                                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Differences from Old System

### OLD (OpenAI + ComfyUI)
```
Idea → OpenAI (text) → ComfyUI (image + video)
                    ↑
                Text prompt only
```

### NEW (Gemini + ComfyUI)
```
Idea → Gemini (text) → Gemini (images) → ComfyUI (video only)
                                      ↑
                               Pre-generated images
```

### Benefits
1. **Better Quality**: Gemini's specialized image model
2. **Faster**: Parallel image generation
3. **More Control**: Pre-generate and review images
4. **Cost Effective**: ~$0.08 per image vs ComfyUI compute costs
5. **Reliable**: Can retry failed images without re-rendering video

---

## Configuration Mapping

```
config.py Settings                → Used By
─────────────────────────────────────────────────
GEMINI_API_KEY                   → gemini_engine.py
GEMINI_TEXT_MODEL                → gemini_engine.py
GEMINI_IMAGE_MODEL               → image_generator.py
COMFY_URL                        → comfy_client.py
WORKFLOW_PATH                    → main.py
LOAD_IMAGE_NODE_ID               → prompt_compiler.py
MOTION_PROMPT_NODE_ID            → prompt_compiler.py
IMAGES_OUTPUT_DIR                → image_generator.py
IMAGE_ASPECT_RATIO               → image_generator.py
IMAGE_RESOLUTION                 → image_generator.py
```

---

## Error Handling Flow

```
Image Generation
    │
    ├─ SUCCESS → Add image_path → Valid shots → Render
    │
    └─ FAILURE → Add image_path = None → Skip shot
                                        │
                                        ▼
                                Filter valid_shots
                                        │
                                        ▼
                                Render only valid shots
                                        │
                                        ├─ 0 valid shots → ERROR → Stop
                                        └─ 1+ valid shots → Continue
```

This ensures graceful degradation - if some images fail, the system continues with those that succeeded.
