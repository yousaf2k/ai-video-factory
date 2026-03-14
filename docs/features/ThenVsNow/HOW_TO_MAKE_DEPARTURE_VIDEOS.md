# How to Make Departure Videos - ThenVsNow FLFI2V Feature

**Date:** March 12, 2026
**Status:** Complete Guide

---

## Overview

Departure videos are the second video segment for each character in a ThenVsNow project. They show both the younger (THEN) and older (NOW) versions of a character walking together to the right side of the frame, exiting the scene as friends who will remain connected.

**Video Logic:**
- **First Frame:** Current character's NOW image (both versions visible)
- **Last Frame:** Next character's NOW image OR scene/set image (if last character)

---

## Prerequisites

Before making departure videos, you need:

1. ✅ **A ThenVsNow session** with the `then_vs_now` story agent
2. ✅ **THEN images generated** for all characters (younger versions)
3. ✅ **NOW images generated** for all characters (older versions with selfie composition)
4. ✅ **Meeting video prompts** defined in story/shots data
5. ✅ **Departure video prompts** defined in story/shots data

---

## Method 1: Automatic Generation (Recommended)

### Step 1: Generate Images First

Departure videos require NOW images to exist first.

**Via Web UI:**
1. Open your session in the web interface
2. Navigate to the Shots tab
3. Click "Regenerate All Images" or regenerate individual shots
4. Wait for all THEN and NOW images to complete

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/sessions/{session_id}/shots/batch-regenerate" \
  -H "Content-Type: application/json" \
  -d '{
    "shot_indices": [1, 2, 3, 4],
    "regenerate_images": true,
    "regenerate_videos": false,
    "force_images": true
  }'
```

### Step 2: Generate Departure Videos

**Via Web UI:**
1. Click "Regenerate All Videos" button
2. The system will automatically generate BOTH Meeting and Departure videos for each shot
3. Wait for completion

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/sessions/{session_id}/shots/batch-regenerate" \
  -H "Content-Type: application/json" \
  -d '{
    "shot_indices": [1, 2, 3, 4],
    "regenerate_images": false,
    "regenerate_videos": true,
    "force_videos": true
  }'
```

### Step 3: Verify Departure Videos

1. Switch to video mode on any shot card
2. Click the "Departure" button to view the departure video
3. Verify:
   - Both characters are visible at the start
   - They walk to the right together
   - Camera follows with smooth tracking
   - Video transitions to next character or scene

---

## Method 2: Generate Only Departure Videos

If you only want to generate/regenerate departure videos (not meeting videos):

### Via Web UI

Currently, the web UI generates both Meeting and Departure videos together. To regenerate only departure videos, use the API.

### Via API

**Regenerate departure video for a single shot:**
```bash
curl -X POST "http://localhost:8000/api/sessions/{session_id}/shots/1/regenerate-video" \
  -H "Content-Type: application/json" \
  -d '{
    "force": true,
    "video_variant": "departure"
  }'
```

**Regenerate departure videos for multiple shots:**
```python
import requests

session_id = "your_session_id"
shot_indices = [1, 3, 5]  # Shots to regenerate

for shot_index in shot_indices:
    response = requests.post(
        f"http://localhost:8000/api/sessions/{session_id}/shots/{shot_index}/regenerate-video",
        json={
            "force": True,
            "video_variant": "departure"
        }
    )
    print(f"Shot {shot_index}: {response.json()}")
```

---

## Method 3: Manual Prompt Customization

If you want to customize the departure video prompt:

### Step 1: Edit Shots JSON

Open `shots.json` in your session folder:

```json
[
  {
    "index": 1,
    "is_flfi2v": true,
    "departure_video_prompt": "TRANSITION: Both younger and older Marlon Brando walk together to the right from the dark office set, smiling and talking in friendly conversation about family matters. Camera tracks smoothly following their movement as they exit. Vintage mahogany desk, green banker's lamp, red velvet drapes visible. Crew member adjusting light flag in background. Warm lamp glow, hopeful closure atmosphere.",
    "departure_video_rendered": false
  }
]
```

### Step 2: Regenerate

Use the API to regenerate with your custom prompt:

```bash
curl -X POST "http://localhost:8000/api/sessions/{session_id}/shots/1/regenerate-video" \
  -H "Content-Type: application/json" \
  -d '{
    "force": true,
    "video_variant": "departure"
  }'
```

---

## Understanding Departure Video Logic

### How the System Determines the Last Frame

