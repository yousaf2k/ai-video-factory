# Video Length Configuration Guide

## Overview

The AI Film Studio now supports **custom video lengths**. You can specify:
- Total video length (e.g., 60 seconds)
- Length per shot (e.g., 5 seconds)
- The system automatically calculates how many shots to generate

## How It Works

### The Math

```
Number of Shots = Total Video Length ÷ Shot Length

Example:
- Total video: 60 seconds
- Shot length: 5 seconds
- Shots needed: 60 ÷ 5 = 12 shots
```

### Video Generation

Each shot generates a video of the specified length:
- **Default**: 5 seconds per shot
- **Framerate**: 24 FPS (configurable in `config.py`)
- **Frames per shot**: Length × FPS (e.g., 5s × 24fps = 120 frames)

## Usage

### Run Pipeline with Custom Length

```bash
python core/main.py
```

You'll be prompted:

```
==================================================================
VIDEO CONFIGURATION
==================================================================

Enter total video length in seconds (or press Enter for default based on story):
```

**Options:**

1. **Specify total length**:
   ```
   Enter total video length: 60
   Enter length per shot in seconds (default: 5.0s): 5

   [INFO] Target: 60.0s video, 5.0s per shot = 12 shots
   ```

2. **Use story-based length**:
   ```
   Enter total video length: [press Enter]
   Enter length per shot in seconds: 3

   [INFO] Shot length: 3.0s (number of shots based on story)
   → System generates as many shots as needed for the story
   ```

3. **Use all defaults**:
   ```
   Enter total video length: [press Enter]
   Enter length per shot in seconds: [press Enter]

   [INFO] Shot length: 5.0s (number of shots based on story)
   ```

## Examples

### Example 1: 30-Second Video

```
Enter total video length: 30
Enter length per shot: 5

Result:
- Total: 30 seconds
- Per shot: 5 seconds
- Shots: 30 ÷ 5 = 6 shots
- Frames per shot: 5 × 24 = 120 frames
```

### Example 2: 2-Minute Video with 10-Second Shots

```
Enter total video length: 120
Enter length per shot: 10

Result:
- Total: 120 seconds (2 minutes)
- Per shot: 10 seconds
- Shots: 120 ÷ 10 = 12 shots
- Frames per shot: 10 × 24 = 240 frames
```

### Example 3: Story-Based (Unknown Length)

```
Enter total video length: [press Enter]
Enter length per shot: 4

Result:
- Shot length: 4 seconds each
- Number of shots: Determined by story (typically 5-10)
- Total length: Depends on story (e.g., 7 shots × 4s = 28 seconds)
```

## Configuration

### Default Settings

Edit `config.py` to change defaults:

```python
# Default video length per shot (in seconds)
DEFAULT_SHOT_LENGTH = 5.0

# Video framerate (fps)
VIDEO_FPS = 24

# Target total video length (in seconds)
# Set to None to generate based on story length
TARGET_VIDEO_LENGTH = None  # or 60.0 for 60 seconds
```

### Wan 2.2 Video Node ID

Ensure `WAN_VIDEO_NODE_ID` is correctly set in `config.py`:

```python
# WanImageToVideo node ID (for setting video length)
WAN_VIDEO_NODE_ID = "98"  # Update to match your workflow
```

To find this ID:
1. Open your workflow in ComfyUI
2. Find the **WanImageToVideo** node
3. Right-click → "Node ID for Save"
4. Update `config.py` with this value

## How Video Length is Set

The system updates the WanImageToVideo node parameters:

```
WanImageToVideo widgets_values:
  [width, height, frames, something]

Example:
  Before: [1024, 576, 81, 1]  # 81 frames at 24fps = 3.375s
  After:  [1024, 576, 120, 1] # 120 frames at 24fps = 5.0s
```

**Frames = Length (seconds) × FPS**

## Session Management

Video configuration is saved in each session:

```json
{
  "video_config": {
    "total_length": 60.0,
    "shot_length": 5.0,
    "fps": 24
  }
}
```

When resuming a session, the same video length is used automatically.

## Tips

### Short Videos (< 30 seconds)
- Use 3-5 second shots
- More shots, shorter each
- Good for trailers, teasers

### Medium Videos (30s - 2 minutes)
- Use 5-10 second shots
- Balanced pace
- Good for short stories

### Long Videos (2+ minutes)
- Use 10-15 second shots
- Fewer shots, longer each
- Good for documentaries

### Performance Considerations

**Shorter shots** (3-5 seconds):
- ✅ Faster to render
- ✅ More dynamic cuts
- ❌ More images to generate
- ❌ More files to manage

**Longer shots** (10+ seconds):
- ✅ Fewer images to generate
- ✅ Smoother, cinematic
- ❌ Longer render time per shot
- ❌ Less dynamic

## Cost Estimation

```
Total Cost = (Number of Shots) × (Cost per Shot)

Cost per Shot:
- Image generation: ~$0.08
- Video rendering: Free (ComfyUI local)
- Total: ~$0.08 per shot

Examples:
- 6 shots  × $0.08 = $0.48
- 12 shots × $0.08 = $0.96
- 24 shots × $0.08 = $1.92
```

## Troubleshooting

### "Video length not working"

- Check `WAN_VIDEO_NODE_ID` in `config.py`
- Verify the node ID matches your workflow
- Check ComfyUI console for errors

### "Too many/few shots generated"

- Adjust shot length (longer = fewer shots)
- Or specify exact total length
- The system limits shots to: total_length ÷ shot_length

### "Videos are wrong length"

- Verify `VIDEO_FPS` in `config.py`
- Check workflow is using the correct node
- Review session metadata for actual settings

## Advanced: Presets

Create presets in `config.py`:

```python
# Preset configurations
VIDEO_PRESETS = {
    "trailer": {"shot_length": 3.0, "total_length": 30.0},
    "short": {"shot_length": 5.0, "total_length": 60.0},
    "medium": {"shot_length": 8.0, "total_length": 120.0},
    "long": {"shot_length": 10.0, "total_length": 300.0}
}
```

Use in code:
```python
preset = VIDEO_PRESETS["trailer"]
shot_length = preset["shot_length"]
total_length = preset["total_length"]
```

## Summary

✅ **Flexible Length Control** - Set total or per-shot length
✅ **Automatic Calculation** - System determines shot count
✅ **Session Persistence** - Settings saved per session
✅ **Frame Accurate** - Precise frame count for each shot
✅ **Cost Predictable** - Know cost before generating

**You have full control over your video length!**
