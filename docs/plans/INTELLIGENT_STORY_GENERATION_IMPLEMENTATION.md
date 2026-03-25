# Intelligent Story Generation with Dynamic Scene/Shot Calculation

## Implementation Summary

This document summarizes the implementation of intelligent story generation with dynamic scene/shot calculation, enabling more nuanced video production where shot distribution is based on scene importance and duration rather than even distribution.

## Overview

**What Changed:**
- Story agents can now specify `scene_duration` (in seconds) for each scene
- Shot planner calculates shots per scene from scene duration: `shots = scene_duration ÷ shot_length`
- Target video length is passed to story generation via `{VIDEO_LENGTH}` placeholder
- Scene durations are validated and auto-corrected if they don't match target length

**Key Benefits:**
- More important scenes get more shots (and thus more visual coverage)
- Faster-paced scenes can be shorter with fewer shots
- Slower-paced scenes can be longer with more detail
- Better control over final video length
- Backward compatible - agents without scene_duration still work

## Files Modified

### 1. `config.py`
**Changes:**
- Added `MIN_SCENE_LENGTH = 15` - minimum seconds per scene
- Added `SCENE_DURATION_TOLERANCE = 0.15` - 15% tolerance for validation

**Location:** Lines 237-247

### 2. `core/story_engine.py`
**Changes:**
- Added `target_length` parameter to `build_story()` function
- Injects `{VIDEO_LENGTH}` context into agent prompts
- Added `validate_and_adjust_scene_durations()` function
- Auto-corrects scene durations if outside tolerance

**Key Functions:**
- `build_story(idea, agent_name="default", target_length=None)` - now accepts target_length
- `validate_and_adjust_scene_durations(story, target_length, tolerance=0.15)` - validates and adjusts scene durations

**Example Usage:**
```python
story = build_story(
    "Climate change documentary",
    agent_name="documentary",
    target_length=300  # 5-minute video
)
```

### 3. `core/shot_planner.py`
**Changes:**
- Detects `scene_length` or `scene_duration` fields in scenes
- Calculates shots per scene from duration: `shots = scene_duration ÷ shot_length`
- Implements fallback to even distribution when scene_length missing
- Logs scene-based shot distribution

**Key Logic:**
```python
if has_scene_lengths:
    for scene in scenes:
        scene_len = scene.get("scene_length") or scene.get("scene_duration", 0)
        shots_for_scene = max(MIN_SHOTS_PER_SCENE, int(scene_len / DEFAULT_SHOT_LENGTH))
        logger.info(f"Scene {i}: {shots_for_scene} shots ({scene_len}s ÷ {DEFAULT_SHOT_LENGTH}s/shot)")
```

**Example Output:**
```
[INFO] Using scene-based shot distribution
[INFO] Scene 0: 9 shots (45s ÷ 5s/shot)
[INFO] Scene 1: 12 shots (60s ÷ 5s/shot)
[INFO] Scene 2: 15 shots (75s ÷ 5s/shot)
[INFO] Total shots planned: 36 (~180s video)
```

### 4. `core/main.py`
**Changes:**
- Calculates `target_length` from config or max_shots
- Passes `target_length` to `build_story()` in both auto and manual modes

**Locations:**
- Auto mode: Lines 1271-1282 (STEP 2: Story Generation)
- Manual mode: Lines 1524-1541 (STEP 2: Story Generation)

**Calculation Logic:**
```python
target_length = None
if shot_length and config.TARGET_VIDEO_LENGTH:
    target_length = config.TARGET_VIDEO_LENGTH
elif shot_length and max_shots:
    target_length = max_shots * shot_length
```

### 5. Agent Templates Updated
**Files Modified:**
- `agents/story/documentary.md`
- `agents/story/netflix_documentary.md`
- `agents/story/youtube_documentary.md`
- `agents/story/prehistoric_dinosaur.md`

**Changes to Each Agent:**
- Added `{VIDEO_LENGTH}` placeholder in instructions
- Added `scene_duration` field to JSON output format
- Added scene duration allocation rules and examples
- Added minimum scene duration (15 seconds)
- Added recommended durations by scene type

**Example Agent Structure:**
```markdown
## Video Duration Planning

You are creating a story for a **{VIDEO_LENGTH}-second video**.

### Scene Duration Allocation

You MUST assign a `scene_duration` (in seconds) to each scene.

**Rules**:
1. Each scene must have `scene_duration` field (integer, in seconds)
2. Sum of all scene_duration must equal {VIDEO_LENGTH}
3. Minimum scene duration: 15 seconds
4. Recommended scene durations by type:
   - Opening/hook scenes: 30-60 seconds
   - Main content scenes: 45-90 seconds
   - Climax/peak scenes: 60-120 seconds
   - Closing/outro scenes: 20-40 seconds
```

