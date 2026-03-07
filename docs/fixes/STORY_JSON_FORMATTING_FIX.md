# Story JSON Formatting Fix

## Date: 2026-02-26

## Problem

The `story.json` file was being written as a single line, making it difficult to read and debug. The JSON was minified/compressed without proper indentation or line breaks.

**Example of the problem:**
```json
{"title":"Video Title","style":"dramatic cinematic","scenes":[{"location":"Scene 1","characters":"Character","action":"Action","emotion":"Emotion","narration":"Narration text","scene_duration":45}]}
```

## Root Cause

In `core/story_engine.py`, the `json.dumps()` function was called without the `indent=2` parameter:
```python
story_json = json.dumps(adjusted_story, ensure_ascii=False)  # Missing indent parameter
```

This caused the JSON to be output as a single line.

## Solution

Updated `core/story_engine.py` to add proper indentation:

### Change 1: Added indentation for stories with target_length

**Before:**
```python
if target_length:
    try:
        story = json.loads(story_json)
        is_valid, actual_total, diff, adjusted_story = validate_and_adjust_scene_durations(
            story, target_length, config.SCENE_DURATION_TOLERANCE
        )
        story_json = json.dumps(adjusted_story, ensure_ascii=False)
```

**After:**
```python
if target_length:
    try:
        story = json.loads(story_json)
        is_valid, actual_total, diff, adjusted_story = validate_and_adjust_scene_durations(
            story, target_length, config.SCENE_DURATION_TOLERANCE
        )
        story_json = json.dumps(adjusted_story, ensure_ascii=False, indent=2)
```

### Change 2: Added indentation for stories WITHOUT target_length

Added a new else branch to format JSON even when no target_length is provided:

```python
else:
    # Format JSON with proper indentation even when no target_length
    try:
        story = json.loads(story_json)
        story_json = json.dumps(story, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        logger.warning("Failed to parse story JSON for formatting")
```

## Result

Now the `story.json` file is properly formatted with indentation and line breaks:

**Example after fix:**
```json
{
  "title": "Video Title",
  "style": "dramatic cinematic",
  "scenes": [
    {
      "location": "Scene 1",
      "characters": "Character",
      "action": "Action",
      "emotion": "Emotion",
      "narration": "Narration text",
      "scene_duration": 45
    }
  ]
}
```

## Test Results

Created `test_json_formatting.py` to verify the fix:

**Test 1: With target_length**
- ✅ JSON is valid
- ✅ JSON is multiline (46 lines)
- ✅ JSON has proper indentation (44 indented lines)
- ✅ All scenes have scene_duration field

**Test 2: Without target_length**
- ✅ JSON is valid
- ✅ JSON is multiline (54 lines)

## Files Modified

1. **core/story_engine.py** (lines 137-151)
   - Added `indent=2` parameter to both json.dumps() calls
   - Added else branch for formatting when no target_length

## Benefits

1. **Readability**: story.json files are now human-readable
2. **Debugging**: Easier to inspect and verify story structure
3. **Version Control**: Better git diffs when story.json changes
4. **Manual Editing**: Users can now manually edit story.json if needed
5. **Consistency**: All JSON output uses the same formatting standard

## Backward Compatibility

This change is fully backward compatible:
- JSON parsing (`json.loads()`) works the same whether formatted or minified
- All existing code that reads story.json will continue to work
- No changes to data structure, only formatting

## Testing

To test the fix:

```bash
python test_json_formatting.py
```

Expected output:
- Both tests should pass
- JSON should be multiline with proper indentation
- All scenes should have scene_duration field (when target_length is provided)

---

**Fix completed**: 2026-02-26
**Status**: ✅ Implemented and tested
**Test result**: All tests passed
