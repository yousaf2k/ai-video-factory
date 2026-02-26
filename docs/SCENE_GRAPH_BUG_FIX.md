# Scene Graph Bug Fix - 2026-02-26

## Issue

The pipeline was failing at "STEP 3: Scene Graph" with the error:

```
KeyError: 'scenes'
```

**Traceback**:
```
File "C:\AI\ai_video_factory_v1\core\scene_graph.py", line 20, in build_scene_graph
    for i, s in enumerate(story["scenes"]):
                          ~~~~~^^^^^^^^^^
KeyError: 'scenes'
```

## Root Cause

The LLM (when using the prehistoric_pov agent) was returning a JSON **array of scenes directly**, instead of wrapping them in a JSON object with a `scenes` key:

**Expected format**:
```json
{
  "title": "...",
  "style": "...",
  "scenes": [...]
}
```

**Actual format returned**:
```json
[
  {"location": "...", "action": "...", ...},
  {"location": "...", "action": "...", ...},
  ...
]
```

The `scene_graph.py` had code to handle arrays (lines 11-16), but it incorrectly assumed that an array would contain a story object, not the scenes themselves. It was doing `story = story[0]`, which made `story` become the first scene object (a dict with location, action, etc.), not a story object with a `scenes` key.

## Fix Applied

### 1. Updated `core/scene_graph.py`

**Before**:
```python
# Handle case where LLM returns an array containing the story object
if isinstance(story, list):
    if len(story) > 0:
        story = story[0]
    else:
        return []

graph = []

for i, s in enumerate(story["scenes"]):
```

**After**:
```python
# Handle case where LLM returns an array of scenes directly (without wrapping in object)
if isinstance(story, list):
    if len(story) == 0:
        return []
    # Check if first item has scene structure (location, action, etc.)
    # If so, treat entire list as scenes
    if len(story) > 0 and isinstance(story[0], dict):
        if "location" in story[0] or "action" in story[0]:
            # This is a list of scenes, use it directly
            scenes = story
        elif "scenes" in story[0]:
            # List contains story object with scenes key
            story = story[0]
            scenes = story["scenes"]
        else:
            # Unknown format, try to use as scenes
            scenes = story
    else:
        scenes = story
else:
    # Story is an object with scenes key
    scenes = story.get("scenes", [])

graph = []

for i, s in enumerate(scenes):
```

### 2. Added Better Error Handling

- Added `.get()` methods instead of direct key access to handle missing fields gracefully
- Added logging for debugging (info and warning levels)
- Added validation to skip invalid scenes
- Added info log to show how many scenes were processed

### 3. Updated Story Agents

Updated both `agents/story/prehistoric_pov.md` and `agents/story/prehistoric_dinosaur.md` to explicitly specify the correct JSON output format:

```json
{
  "title": "Documentary title",
  "style": "Documentary style",
  "scenes": [...]
}
```

This ensures the LLM returns the proper format going forward.

## Verification

Tested the fix with the actual story that caused the error:

```bash
python -c "
from core.scene_graph import build_scene_graph
with open('output/sessions/session_20260226_112952/story.json', 'r') as f:
    story_json = f.read()
graph = build_scene_graph(story_json)
print(f'✓ Built scene graph with {len(graph)} scenes')
"
```

**Result**: ✅ Successfully built scene graph with 7 scenes

## Files Modified

1. `core/scene_graph.py` - Fixed array handling, added logging and error handling
2. `agents/story/prehistoric_pov.md` - Added explicit JSON format specification
3. `agents/story/prehistoric_dinosaur.md` - Added explicit JSON format specification

## Backward Compatibility

The fix maintains backward compatibility by handling **both** formats:
- ✅ New format: `{"title": "...", "scenes": [...]}`
- ✅ Old/LLM format: `[{...}, {...}, ...]`

This ensures the pipeline works regardless of which format the LLM returns.

## Testing

To test the fix:

```bash
# Test with existing session
python core/main.py --resume session_20260226_112952

# Or generate new content with POV agents
python core/main.py --story-agent prehistoric_pov --idea "Time traveler encounters T-Rex"
```

## Status

✅ **FIXED** - Scene graph now handles both JSON formats correctly

---

**Fixed by**: Claude Code
**Date**: 2026-02-26
**Impact**: Pipeline can now proceed past STEP 3 when LLM returns array of scenes
