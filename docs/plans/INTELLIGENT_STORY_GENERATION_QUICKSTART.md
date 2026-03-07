# Intelligent Story Generation - Quick Start Guide

## What Is This?

A new feature that enables **intelligent shot distribution** based on scene importance. Instead of evenly distributing shots across all scenes, each scene now has a duration, and shots are calculated from that duration.

**Before:** 120 shots ÷ 5 scenes = 24 shots each (even distribution)
**After:** Scene durations determine shot count (important scenes get more shots)

## Quick Start

### 1. Use an Updated Agent

Use one of these agents (already updated with VIDEO_LENGTH support):
- `documentary`
- `netflix_documentary`
- `youtube_documentary`
- `prehistoric_dinosaur`

### 2. Run Pipeline

```bash
python core/main.py \
  --idea "A 5-minute documentary about climate change" \
  --story-agent documentary \
  --auto
```

The system will:
1. Calculate target length from config (default: 600s)
2. Pass target length to story agent
3. Agent generates scene with `scene_duration` for each scene
4. Shot planner calculates shots from duration
5. More important scenes get more shots!

### 3. Check the Output

Look for these logs:
```
[INFO] Target video length: 600s
[INFO] Video length context: 600s
[INFO] Using scene-based shot distribution
[INFO] Scene 0: 9 shots (45s ÷ 5s/shot)
[INFO] Scene 1: 12 shots (60s ÷ 5s/shot)
[INFO] Scene 2: 15 shots (75s ÷ 5s/shot)
[INFO] Total shots planned: 36 (~180s video)
```

## Example Story JSON

```json
{
  "title": "Climate Crisis",
  "style": "cinematic documentary",
  "scenes": [
    {
      "location": "Melting glacier",
      "characters": "Scientists, narrator",
      "action": "Researchers measuring ice loss",
      "emotion": "Concern and urgency",
      "narration": "The ice is disappearing faster than predicted...",
      "scene_duration": 45  // NEW: Duration in seconds
    },
    {
      "location": "Coastal city",
      "characters": "Residents, narrator",
      "action": "Flooding streets, evacuation",
      "emotion": "Fear and determination",
      "narration": "Communities face the reality of rising seas...",
      "scene_duration": 75  // Longer scene = more shots
    }
  ]
}
```

## How Shot Calculation Works

```
Scene Duration ÷ Shot Length = Shots per Scene

Example:
- Scene 0: 45 seconds ÷ 5 seconds/shot = 9 shots
- Scene 1: 60 seconds ÷ 5 seconds/shot = 12 shots
- Scene 2: 75 seconds ÷ 5 seconds/shot = 15 shots

Total: 36 shots = 180 seconds (3 minutes)
```

## Benefits

✅ **Important scenes get more coverage** - Climax scenes can be longer with more shots
✅ **Pacing control** - Fast scenes can be short, slow scenes can be long
✅ **Better length control** - Total video length matches target more accurately
✅ **Backward compatible** - Old agents still work (use even distribution)

## Configuration

Edit `config.py` to adjust:

```python
# Minimum scene duration (seconds)
MIN_SCENE_LENGTH = 15

# Validation tolerance (15% = acceptable deviation)
SCENE_DURATION_TOLERANCE = 0.15

# Default shot length (seconds per shot)
DEFAULT_SHOT_LENGTH = 5

# Target video length (seconds)
TARGET_VIDEO_LENGTH = 600  # 10 minutes
```

## Validation & Auto-Correction

If scene durations don't sum to target length:

**Example:**
- Target: 300 seconds
- Agent generates: 350 seconds (16.7% deviation)

**System response:**
```
[WARN] Scene duration mismatch: 350s vs target 300s (deviation: 16.7%)
[INFO] Auto-corrected scene durations: 350s -> 300s
```

The system **automatically adjusts** all scene durations proportionally to match the target!

## Backward Compatibility

**Old agents** (without scene_duration):
- Work exactly as before
- Use even distribution: max_shots ÷ scene_count
- No errors, no issues

**New agents** (with scene_duration):
- Use intelligent distribution based on scene duration
- More nuanced video production
- Better control over pacing

## Updating Custom Agents

To add VIDEO_LENGTH support to your custom agent:

### Step 1: Add to Agent Template

Create/edit `agents/story/your_agent.md`:

