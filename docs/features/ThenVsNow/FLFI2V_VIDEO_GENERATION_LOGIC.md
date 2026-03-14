# FLFI2V Video Generation Logic

**Date:** March 12, 2026
**Status:** Updated

---

## Overview

FLFI2V (First Last Frame Image to Video) generation for "Then Vs Now" projects uses different image combinations for Meeting and Departure videos.

---

## Video Generation Logic

### Meeting Video

**First Frame:** THEN image (younger character)
**Last Frame:** NOW image (older character)

The meeting video shows the emotional reunion when the older character arrives and meets their younger self.

**Workflow:**
- Load THEN image into first frame node (node 128)
- Load NOW image into last frame node (node 151)
- Use meeting_video_prompt for motion

**Example Flow:**
```
Young Marlon Brando (THEN) ← First Frame
     ↓
     Walk toward & hug
     ↓
Older Marlon Brando (NOW) ← Last Frame
```

---

### Departure Video

**First Frame:** NOW image (current character)
**Last Frame:** Next character's THEN image OR Scene image

The departure video shows both characters leaving the set together, transitioning to the next scene.

**Workflow:**
- Load current character's NOW image into first frame node (node 128)
- Find next character's THEN image OR scene image
- Load found image into last frame node (node 151)
- Use departure_video_prompt for motion

**Example Flow:**
```
Current Character's NOW (both versions) ← First Frame
     ↓
     Walk together to the right
     ↓
Next Character's THEN OR Scene Image ← Last Frame
```

---

## Implementation Details

### Finding the Next Character's THEN Image

The system searches for the next shot that meets these criteria:
1. Has the same `scene_id` as the current shot
2. Has an `index` greater than the current shot
3. Has a generated `then_image_path`

**Algorithm:**
```python
for next_shot in shots[shot_index:]:  # Start from current shot
    if next_shot.get('scene_id') == current_scene_id and next_shot.get('index') > shot_index:
        if next_shot.get('then_image_path'):
            return next_shot['then_image_path']  # Found next character's THEN image
```

### Fallback: Scene Image

If no next character is found in the current scene, the system uses a scene/set image:
1. Retrieves the scene from story data using `scene_id`
2. Looks for `scene_image_path` in the scene data
3. Uses this image as the last frame

**Scene Image Storage:**
- Scene images are stored in the story's `scenes` array
- Each scene can have an optional `scene_image_path` field
- This field can be populated by a separate scene image generation feature

### Ultimate Fallback

If neither next character's NOW image nor scene image is available:
- Use current character's NOW image as both first and last frame
- Log a warning: "Using current character's NOW image (fallback)"

---

## Code Changes

### 1. Modified `_generate_flfi2v_video()` Function

**Added parameter:**
```python
def _generate_flfi2v_video(
    self, session_id: str, shot: Dict[str, Any],
    variant: str, video_mode: Optional[str],
    workflow_name: Optional[str], session_title: Optional[str],
    video_filename: str, seed: Optional[int] = None,
    last_frame_image_path: Optional[str] = None  # NEW
) -> str:
```

**Updated image injection logic:**
```python
if variant == "meeting":
    # THEN image (first frame) + NOW image (last frame)
    first_frame = shot['then_image_path']
    last_frame = shot['now_image_path']

elif variant == "departure":
    # NOW image (first frame) + next character's NOW or scene image (last frame)
    first_frame = shot['now_image_path']
    last_frame = last_frame_image_path or shot['now_image_path']
```

### 2. Modified `_regenerate_flfi2v_videos()` Function

