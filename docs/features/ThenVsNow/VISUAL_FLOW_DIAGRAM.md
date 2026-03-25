# Complete Visual Flow: Reference Images & Scene Backgrounds

This document shows the complete data flow from UI upload to final image generation.

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────┐         ┌──────────────────────┐      │
│  │ CharacterReference  │         │ SceneBackground      │      │
│  │ Upload Component    │         │ Manager Component    │      │
│  └─────────┬────────────┘         └─────────┬────────────┘      │
│            │                               │                     │
│            │ Upload POST                  │ Upload POST         │
│            │ Generate POST                │                     │
└────────────┼───────────────────────────────┼─────────────────────┘
             │                               │
             ↓                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                       API LAYER (FastAPI)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  POST /characters/{index}/upload-reference?variant={then|now}  │
│  ├─ Validate file type                                           │
│  ├─ Save to project/references/                                  │
│  ├─ Update story.json with path                                  │
│  └─ Broadcast WebSocket update                                   │
│                                                                   │
│  POST /scenes/{id}/upload-background                             │
│  ├─ Validate file type                                           │
│  ├─ Save to project/backgrounds/                                 │
│  ├─ Update scene with path                                       │
│  └─ Broadcast WebSocket update                                   │
│                                                                   │
│  POST /scenes/{id}/generate-background                           │
│  ├─ Queue background generation task                            │
│  └─ Return immediately (async)                                   │
└────────────┬───────────────────────────────┬─────────────────────┘
             │                               │
             │                               │ Generation Request
             ↓                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                  GENERATION SERVICE (Async)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  generate_scene_background()                                     │
│  ├─ Load scene.set_prompt                                        │
│  ├─ Generate using Flux workflow                                 │
│  ├─ Save to project/backgrounds/                                 │
│  ├─ Update story.json                                            │
│  └─ Broadcast progress via WebSocket                             │
│                                                                   │
│  _regenerate_flfi2v_images()                                     │
│  ├─ Get character references from story                          │
│  ├─ Select workflow:                                             │
│  │   ├─ Has THEN reference? → flux_ipadapter_then               │
│  │   ├─ Has NOW reference? → flux_ipadapter_now                 │
│  │   └─ No references? → flux (standard)                        │
│  ├─ Generate THEN/NOW images                                    │
│  └─ Broadcast progress via WebSocket                             │
└────────────┬───────────────────────────────┬─────────────────────┘
             │                               │
             ↓                               ↓
┌─────────────────────────────────────────────────────────────────┐
│              COMFYUI IMAGE GENERATOR (Core)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  generate_image_comfyui(                                         │
│    prompt, output_path,                                          │
│    reference_image_path  ← Key new parameter!                   │
│  )                                                                │
│  ├─ Load workflow from config                                    │
│  ├─ Inject reference into LoadImage node (ID: 1)                │
│  ├─ Inject prompt into CLIPTextEncode node (ID: 6)              │
│  ├─ Set dimensions in EmptyFlux2LatentImage (ID: 10)           │
│  ├─ Submit to ComfyUI                                            │
│  ├─ Wait for completion with progress callback                  │
│  └─ Retrieve and save image                                      │
│                                                                   │
└────────────┬───────────────────────────────┬─────────────────────┘
             │                               │
             ↓                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                    COMFYUI (External Process)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Workflow: flux_ipadapter_then/now                               │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐            │
│  │ LoadImage  │───→│ IPAdapter  │───→│ Sampler    │            │
│  │ (Ref Photo)│    │ (weight:0.7)│    │ (20 steps) │            │
│  └────────────┘    └────────────┘    └──────┬─────┘            │
│                                              │                   │
│                                         ┌────↓─────┐            │
│                                         │ VAEDecode│            │
│                                         └────┬─────┘            │
│                                              │                   │
│                                         ┌────↓─────┐            │
│                                         │ SaveImage│            │
│                                         └──────────┘            │
│                                                                   │
└────────────┬───────────────────────────────┬─────────────────────┘
             │                               │
             ↓                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                      FILE SYSTEM                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  project/{project_id}/                                            │
│  ├── references/                                                 │
│  │   ├── {uuid}_then_ref.png           ← THEN reference          │
│  │   └── {uuid}_now_ref.png            ← NOW reference           │
│  ├── backgrounds/                                                 │
│  │   └── scene_{id}_background_001.png  ← Generated/uploaded     │
│  └── images/                                                      │
│      ├── shot_{idx}_then_{ver}.png      ← Generated THEN         │
│      └── shot_{idx}_now_{ver}.png       ← Generated NOW          │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Detailed Flow: Character Reference Upload

