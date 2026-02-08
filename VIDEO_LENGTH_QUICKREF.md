# Video Length Quick Reference

## Prompts You'll See

When running `python core/main.py`:

```
==================================================================
VIDEO CONFIGURATION
==================================================================

Enter total video length in seconds (or press Enter for default based on story):
```

## Quick Examples

### "I want a 1-minute video"
```
Enter total video length: 60
Enter length per shot: 5
→ Result: 12 shots × 5s = 60 seconds
```

### "I want a 30-second video"
```
Enter total video length: 30
Enter length per shot: 5
→ Result: 6 shots × 5s = 30 seconds
```

### "Let the story decide"
```
Enter total video length: [press Enter]
Enter length per shot: 5
→ Result: Story determines shot count (usually 5-10 shots)
```

### "I want 10-second shots"
```
Enter total video length: [press Enter]
Enter length per shot: 10
→ Result: Each shot is 10 seconds
```

## Shot Length Guide

| Shot Length | Best For | Shots/Minute |
|-------------|----------|--------------|
| 3 seconds   | Trailers, fast cuts | 20 shots |
| 5 seconds   | Short videos (default) | 12 shots |
| 8 seconds   | Medium pace | 7.5 shots |
| 10 seconds  | Long, cinematic | 6 shots |

## Cost Calculator

```
Total Cost = Number of Shots × $0.08

Examples:
  6 shots  × $0.08 = $0.48
  12 shots × $0.08 = $0.96
  24 shots × $0.96 = $1.92
```

## Configuration File

Edit `config.py` to change defaults:

```python
DEFAULT_SHOT_LENGTH = 5.0  # Seconds per shot
VIDEO_FPS = 24            # Framerate
TARGET_VIDEO_LENGTH = None # Or set to 60.0 for 60 seconds
```

## Pro Tips

💡 **Start with default** - Press Enter twice for automatic settings
💡 **Shorter shots** = More dynamic, more images needed
💡 **Longer shots** = More cinematic, faster to render
💡 **Check session** - View saved settings: `python sessions.py view <id>`

## Need More Details?

See `VIDEO_LENGTH_GUIDE.md` for complete documentation.