The system uses this logic to find the last frame image:

```python
# 1. Try to find next character in same scene
for next_shot in shots[shot_index:]:
    if next_shot.scene_id == current_scene_id and next_shot.index > shot_index:
        if next_shot.now_image_path:
            return next_shot.now_image_path  # Use next character's NOW image

# 2. If no next character, use scene image
if scene.image_path:
    return scene.image_path  # Use movie set background

# 3. Ultimate fallback: use current character's NOW image
return current_shot.now_image_path
```

### Example: Middle Character

**Shot 3: Character C (Al Pacino as Michael Corleone)**

```
First Frame: Current Character's NOW
┌─────────────────────────────────────┐
│  Production Set (Restaurant)        │
│   [Young Al Pacino]  [Older Al Pacino]│
│        (NOW)           (NOW)         │
│   Walking together to the right →   │
└─────────────────────────────────────┘
              ↓ Transition ↓
Last Frame: Next Character's NOW
┌─────────────────────────────────────┐
│  Production Set (Restaurant)        │
│   [Young Robert D.]  [Older Robert D.]│
│        (NOW)           (NOW)         │
│   Character D entering the scene   │
└─────────────────────────────────────┘
```

### Example: Last Character

**Shot 5: Character E (last in scene)**

```
First Frame: Current Character's NOW
┌─────────────────────────────────────┐
│  Production Set (Garden)            │
│   [Young Character E] [Older E]     │
│        (NOW)          (NOW)         │
│   Walking together to the right →   │
└─────────────────────────────────────┘
              ↓ Transition ↓
Last Frame: Scene Image
┌─────────────────────────────────────┐
│  Movie Set Background (Empty)       │
│  Corleone Family Estate Garden      │
│  Beautiful landscaping, natural     │
│  lighting, peaceful atmosphere      │
└─────────────────────────────────────┘
```

---

## Departure Video Prompt Template

The system uses this template for departure video prompts (defined in `agents/story/then_vs_now.md`):

```
TRANSITION: Both characters (THEN and NOW versions) walk together to the right
side of frame, smiling and talking to each other in friendly conversation. Camera
follows their movement with smooth tracking shot as they exit the scene. Production
set and equipment visible in background, crew members working naturally. Warm
lighting, joyful atmosphere, natural walking animation, sense of closure and
continued friendship.
```

### Scene Action Template

```
[Departure/TRANSITION] Both characters (THEN on left, NOW on right) walk together
to the right side of frame, smiling and talking to each other in friendly
conversation. Camera follows their movement with smooth tracking as they exit the
scene together. STRAIGHT-ON EYE-LEVEL CAMERA, PERFECTLY CENTERED SYMMETRICAL
FRAMING, TRIPOD PERSPECTIVE. Production set and equipment visible, crew members
working naturally in background.
```

---

## Troubleshooting

### Issue: "FLFI2V shot X requires both THEN and NOW images"

**Solution:** Generate images first before generating videos.

```bash
# Generate images
curl -X POST "http://localhost:8000/api/sessions/{session_id}/shots/batch-regenerate" \
  -H "Content-Type: application/json" \
  -d '{"shot_indices": [1,2,3], "regenerate_images": true, "regenerate_videos": false}'
```

### Issue: Departure video shows current character in both frames

**Cause:** This is the ultimate fallback when no next character exists and no scene image is available.

**Solution:** Generate a scene image for the last scene:

```python
# 1. Add scene_image_path to your story's last scene
story = session_manager.get_story(session_id)
last_scene = story['scenes'][-1]
last_scene['scene_image_path'] = 'output/sessions/{session_id}/scenes/scene_{scene_id}.png'
session_manager.save_story(session_id, story)

# 2. Generate scene image (you'll need to implement this or do it manually)
```

### Issue: Video doesn't play smoothly or has jerkiness

**Cause:** The FLFI2V workflow may need the "Fix Slow Motion" variant.

**Solution:** Switch to the slower, smoother workflow:

Edit `config.py`:
```python
VIDEO_WORKFLOW = "wan22_flfi2v_fix_slowmotion"
```

Or specify via API:
```bash
curl -X POST "http://localhost:8000/api/sessions/{session_id}/shots/1/regenerate-video" \
  -H "Content-Type: application/json" \
  -d '{
    "force": true,
    "video_workflow": "wan22_flfi2v_fix_slowmotion",
    "video_variant": "departure"
  }'
```

