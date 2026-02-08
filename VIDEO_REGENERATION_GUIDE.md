# Video Regeneration Guide

## Overview

The **Video Regeneration** feature allows you to re-render videos from existing sessions without regenerating images. This is useful when you want to:

- ✅ Change video length (e.g., from 5s shots to 10s shots)
- ✅ Re-render failed videos
- ✅ Try different quality settings
- ✅ Re-render after ComfyUI updates
- ✅ Adjust to new workflow settings

## Quick Start

### Interactive Mode (Easiest)

```bash
python regenerate.py
```

You'll see a menu:
```
==================================================================
VIDEO REGENERATION WIZARD
==================================================================

Available Sessions:
  1. ✓ session_20250207_143000
     Idea: A futuristic city at sunset...
     Shots: 7, Videos: 7
  2. ⏳ session_20250208_002238
     Idea: A documentary about Indus Valley...
     Shots: 7, Videos: 4

Select session number (or 'q' to quit): 2

[INFO] Current shot length: 5.0s
Enter new shot length (or press Enter to keep 5.0s): 10

Regenerate all videos (including already rendered)? (y/n): n

[INFO] Will render 3 videos (only missing ones)
Proceed with rendering? (y/n): y
```

### Command-Line Mode

```bash
# List sessions first
python regenerate.py --list

# Regenerate with new length
python regenerate.py --session session_20250208_002238 --length 10

# Force regenerate all videos
python regenerate.py --session session_20250208_002238 --force

# Change length and regenerate all
python regenerate.py --session session_20250208_002238 --length 8 --force
```

## Use Cases

### Scenario 1: Change Video Length

**Problem:** Videos are too short

```bash
python regenerate.py --session session_XXX --length 10
```

This changes each shot from current length (e.g., 5s) to 10 seconds.

**Result:**
- Old: 7 shots × 5s = 35 seconds
- New: 7 shots × 10s = 70 seconds
- Uses existing images (no need to regenerate)

### Scenario 2: Re-render Failed Videos

**Problem:** Some videos failed during rendering

```bash
python regenerate.py --session session_XXX
```

This automatically detects which videos are missing and only renders those.

**Result:**
- Checks all 7 shots
- Finds 4 rendered, 3 missing
- Renders only the 3 missing ones
- Saves time and resources

### Scenario 3: Try Different Settings

**Problem:** Want to re-render with new ComfyUI settings

```bash
# Update your workflow in ComfyUI
# Save the updated workflow
# Then re-render all videos:
python regenerate.py --session session_XXX --force
```

This regenerates all videos using the new workflow settings.

**Result:**
- All videos re-rendered
- Uses your updated workflow
- Existing images reused

### Scenario 4: Mixed Scenario

**Problem:** Want longer videos AND re-render everything

```bash
python regenerate.py --session session_XXX --length 8 --force
```

This changes shot length to 8 seconds and regenerates all videos.

## Commands Reference

### List Sessions

```bash
python regenerate.py --list
```

Shows all sessions with status.

### Interactive Mode

```bash
python regenerate.py
# or
python regenerate.py --interactive
```

Menu-driven interface.

### Regenerate Specific Session

```bash
# Basic regeneration (only missing videos)
python regenerate.py --session session_20250208_002238

# With new shot length
python regenerate.py --session session_20250208_002238 --length 10

# Force regenerate all
python regenerate.py --session session_20250208_002238 --force

# Combine options
python regenerate.py --session session_20250208_002238 --length 8 --force
```

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--interactive` | `-i` | Interactive mode with menus |
| `--session ID` | `-s ID` | Session ID to regenerate |
| `--length SEC` | `-l SEC` | New shot length in seconds |
| `--force` | `-f` | Regenerate all videos |
| `--list` | | List all sessions |
| `--help` | `-h` | Show help message |

## Examples

### Example 1: Make Videos Longer

```bash
# Current: 5s shots, 35 seconds total
# Want: 10s shots, 70 seconds total

python regenerate.py --session session_20250208_002238 --length 10
```

### Example 2: Re-render Only Failed Videos

```bash
# Session has 3 failed videos out of 7
# Only regenerate the 3 failed ones

python regenerate.py --session session_20250208_002238
```

### Example 3: Complete Re-render

```bash
# Want to re-render all videos with new workflow

python regenerate.py --session session_20250208_002238 --force
```

### Example 4: Change Length + Re-render All

```bash
# Change to 8-second shots and re-render everything

