# Session Management Guide

## Overview

The AI Film Studio now includes **crash recovery and session management**. All outputs (story, shots, images) are automatically saved, and you can continue interrupted generations.

## Features

✅ **Automatic Progress Saving** - Every step is saved in real-time
✅ **Crash Recovery** - Resume from where you left off
✅ **Session History** - Track all your video generations
✅ **Output Preservation** - Story, prompts, and images are stored
✅ **Smart Continuation** - Skip completed shots on resume

## Session Structure

Each session creates a directory with all outputs:

```
output/sessions/session_YYYYMMDD_HHMMSS/
├── session_YYYYMMDD_HHMMSS_meta.json    # Session metadata & progress
├── story.json                            # Generated story
├── shots.json                            # All shot data (prompts)
└── images/                               # Generated images
    ├── shot_001.png
    ├── shot_002.png
    └── ...
```

## Usage

### Starting a New Video

Just run the pipeline normally:

```bash
python core/main.py
```

A new session is automatically created and tracked.

### Crash Recovery

If the system crashes or stops, just run again:

```bash
python core/main.py
```

You'll see:

```
==================================================================
INCOMPLETE SESSION FOUND
==================================================================
Session ID: session_20250208_002238
Started: 2025-02-08T00:22:38.123456
Idea: A documentary about the Indus Valley Civilization...

Progress:
  Total shots: 7
  Images generated: 4
  Videos rendered: 2

Shot Status:
  [DONE] Shot 1: Sweeping aerial view...
  [DONE] Shot 2: Animated map...
  [IMG]  Shot 3: Detailed CGI recreation...
  [TODO] Shot 4: Close-ups of artifacts...
  ...
==================================================================

Do you want to continue this session? (y/n):
```

- Type `y` to continue from where you left off
- Type `n` to start a new session

### Viewing Sessions

List all sessions:

```bash
python sessions.py list
```

Output:
```
================================================================================
AI FILM STUDIO - SESSIONS
================================================================================

✓ COMPLETE | session_20250207_143000
  Idea: A futuristic city at sunset with flying cars...
  Started: 2025-02-07T14:30:00
  Progress: 7/7 images, 7 videos

⏳ IN PROGRESS | session_20250208_002238
  Idea: A documentary about the Indus Valley Civilization...
  Started: 2025-02-08T00:22:38
  Progress: 4/7 images, 2 videos

================================================================================
```

View detailed session info:

```bash
python sessions.py view session_20250208_002238
```

## Session Files Explained

### metadata file (`session_XXX_meta.json`)

Contains:
- Session ID and timestamp
- Original idea
- Start/completion times
- Step completion status
- Shot details with prompts and progress
- Statistics

Example:
```json
{
  "session_id": "session_20250208_002238",
  "timestamp": "20250208_002238",
  "idea": "A documentary about the Indus Valley Civilization...",
  "started_at": "2025-02-08T00:22:38.123456",
  "completed": false,
  "steps": {
    "story": true,
    "scene_graph": true,
    "shots": true,
    "images": false,
    "videos": false
  },
  "shots": [
    {
      "index": 1,
      "image_prompt": "Sweeping aerial view...",
      "motion_prompt": "slow camera pan...",
      "camera": "slow pan",
      "image_generated": true,
      "image_path": "output/sessions/session_20250208_002238/images/shot_001.png",
      "video_rendered": true
    },
    ...
  ],
  "stats": {
    "total_shots": 7,
    "images_generated": 4,
    "videos_rendered": 2
  }
}
```

### story.json

The complete generated story in JSON format:

```json
{
  "title": "Indus Valley: Cradle of Civilization",
  "style": "ultra cinematic documentary",
  "scenes": [...]
}
```

### shots.json

All shot data with prompts:

```json
[
  {
    "index": 1,
    "image_prompt": "Sweeping aerial view of the Indus River valley...",
    "motion_prompt": "slow, majestic camera pan from left to right",
    "camera": "slow pan",
    "image_path": "images/shot_001.png"
  },
  ...
]
```

## Scenarios

### Scenario 1: System Crashes During Image Generation

1. Run: `python core/main.py`
2. System crashes after generating 3 of 7 images
3. Run again: `python core/main.py`
4. Choose to continue session
5. System generates remaining 4 images
6. Continues to video rendering

### Scenario 2: ComfyUI Runs Out of VRAM Mid-Generation

1. Run: `python core/main.py`
2. ComfyUI stops after 2 videos
3. Fix VRAM issue (close other apps)
4. Run again: `python core/main.py`
5. Continue session - skips completed shots
6. Renders remaining 5 videos

### Scenario 3: Want to Reuse Prompts from Previous Session

1. View session: `python sessions.py view session_XXX`
2. Copy prompts from `output/sessions/session_XXX/shots.json`
3. Edit as needed
4. Use in new video or share with others

### Scenario 4: Starting Fresh

1. Run: `python core/main.py`
2. When asked to continue, type `n`
3. New session created with new timestamp

## Best Practices

1. **Check Sessions Regularly**: Use `python sessions.py list` to see progress
2. **Backup Important Sessions**: Copy entire session directory to safe location
3. **Review Prompts**: Check `shots.json` to see what prompts were generated
4. **Monitor Disk Space**: Sessions accumulate - clean up old ones periodically

## Troubleshooting

### "Session not found" error

- Check the session ID is correct
- Verify session directory exists in `output/sessions/`

### Images already generated but not marked

- The system checks if files exist before regenerating
- You can manually mark shots complete by editing the metadata file

### Cannot continue session

- If session files are corrupted, you may need to start fresh
- Copy prompts from the old session's `shots.json` to reuse them

## Advanced: Manual Session Management

### Create a custom session from existing data

1. Create session directory structure
2. Create `shots.json` with your prompts
3. Place images in `images/` folder
4. Run pipeline to render videos

### Extract prompts from a session

```bash
# Copy shots JSON
cp output/sessions/session_XXX/shots.json my_shots.json

# View prompts
python -m json.tool my_shots.json | less
```

## Directory Structure

```
C:\AI\ai_video_factory\
├── core\
│   ├── main.py              # Pipeline with session management
│   └── session_manager.py   # Session tracking module
├── output\
│   └── sessions\            # All session data
│       ├── session_20250207_143000\
│       │   ├── session_20250207_143000_meta.json
│       │   ├── story.json
│       │   ├── shots.json
│       │   └── images\
│       │       ├── shot_001.png
│       │       └── ...
│       └── session_20250208_002238\
│           └── ...
└── sessions.py              # Session viewer utility
```

## Summary

The session management system ensures:

✅ **No Lost Work** - Everything is saved in real-time
✅ **Easy Recovery** - One command to continue
✅ **Full History** - Track all your generations
✅ **Reusable Data** - Export prompts, share sessions
✅ **Smart Resuming** - Only does what's needed

**Never lose progress again!**