### Issue: "Next character's NOW image not found"

**Cause:** Shots may not be properly ordered by scene_id.

**Solution:** Verify your shots have correct scene_id assignments:

```python
shots = session_manager.get_shots(session_id)
for shot in shots:
    print(f"Shot {shot['index']}: scene_id={shot.get('scene_id')}")
```

---

## Workflow Configuration

Departure videos use the FLFI2V workflow defined in `config.py`:

```python
VIDEO_WORKFLOWS = {
    "wan22_flfi2v": {
        "workflow_path": resolve_path("workflow/video/wan22_flf2v_api.json"),
        "load_image_first_node_id": "128",  # First frame input
        "load_image_last_node_id": "151",   # Last frame input
        "motion_prompt_node_id": "93",      # Motion prompt
        "wan_video_node_id": "150",         # Video output
        "seed_node_id": "142",              # Seed control
        "description": "Wan 2.2 FLFI2V - First/Last frame to video"
    },
    "wan22_flfi2v_fix_slowmotion": {
        "workflow_path": resolve_path("workflow/video/Wan22_FLFI2V_FixSlowMotion_API.json"),
        # ... same node IDs ...
        "description": "Wan 2.2 FLFI2V - Fixed slow motion version"
    }
}
```

**Node Mapping:**
- **Node 128:** First frame (Departure: Current character's NOW image)
- **Node 151:** Last frame (Departure: Next character's NOW or scene image)
- **Node 93:** Motion prompt injection
- **Node 142:** Seed control (seed=1 for first generation)

---

## Quality Checklist

Before finalizing your departure videos, verify:

- [ ] **Walking Animation:** Both characters walk naturally, not slide
- [ ] **Direction:** Movement is toward the right side of frame
- [ ] **Conversation:** Characters appear to be talking/smiling
- [ ] **Camera Tracking:** Camera follows smoothly, not jerky
- [ ] **Exit:** Characters fully exit or transition to next scene
- [ ] **Lighting:** Warm, hopeful lighting throughout
- [ ] **Background:** Production set and crew visible
- [ ] **Duration:** 15-30 seconds (adjust as needed)
- [ ] **Transition:** Smooth transition from current to next character/scene

---

## File Structure

After generation, departure videos are stored as:

```
output/sessions/{session_id}/videos/
├── shot_001_meeting_001.mp4
├── shot_001_departure_001.mp4  ← Departure video
├── shot_002_meeting_001.mp4
├── shot_002_departure_001.mp4  ← Departure video
└── ...
```

**In `shots.json`:**
```json
{
  "index": 1,
  "departure_video_rendered": true,
  "departure_video_path": "output/sessions/session_xxx/videos/shot_001_departure_001.mp4"
}
```

---

## Advanced: Custom Scene Images

To generate custom scene/set images for the last frame:

### Option 1: Manual Generation

1. Use the scene's `set_prompt` from your story
2. Generate an image manually using ComfyUI or Gemini
3. Save it to the session's scenes folder
4. Update `story.json`:
   ```json
   {
     "scenes": [
       {
         "scene_id": 0,
         "set_prompt": "Dark office with mahogany desk...",
         "scene_image_path": "output/sessions/session_xxx/scenes/scene_0.png"
       }
     ]
   }
   ```

### Option 2: Automated Generation (Future Feature)

The system may include a feature to automatically generate scene images from set prompts. This would:
1. Extract `set_prompt` from each scene
2. Generate a high-quality scene image
3. Save it to the session folder
4. Update `scene_image_path` automatically

---

## Summary

**To make departure videos:**

1. ✅ Generate THEN and NOW images first
2. ✅ Use "Regenerate All Videos" or API to generate videos
3. ✅ Switch to video mode and click "Departure" button to view
4. ✅ Verify smooth walking animation and camera tracking
5. ✅ Ensure proper transitions between characters

**Key Points:**
- Departure videos use NOW image as first frame
- Last frame is next character's NOW or scene image
- Both characters walk to the right together
- Camera follows with smooth tracking
- Duration: 15-30 seconds
- Seed=1 for first generation (deterministic)

---

**See Also:**
- [Then Vs Now Quick Start](THEN_VS_NOW_QUICKSTART.md)
- [FLFI2V Video Generation Logic](FLFI2V_VIDEO_GENERATION_LOGIC.md)
- [Then Vs Now Motion Prompt Guide](THEN_VS_NOW_MOTION_PROMPT_GUIDE.md)
