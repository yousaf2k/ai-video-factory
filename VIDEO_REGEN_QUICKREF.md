# Video Regeneration - Quick Reference

## What It Does

Re-render videos from existing sessions WITHOUT regenerating images.

✅ Change video length
✅ Fix failed renders
✅ Try new settings
✅ No extra API cost

## Common Commands

### Interactive Mode (Easiest)
```bash
python regenerate.py
```
Menu-driven. Just follow the prompts.

### List Sessions First
```bash
python regenerate.py --list
```
Shows all sessions with status.

### Change Video Length
```bash
# Make shots longer (10 seconds each)
python regenerate.py --session session_XXX --length 10

# Make shots shorter (3 seconds each)
python regenerate.py --session session_XXX --length 3
```

### Re-render Failed Videos
```bash
# Only renders missing videos
python regenerate.py --session session_XXX
```

### Re-render Everything
```bash
# Re-render all videos (even already rendered)
python regenerate.py --session session_XXX --force
```

### Change Length + Re-render All
```bash
python regenerate.py --session session_XXX --length 8 --force
```

## Quick Examples

### "My videos are too short"
```bash
# Change from 5s to 10s shots
python regenerate.py --session session_XXX --length 10
```

### "Some videos failed"
```bash
# Only render missing ones
python regenerate.py --session session_XXX
```

### "I updated ComfyUI settings"
```bash
# Re-render with new settings
python regenerate.py --session session_XXX --force
```

### "Want both longer and re-render all"
```bash
python regenerate.py --session session_XXX --length 10 --force
```

## Options

| Option | What It Does |
|--------|--------------|
| `--list` | List all sessions |
| `--session ID` | Which session to regenerate |
| `--length SEC` | New shot length (seconds) |
| `--force` | Re-render all videos |
| `--interactive` | Menu-driven mode |

## Scenarios

| Scenario | Command |
|----------|---------|
| Change length | `--length <seconds>` |
| Fix failed | (no extra flags needed) |
| New settings | `--force` |
| Everything | `--length <sec> --force` |

## What Happens

1. Loads session data
2. Uses existing images (saves money!)
3. Loads workflow with video length
4. Submits to ComfyUI
5. Updates session metadata

## Cost

**FREE** - No API costs!
Images already generated, only ComfyUI rendering (local).

## Time

Depends on:
- Number of videos
- Shot length (longer = more time)
- Your GPU speed

Typical: 2-4 minutes per 5-second shot on RTX 4090.

## Need More?

See `VIDEO_REGENERATION_GUIDE.md` for complete documentation.