## Backward Compatibility

**How It Works:**
1. Scene duration is **OPTIONAL** in story JSON
2. If `scene_length` or `scene_duration` is present → use intelligent distribution
3. If missing → fall back to even distribution (current behavior)
4. Agents without `{VIDEO_LENGTH}` placeholder still work normally

**Fallback Logic:**
```python
if has_scene_lengths:
    # Use scene-based distribution
    shots_for_scene = scene_duration / shot_length
else:
    # Use even distribution (current behavior)
    shots_per_scene = max_shots / scene_count
```

## Validation & Auto-Correction

**Tolerance:** 15% deviation acceptable

**Example:**
- Target: 300 seconds
- Actual sum: 350 seconds (16.7% deviation - outside tolerance)
- **Action:** Warn user + auto-correct proportionally
- Result: Adjusted to 300 seconds

**Logging:**
```
[WARN] Scene duration mismatch: 350s vs target 300s (deviation: 16.7%)
[INFO] Auto-corrected scene durations: 350s -> 300s
```

## Testing

### Test 1: Story Generation with Video Length
```python
from core.story_engine import build_story
import json

story = build_story('Climate change', agent_name='documentary', target_length=300)
data = json.loads(story)

# Check for scene_duration
for i, s in enumerate(data['scenes']):
    duration = s.get('scene_duration', 'MISSING')
    print(f'Scene {i}: {duration}s')

total = sum(s.get('scene_duration', 0) for s in data['scenes'])
print(f'Total: {total}s (target: 300s)')
```

**Expected:**
- Each scene has `scene_duration` field
- Sum ≈ 300s (within 15% tolerance)

### Test 2: Shot Planner with Scene Durations
```python
from core.shot_planner import plan_shots

scenes = [
    {'scene_duration': 30, 'location': 'Intro', 'action': 'Start'},
    {'scene_duration': 60, 'location': 'Main', 'action': 'Content'},
    {'scene_duration': 30, 'location': 'End', 'action': 'Finish'}
]

shots = plan_shots(scenes, shot_length=5)
print(f'Total shots: {len(shots)}')
```

**Expected:**
- Total shots: 24 (30÷5 + 60÷5 + 30÷5 = 6+12+6)
- Logs show: "Scene 0: 6 shots (30s ÷ 5s/shot)"

### Test 3: Full Pipeline
```bash
python core/main.py \
  --idea "A 3-minute documentary about penguins" \
  --story-agent documentary \
  --total-length 180 \
  --auto
```

**Expected logs:**
```
[INFO] Target video length: 180s
[INFO] Video length context: 180s
[INFO] Scene 0: 9 shots (45s ÷ 5s/shot)
[INFO] Scene 1: 12 shots (60s ÷ 5s/shot)
[INFO] Total shots planned: 36 (~180s video)
```

### Test 4: Backward Compatibility
```bash
# Use agent WITHOUT scene_duration support
python core/main.py \
  --story-agent dramatic \
  --max-shots 24 \
  --auto
```

**Expected:** Works normally (even distribution, no errors)

## Example Story JSON (New Format)

```json
{
  "title": "Penguins of Antarctica",
  "style": "cinematic documentary",
  "scenes": [
    {
      "location": "Antarctic ice shelf",
      "characters": "Penguin colony, narrator",
      "action": "Penguins emerging from water, gathering on ice",
      "emotion": "Wonder at nature's resilience",
      "narration": "In the harshest environment on Earth, life finds a way...",
      "scene_duration": 45
    },
    {
      "location": "Ice interior - nesting grounds",
      "characters": "Penguin pairs, eggs, chicks",
      "action": "Parents nesting, protecting eggs from cold",
      "emotion": "Tenderness mixed with harsh reality",
      "narration": "For these pairs, it's a race against time...",
      "scene_duration": 60
    },
    {
      "location": "Ocean edge - hunting ground",
      "characters": "Adult penguins, predator seals",
      "action": "Penguins diving, hunting krill, evading seals",
      "emotion": "Danger and survival instinct",
      "narration": "The ocean provides, but it also takes...",
      "scene_duration": 75
    }
  ]
}
```

## Shot Distribution Example

**Story with Scene Durations:**
- Scene 0: 45s → 9 shots (45s ÷ 5s/shot)
- Scene 1: 60s → 12 shots (60s ÷ 5s/shot)
- Scene 2: 75s → 15 shots (75s ÷ 5s/shot)

**Result:**
- Total duration: 180s (3 minutes)
- Total shots: 36
- Shot distribution: Intelligent based on scene importance
- Important scenes get more coverage (hunting scene: 15 shots vs intro: 9 shots)