```
User Action:
  1. Drag & drop photo onto CharacterReferenceUpload component
  2. Select variant: "then" or "now"

Frontend:
  1. Create FormData with file
  2. POST to /api/projects/{id}/story/characters/{index}/upload-reference?variant={then|now}

Backend API:
  1. Validate file is image
  2. Generate unique filename: {uuid}_then_ref.png
  3. Save to: output/projects/{id}/references/{filename}
  4. Load story.json
  5. Update character[{index}].{then|now}_reference_image_path = relative_path
  6. Save story.json
  7. Broadcast WebSocket: {type: "story_updated", story: {...}}

Frontend UI:
  1. Receive WebSocket update
  2. Refresh story data
  3. Display preview image

Next Generation:
  1. User clicks "Generate" on shot
  2. Backend loads story.json
  3. Detects character[{character_id}].then_reference_image_path exists
  4. Auto-selects flux_ipadapter_then workflow
  5. Passes reference_image_path to generate_image_comfyui()
  6. ComfyUI injects reference into LoadImage node
  7. IP-Adapter ensures facial consistency
```

## Detailed Flow: Background Generation

```
User Action:
  1. Click "Generate AI" button in SceneBackgroundManager
  2. Component checks scene.set_prompt exists

Backend API:
  1. POST to /api/projects/{id}/story/scenes/{scene_id}/generate-background
  2. Create async task: generate_scene_background()

Generation Service (Async):
  1. Load scene.set_prompt
  2. Broadcast progress 0%
  3. Call generate_image_comfyui() with:
     - prompt: scene.set_prompt
     - workflow: flux_background (no IP-Adapter)
     - output: project/backgrounds/scene_{id}_background_001.png
  4. Progress callbacks broadcast to WebSocket
  5. On complete:
     a. Save image path as relative
     b. Update scene.background_image_path
     c. Update scene.background_generated = true
     d. Update scene.background_is_generated = true
     e. Save story.json
     f. Broadcast completion

Frontend UI:
  1. Receive progress updates via WebSocket
  2. Update progress bar
  3. On completion: Refresh scene data
  4. Display preview with "AI Generated" badge
```

## Workflow Selection Logic

```
_regenerate_flfi2v_images() logic:

FOR each shot to generate:
  ├─ Get character_id from shot
  ├─ Find character in story.characters
  ├─ Check character.{then|now}_reference_image_path
  │
  ├─ GENERATE THEN:
  │   ├─ if character.then_reference_image_path exists:
  │   │   ├─ workflow = "flux_ipadapter_then"
  │   │   ├─ reference = character.then_reference_image_path
  │   │   └─ logger.info("Using IP-Adapter for THEN")
  │   └─ else:
  │       ├─ workflow = "flux" (standard)
  │       ├─ reference = None
  │       └─ logger.info("No THEN reference, using standard Flux")
  │
  └─ GENERATE NOW:
      ├─ if character.now_reference_image_path exists:
      │   ├─ workflow = "flux_ipadapter_now"
      │   ├─ reference = character.now_reference_image_path
      │   └─ logger.info("Using IP-Adapter for NOW")
      └─ else:
          ├─ workflow = "flux" (standard)
          ├─ reference = None
          └─ logger.info("No NOW reference, using standard Flux")
```