**Added next character search:**
```python
# Find next character's THEN image for departure video
last_frame_image = None

current_scene_id = shot.get('scene_id')
if current_scene_id is not None:
    # Find next shot with same scene_id
    for next_shot in shots[shot_index:]:
        if next_shot.get('scene_id') == current_scene_id and next_shot.get('index') > shot_index:
            if next_shot.get('then_image_path'):
                last_frame_image = next_shot['then_image_path']
                break

    # If no next character, try scene image
    if not last_frame_image:
        story = self.session_manager.get_story(session_id)
        if story and current_scene_id < len(story.get('scenes', [])):
            scene = story['scenes'][current_scene_id]
            scene_image_path = scene.get('scene_image_path')
            if scene_image_path:
                last_frame_image = scene_image_path
```

### 3. Added `scene_image_path` Field

**Python Model (`web_ui/backend/models/story.py`):**
```python
class Scene(BaseModel):
    # ... existing fields ...
    scene_image_path: Optional[str] = Field(default=None, description="Path to generated scene/set image")
```

**TypeScript Type (`web_ui/frontend/src/types/index.ts`):**
```typescript
export interface Scene {
  // ... existing fields ...
  scene_image_path?: string;
}
```

---

## Examples

### Example 1: Middle Character

**Shot 3: Character C**
- **Meeting Video:** Character C THEN → Character C NOW
- **Departure Video:** Character C NOW (first) → Character D THEN (last)

**Flow:**
```
Meeting: [C_YOUNG] → [C_OLD]
Departure: [C_OLD + C_OLD] → [D_YOUNG + D_YOUNG]
```

### Example 2: Last Character

**Shot 5: Character E (last in scene)**
- **Meeting Video:** Character E THEN → Character E NOW
- **Departure Video:** Character E NOW (first) → Scene Image (last)

**Flow:**
```
Meeting: [E_YOUNG] → [E_OLD]
Departure: [E_OLD + E_OLD] → [MOVIE_SET_BACKGROUND]
```

---

## Video File Naming

**Meeting videos:**
```
shot_001_meeting_001.mp4  (first generation)
shot_001_meeting_002.mp4  (regeneration)
```

**Departure videos:**
```
shot_001_departure_001.mp4  (first generation)
shot_001_departure_002.mp4  (regeneration)
```

---

## Logging

The system logs detailed information about which images are used:

```
FLFI2V shot 1 meeting video using fixed seed: 1
Meeting video first frame: THEN image
Meeting video last frame: NOW image

FLFI2V shot 1 departure video using fixed seed: 1
Departure video first frame: NOW image (current character)
Departure video last frame: Next character's THEN image (shot 3)
```

Or if using scene image:

```
Departure video first frame: NOW image (current character)
Departure video last frame: Scene image (scene 2)
```

---

## Future Enhancements

### Scene Image Generation

Currently, scene images must be generated separately. A future feature could:
1. Generate scene/set images using the `set_prompt` from story data
2. Automatically populate `scene_image_path` for each scene
3. Provide UI for regenerating scene images

**Potential implementation:**
```python
def generate_scene_image(session_id: str, scene_id: int):
    """Generate a scene/set image for departure video last frames"""
    story = session_manager.get_story(session_id)
    scene = story['scenes'][scene_id]
    set_prompt = scene.get('set_prompt', '')

    # Generate image using set_prompt
    image_path = generate_image(prompt=set_prompt, ...)

    # Save to scene
    scene['scene_image_path'] = image_path
    save_story(session_id, story)
```

---

## Verification Checklist

When testing FLFI2V video generation:

- [ ] Meeting video uses THEN image as first frame
- [ ] Meeting video uses NOW image as last frame
- [ ] Departure video uses NOW image as first frame
- [ ] Departure video uses next character's THEN image as last frame (when available)
- [ ] Departure video uses scene image as last frame (when no next character)
- [ ] Departure video falls back gracefully when no images available
- [ ] Video files are named correctly with meeting/departure suffix
- [ ] Logging shows correct image sources for each video
- [ ] Videos play smoothly with correct motion prompts

---

**Status:** ✅ Implemented and ready for use
**Files Modified:**
- `web_ui/backend/services/generation_service.py`
- `web_ui/backend/models/story.py`
- `web_ui/frontend/src/types/index.ts`