python regenerate.py --session session_20250208_002238 --length 8 --force
```

## What Gets Updated

### Session Metadata

When you regenerate videos, the session is updated:

```json
{
  "session_id": "session_20250208_002238",
  "video_config": {
    "shot_length": 10.0,  // Updated if changed
    "fps": 24
  },
  "shots": [
    {
      "index": 1,
      "video_rendered": true  // Marked as rendered
    },
    ...
  ],
  "stats": {
    "videos_rendered": 7  // Updated count
  }
}
```

### Video Files

Videos are saved by ComfyUI to its output directory (typically `ComfyUI/output/`).

The original videos are **not automatically deleted** - you'll need to manually remove them if desired.

## Workflow

### Regeneration Process

```
1. Load session metadata
2. Load shots data
3. Determine shot length to use
4. Check which shots have images
5. Determine which videos to render:
   • If --force: all shots
   • If not --force: only unrendered shots
6. Load workflow with video length
7. Submit to ComfyUI
8. Wait for completion
9. Update session metadata
```

### Image Reuse

**Key benefit:** Existing images are reused!

```
Session:
  ├─ Images (already generated)
  │   ├─ shot_001.png ✓
  │   ├─ shot_002.png ✓
  │   └─ ...
  └─ Videos (to be regenerated)
      ├─ shot_001.mp4 ← Re-rendered
      ├─ shot_002.mp4 ← Re-rendered
      └─ ...
```

No need to regenerate images (saves time and money)!

## Cost & Time

### Cost

**No additional API costs!** Images are already generated.

Only ComfyUI rendering time (free, local).

### Time

```
Time = (Number of videos) × (Render time per video)

Example (5-second shots on RTX 4090):
  6 videos × ~2 minutes = ~12 minutes total

Example (10-second shots):
  6 videos × ~4 minutes = ~24 minutes total
```

## Troubleshooting

### "Session not found"

```bash
# List sessions first to get correct ID
python regenerate.py --list
```

### "No shots with images found"

The session doesn't have generated images. You need to generate images first:

```bash
python core/main.py
```

### "ComfyUI not responding"

Make sure ComfyUI is running:
```bash
# Check if ComfyUI is accessible
curl http://127.0.0.1:8188/system_stats
```

### "Workflow error"

Make sure `WORKFLOW_PATH` in `config.py` points to a valid workflow file.

### "Videos are wrong length"

Check that `WAN_VIDEO_NODE_ID` in `config.py` matches your workflow.

## Advanced Usage

### Batch Regenerate Multiple Sessions

```bash
# Regenerate all sessions with 10-second shots
for session in session_20250207_* session_20250208_*; do
    python regenerate.py --session "$session" --length 10
done
```

### Preset Lengths

```bash
# Short: 3 seconds each
python regenerate.py --session session_XXX --length 3

# Default: 5 seconds each
python regenerate.py --session session_XXX --length 5

# Medium: 8 seconds each
python regenerate.py --session session_XXX --length 8

# Long: 10 seconds each
python regenerate.py --session session_XXX --length 10

# Very long: 15 seconds each
python regenerate.py --session session_XXX --length 15
```

### Quality Comparison

```bash
# Render same session with different lengths
python regenerate.py --session session_XXX --length 5
# Compare...

# Then try longer
python regenerate.py --session session_XXX --length 10 --force
# Compare...
```

## Best Practices

### When to Use --force

✅ **Use --force when:**
- Changed ComfyUI workflow
- Updated ComfyUI/models
- Want to re-render with better settings
- Previous renders had quality issues

❌ **Don't use --force when:**
- Only need missing videos
- Want to save time
- Current renders are good

### When to Change Length

✅ **Change length when:**
- Original videos too short/long
- Want different pacing
- Targeting different platform (e.g., 60s for YouTube Shorts)
- Creating multiple versions

### Workflow

1. **List sessions** → Find the right one
2. **Check current settings** → Note current shot length
3. **Decide on changes** → New length? Force re-render?
4. **Run regeneration** → Use appropriate command
5. **Verify results** → Check ComfyUI output

## Summary

✅ **Re-render Videos** - Without regenerating images
✅ **Change Length** - Adjust video duration
✅ **Fix Failures** - Re-render only what's needed
✅ **Try New Settings** - Experiment with workflows
✅ **Save Time** - Reuse existing images
✅ **No Extra Cost** - Free ComfyUI rendering

**Video regeneration gives you flexibility without wasting work!**