## Data Flow Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                     STORY.JSON STRUCTURE                       │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  {                                                              │
│    "characters": [                                             │
│      {                                                          │
│        "name": "Actor Name",                                   │
│        "scene_id": 0,                                          │
│        "then_prompt": "...",                                   │
│        "now_prompt": "...",                                    │
│        "then_reference_image_path": "output/projects/.../then_ref.png",  ← NEW
│        "now_reference_image_path": "output/projects/.../now_ref.png"   ← NEW
│      }                                                          │
│    ],                                                           │
│    "scenes": [                                                 │
│      {                                                          │
│        "scene_id": 0,                                          │
│        "set_prompt": "movie set background...",                │
│        "background_image_path": "output/projects/.../background.png", ← NEW
│        "background_generated": true,                            ← NEW
│        "background_is_generated": true                         ← NEW
│      }                                                          │
│    ]                                                            │
│  }                                                              │
│                                                                │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│                   IMAGE GENERATION REQUEST                      │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  generate_image_comfyui(                                       │
│    prompt = "young version, 20 years ago, actor description",  │
│    output_path = "project/images/shot_001_then_001.png",        │
│    reference_image_path = "output/projects/.../then_ref.png"   ← KEY!
│  )                                                              │
│                                                                │
│  ↓                                                              │
│                                                                │
│  Workflow: flux_ipadapter_then                                 │
│  {                                                              │
│    "1": {  ← LoadImage                                         │
│      "inputs": {                                              │
│        "image": "output/projects/.../then_ref.png"  ← Injected! │
│      }                                                         │
│    },                                                          │
│    "5": {  ← IPAdapter                                        │
│      "inputs": {                                              │
│        "weight": 0.7,                                         │
│        "image": ["1", 0]  ← Reference from LoadImage           │
│      }                                                         │
│    },                                                          │
│    "6": {  ← CLIPTextEncode                                   │
│      "inputs": {                                              │
│        "text": "young version, 20 years ago..."               │
│      }                                                         │
│    }                                                           │
│  }                                                              │
│                                                                │
└───────────────────────────────────────────────────────────────┘
```

## WebSocket Event Flow

```
Progress Updates During Generation:

Backend → Frontend WebSocket:
{
  "type": "progress",
  "project_id": "abc123",
  "shot_index": 1,
  "progress": 45  ← Percentage
}

Story Update After Upload:
{
  "type": "story_updated",
  "project_id": "abc123",
  "story": { ... }
}

Background Generation Complete:
{
  "type": "completed",
  "project_id": "abc123",
  "scene_id": 0,
  "step": "background_generation",
  "background_image_path": "output/projects/..."
}
```

## Error Handling Flow

```
Error: Reference image with Gemini mode

generate_image(mode="gemini", reference_image_path="...")
  ↓
Detect: reference_image_path provided but mode != "comfyui"
  ↓
Log warning: "Reference images require ComfyUI mode. Auto-switching..."
  ↓
Auto-switch: mode = "comfyui"
  ↓
Continue: Proceed with ComfyUI generation
  ↓
Return: Warning message to user about mode switch
```

## Complete End-to-End Example

```
1. USER: Uploads THEN reference photo for character 0
   → File saved: project/references/abc123_then_ref.png
   → story.json updated: characters[0].then_reference_image_path

2. USER: Uploads NOW reference photo for character 0
   → File saved: project/references/abc123_now_ref.png
   → story.json updated: characters[0].now_reference_image_path

3. USER: Clicks "Generate Background" for scene 0
   → Queues background generation
   → Uses flux_background workflow (no IP-Adapter)
   → Saves: project/backgrounds/scene_0_background_001.png
   → Updates scene.background_image_path

4. USER: Clicks "Generate" on shot 1 (character 0, scene 0)

   GENERATE NOW:
   → Detects: characters[0].now_reference_image_path exists
   → Selects: flux_ipadapter_now workflow
   → Injects: project/references/abc123_now_ref.png into LoadImage
   → Generates: project/images/shot_001_now_001.png
   → Result: Face matches NOW reference photo ✅

   GENERATE THEN:
   → Detects: characters[0].then_reference_image_path exists
   → Selects: flux_ipadapter_then workflow
   → Injects: project/references/abc123_then_ref.png into LoadImage
   → Generates: project/images/shot_001_then_001.png
   → Result: Face matches THEN reference photo ✅

5. RESULT:
   ✅ NOW image looks like NOW reference photo
   ✅ THEN image looks like THEN reference photo
   ✅ Both images have same background from step 3
   ✅ Facial consistency achieved!
```

## File System Layout After Complete Generation

```
output/projects/abc123/
├── references/
│   ├── a1b2c3d4_then_ref.png          ← THEN reference (uploaded)
│   └── e5f6g7h8_now_ref.png           ← NOW reference (uploaded)
├── backgrounds/
│   └── scene_0_background_001.png      ← Background (AI generated)
├── images/
│   ├── shot_001_then_001.png          ← THEN result (IP-Adapter)
│   └── shot_001_now_001.png           ← NOW result (IP-Adapter)
└── story.json                         ← Updated with all paths
```

---

**This visual guide shows how all components work together** to provide reference image support and scene background generation for ThenVsNow projects!
