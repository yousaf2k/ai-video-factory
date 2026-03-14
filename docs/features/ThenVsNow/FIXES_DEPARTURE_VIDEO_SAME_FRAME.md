# Fix: Departure Video Using Same NOW Image for Both Frames

**Date:** March 13, 2026
**Status:** ✅ Fixed

---

## Problem

When generating departure videos for FLFI2V shots, both the first frame and last frame were using the current character's NOW image. This was because each character had a different `scene_id`, so the "next character in the same scene" search always failed.

### Root Cause

In `core/story_engine.py`, the `generate_shots_from_then_vs_now_story()` function was distributing characters across multiple scenes:

```python
# OLD CODE (BUGGY):
scene_id = char_idx % len(scenes) if scenes else 0
```

This resulted in:
- Character 0 → scene_id 0
- Character 1 → scene_id 1
- Character 2 → scene_id 2
- etc.

Since departure videos search for the **next character in the same scene**, this search always failed because each character was alone in their own scene. The system would fall back to using the current character's NOW image for both frames.

---

## Solution

### Fix 1: Updated Shot Generation (For New Sessions)

**File:** `core/story_engine.py` (line 280)

**Before:**
```python
for char_idx, character in enumerate(characters):
    # Distribute characters across available scenes
    scene_id = char_idx % len(scenes) if scenes else 0
```

**After:**
```python
for char_idx, character in enumerate(characters):
    # For ThenVsNow, all characters appear in scene 0 (the main movie set)
    # This allows departure videos to transition from one character to the next
    scene_id = 0
```

**Why:** For ThenVsNow reunion videos, all characters should be in the same scene (the movie set). This allows departure videos to properly find the "next character in the same scene" and use their NOW image as the last frame.

### Fix 2: Migration Script (For Existing Sessions)

Created `fix_scene_ids.py` to update existing sessions:

```bash
# List all sessions and their scene_id status
python fix_scene_ids.py --list

# Fix a specific session (dry run first)
python fix_scene_ids.py --session session_20260312_230034

# Actually apply the fix
python fix_scene_ids.py --session session_20260312_230034 --live
```

**What the script does:**
1. Loads shots.json for the session
2. Checks which shots have scene_id != 0
3. Updates all shots to have scene_id = 0
4. Saves the updated shots.json

---

## How Departure Videos Work Now

### For Shot 1 (First Character):

```
First Frame: Shot 1's NOW image
Last Frame:  Shot 2's NOW image (next character in scene 0)
Result:      Video shows Character 1 transitioning into Character 2
```

### For Shot 2 (Middle Character):

```
First Frame: Shot 2's NOW image
Last Frame:  Shot 3's NOW image (next character in scene 0)
Result:      Video shows Character 2 transitioning into Character 3
```

### For Shot N (Last Character):

```
First Frame: Shot N's NOW image
Last Frame:  Scene image OR Shot N's NOW image (fallback)
Result:      Video shows Character N transitioning to scene set
```

---

## Verification Steps

### 1. Check Session Status

```bash
# List all sessions to see which need fixing
python fix_scene_ids.py --list
```

Expected output after fix:
```
session_20260312_230034
  Title: Titanic: The Reunion
  Shots: 10
  Scene IDs (first 10): 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
  Status: OK
```

### 2. Debug Frame Selection

```bash
# Check which images will be used for departure video
python debug_departure_frames.py --session session_20260312_230034 --shot 1
```

Expected output (after images generated):
```
1. FIRST FRAME (should be current character's NOW image):
   Path: shot_001_now_001.png
   Status: OK

2. LAST FRAME (should be next character's NOW image or scene image):
   Searching for next character in scene 0...
     Shot 2: scene_id=0, has_now=True <- CANDIDATE
       FOUND: shot_002_now_001.png

Last frame source: Shot 2 NOW image
Last frame path: shot_002_now_001.png
File status: OK
```

### 3. Generate Departure Video

After generating all THEN/NOW images:

**Option A: Web UI**
1. Navigate to session page
2. Select shots for departure video generation
3. Click "Regenerate Videos"
4. Select "Departure" variant

**Option B: API**
```bash
curl -X POST "http://localhost:8000/api/sessions/session_20260312_230034/shots/1/regenerate-video" \
  -H "Content-Type: application/json" \
  -d '{
    "force": true,
    "video_mode": "comfyui",
    "video_workflow": "wan22_flfi2v",
    "video_variant": "departure"
  }'
```

### 4. Verify Output

The departure video should show:
- **Start:** Current character (both THEN and NOW versions)
- **Action:** Both versions walking together to the right
- **End:** Next character's NOW versions entering frame (smooth transition)

---

## Sessions Fixed

All existing ThenVsNow sessions were fixed:

| Session | Title | Shots | Scene IDs Before | Scene IDs After |
|---------|-------|-------|------------------|-----------------|
| session_20260312_230034 | Titanic: The Reunion | 10 | 0,1,2,3,4,5,6,7,8,9 | All 0 |
| session_20260312_214022 | The Matrix: The Reunion | 8 | 0,0,1,1,2,2,3,3 | All 0 |
| session_20260312_202555 | Minority Report: Reunion | 16 | 0,0,1,1,2,2,3,3,4,4... | All 0 |
| session_20260312_192053 | From Dusk Till Dawn: Reunion | 20 | 0,0,1,1,2,2,3,3,4,4... | All 0 |

---

## Code Changes Summary

### Modified Files

1. **`core/story_engine.py`** (line 280)
   - Changed: `scene_id = char_idx % len(scenes) if scenes else 0`
   - To: `scene_id = 0`
   - Reason: All ThenVsNow characters should be in scene 0

### New Tools

1. **`fix_scene_ids.py`**
   - Lists all sessions and their scene_id status
   - Fixes existing sessions by setting all scene_ids to 0
   - Dry-run mode for safe testing

2. **`debug_departure_frames.py`**
   - Diagnoses which images will be used for departure videos
   - Shows search logic for finding next character
   - Identifies fallback behavior

---

## Impact

### Before Fix

```
Departure video for Shot 1:
  First frame: Shot 1 NOW image
  Last frame:  Shot 1 NOW image (fallback - no next character in same scene)
  Result: No transition, same character in both frames
```

### After Fix

```
Departure video for Shot 1:
  First frame: Shot 1 NOW image
  Last frame:  Shot 2 NOW image (next character found in scene 0)
  Result: Smooth transition from Character 1 to Character 2
```

---

## Future Enhancements

### Scene Image Support

Currently, the last character's departure video falls back to using their own NOW image for both frames. Future enhancement could:

1. Auto-generate scene images for each scene
2. Add `scene_image_path` to scene data
3. Use scene image as last frame for final character's departure video

Example:
```python
# In scene generation
scene['scene_image_path'] = f"scenes/scene_{scene_id:03d}.png"

# In departure video logic
if not last_frame_image:
    scene_image_path = scene.get('scene_image_path')
    if scene_image_path:
        last_frame_image = scene_image_path
```

---

## Status

✅ **Fixed and Deployed**

- Root cause identified and fixed
- All existing sessions migrated
- New sessions will have correct scene_ids
- Departure videos now properly transition between characters

---

**See Also:**
- [Departure Video Generation Logic](../guides/FLFI2V_VIDEO_GENERATION_LOGIC.md)
- [How to Make Departure Videos](../guides/HOW_TO_MAKE_DEPARTURE_VIDEOS.md)
- [Then Vs Now Quick Start](../guides/THEN_VS_NOW_QUICKSTART.md)