## Design Decisions

### Decision 1: Scene Duration Format
**Choice:** Seconds (integer)

**Rationale:**
- More intuitive than shot count (5s = 5s, not "1 shot")
- Allows different shot lengths in future
- Consistent with existing DEFAULT_SHOT_LENGTH and TARGET_VIDEO_LENGTH
- Easier validation: sum(scene_duration) ≈ target_length

### Decision 2: Backward Compatibility
**Choice:** scene_length is OPTIONAL with intelligent fallback

**Rationale:**
- Existing agents/stories without scene_length still work
- New agents opt-in by adding scene_length to output
- Gradual migration - no breaking changes

### Decision 3: Context Passing Method
**Choice:** {VIDEO_LENGTH} placeholder in agent prompts

**Rationale:**
- No API changes (build_story() signature backward compatible)
- Flexible - each agent can use context differently
- Agent-specific - some agents may ignore length
- Template-based injection

### Decision 4: Validation Strategy
**Choice:** Warning with auto-correction (not hard failure)

**Rationale:**
- LLM output is unpredictable (can't guarantee exact sums)
- Don't block video generation for small errors
- Warn user + auto-correct proportionally
- 15% tolerance reasonable for creative content

## Success Criteria

✅ Story generation accepts target_length parameter
✅ Video length context injected via {VIDEO_LENGTH} placeholder
✅ Story agents generate scene_duration field (in seconds)
✅ Scene durations validated (within 15% tolerance)
✅ Auto-correction works when durations don't match target
✅ Shot planner uses scene_length to calculate shots per scene
✅ Fallback to even distribution when scene_length missing
✅ Backward compatible (old agents work unchanged)
✅ Pipeline integration passes target_length correctly
✅ Logs show scene-based shot distribution

## Next Steps (Optional Enhancements)

1. **Add VIDEO_LENGTH support to more agents:**
   - `agents/story/time_traveler.md`
   - `agents/story/prehistoric_pov.md`
   - Custom user agents

2. **Image agent updates (optional):**
   - Add scene duration awareness to image generation
   - Adjust pacing based on scene duration

3. **Advanced features:**
   - Support variable shot lengths (slow-motion, fast cuts)
   - Scene-based shot length configuration
   - Minimum/maximum shot duration constraints

4. **Documentation:**
   - Update user guide with new feature
   - Add examples showing before/after comparison
   - Create tutorial for custom agent creation

## Migration Guide for Custom Agents

To add VIDEO_LENGTH support to a custom story agent:

1. **Add to agent template:**
```markdown
## Video Duration Planning

You are creating a story for a **{VIDEO_LENGTH}-second video**.

### Scene Duration Allocation

You MUST assign a `scene_duration` (in seconds) to each scene.

**Rules**:
1. Each scene must have `scene_duration` field (integer, in seconds)
2. Sum of all scene_duration must equal {VIDEO_LENGTH}
3. Minimum scene duration: 15 seconds
```

2. **Update JSON format:**
```json
{
  "scenes": [
    {
      "location": "...",
      "characters": "...",
      "action": "...",
      "emotion": "...",
      "narration": "...",
      "scene_duration": 45  // Add this field
    }
  ]
}
```

3. **Test:**
```bash
python core/main.py \
  --story-agent your_custom_agent \
  --total-length 300 \
  --auto
```

## Troubleshooting

**Issue:** Scene durations don't sum to target length
**Solution:** Auto-correction will adjust proportionally. Check logs for warnings.

**Issue:** Shot count is too high/low
**Solution:** Adjust scene_duration values in story, or modify DEFAULT_SHOT_LENGTH in config.py

**Issue:** Old agents not using scene duration
**Solution:** This is expected. Old agents use even distribution. Update agent template to add VIDEO_LENGTH support.

**Issue:** Validation errors on story generation
**Solution:** Ensure agent includes `{VIDEO_LENGTH}` placeholder and outputs `scene_duration` field in JSON

## Related Files

- `config.py` - Configuration constants
- `core/story_engine.py` - Story generation with target_length support
- `core/shot_planner.py` - Scene-based shot distribution
- `core/main.py` - Pipeline integration
- `agents/story/*.md` - Agent templates with VIDEO_LENGTH support

## Version History

- **v1.0** - Initial implementation (2025-02-26)
  - Added MIN_SCENE_LENGTH and SCENE_DURATION_TOLERANCE to config
  - Updated story_engine.py with target_length parameter
  - Enhanced shot_planner.py with scene-based distribution
  - Integrated pipeline changes in main.py
  - Updated 4 priority agents with VIDEO_LENGTH support