```markdown
## Video Duration Planning

You are creating a story for a **{VIDEO_LENGTH}-second video**.

### Scene Duration Allocation

You MUST assign a `scene_duration` (in seconds) to each scene.

**Rules**:
1. Each scene must have `scene_duration` field (integer, in seconds)
2. Sum of all scene_duration must equal {VIDEO_LENGTH}
3. Minimum scene duration: 15 seconds
4. Recommended durations:
   - Opening scenes: 30-60s
   - Main content: 45-90s
   - Climax scenes: 60-120s
   - Closing scenes: 20-40s

## Output Format

```json
{
  "title": "Your title",
  "style": "your style",
  "scenes": [
    {
      "location": "...",
      "characters": "...",
      "action": "...",
      "emotion": "...",
      "narration": "...",
      "scene_duration": 45  // Duration in seconds
    }
  ]
}
```

{USER_INPUT}
```

### Step 2: Test

```bash
python core/main.py \
  --story-agent your_agent \
  --total-length 300 \
  --auto
```

### Step 3: Verify

Check logs for:
```
[INFO] Video length context: 300s
[INFO] Using scene-based shot distribution
```

## Troubleshooting

**Problem:** Shot count is too high/low
**Solution:** Adjust scene_duration in story JSON, or change DEFAULT_SHOT_LENGTH in config.py

**Problem:** "Scene duration mismatch" warning
**Solution:** Auto-correction will fix it. Adjust agent prompt to generate more accurate durations.

**Problem:** Agent not using scene duration
**Solution:** Ensure agent template includes `{VIDEO_LENGTH}` placeholder and outputs `scene_duration` field

**Problem:** Old agent broken
**Solution:** Old agents should still work. Check for typos or JSON parsing errors.

## Examples

### Example 1: Short Video (3 minutes)

```bash
python core/main.py \
  --idea "Penguin behavior" \
  --story-agent documentary \
  --total-length 180 \
  --auto
```

Expected output:
- Story agent generates scenes summing to 180s
- Shot planner: ~36 shots (180s ÷ 5s/shot)
- Scene-based distribution

### Example 2: Long Video (10 minutes)

```bash
python core/main.py \
  --idea "History of Rome" \
  --story-agent netflix_documentary \
  --total-length 600 \
  --auto
```

Expected output:
- Story agent generates scenes summing to 600s
- Shot planner: ~120 shots (600s ÷ 5s/shot)
- Climax scenes get more shots than intro

### Example 3: Custom Length

```bash
python core/main.py \
  --idea "Quick product demo" \
  --story-agent documentary \
  --total-length 90 \
  --auto
```

Expected output:
- Story agent generates scenes summing to 90s
- Shot planner: ~18 shots (90s ÷ 5s/shot)
- Efficient use of short duration

## Comparison Table

| Feature | Before (Even Distribution) | After (Intelligent Distribution) |
|---------|---------------------------|----------------------------------|
| Shot allocation | max_shots ÷ scene_count | scene_duration ÷ shot_length |
| Scene importance | All scenes equal | Important scenes get more shots |
| Pacing control | Limited | Full control |
| Video length | Approximate | More accurate |
| Backward compatible | N/A | ✅ Yes |

## FAQ

**Q: Do I need to update all my agents?**
A: No. Old agents work as before. Update agents only if you want intelligent distribution.

**Q: What if scene durations don't sum to target?**
A: System auto-corrects proportionally. You'll see a warning in logs.

**Q: Can I still use even distribution?**
A: Yes. Use agents without scene_duration field, or remove {VIDEO_LENGTH} from agent template.

**Q: How do I change shot length?**
A: Edit `DEFAULT_SHOT_LENGTH` in config.py. Default is 5 seconds.

**Q: What's the minimum scene duration?**
A: 15 seconds (configurable via MIN_SCENE_LENGTH in config.py)

**Q: Can scenes have different shot lengths?**
A: Not yet. Currently all scenes use the same shot_length. This may be added in future versions.

**Q: Does this work with batch processing?**
A: Yes. Scene-based distribution works with both single and batch processing modes.

**Q: What happens if LLM doesn't generate scene_duration?**
A: System falls back to even distribution (backward compatible).

## Related Documentation

- [Full Implementation Guide](INTELLIGENT_STORY_GENERATION_IMPLEMENTATION.md) - Technical details
- [Configuration Guide](../config.py) - All configuration options
- [Agent Development](../agents/) - Creating custom agents

## Support

If you encounter issues:
1. Check logs for warnings/errors
2. Verify agent template includes `{VIDEO_LENGTH}` placeholder
3. Ensure story JSON has `scene_duration` field
4. Try with `documentary` agent (known to work)
5. Check configuration in `config.py`

---

**Last Updated:** 2025-02-26
**Version:** 1.0
