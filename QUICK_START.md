# Quick Start Guide

## Before You Begin

Make sure you have:
1. Gemini API key from https://ai.google.dev/
2. ComfyUI installed with Wan 2.2 workflow
3. Python 3.10+ installed

## 5-Minute Setup

### Step 1: Install Dependencies
```bash
cd C:\AI\ai_video_factory
pip install -r requirements.txt
```

### Step 2: Configure API Key
Edit `config.py`, line 8:
```python
GEMINI_API_KEY = "your-actual-api-key-here"  # Paste your key here
```

### Step 3: Find Your Node IDs
1. Open ComfyUI
2. Load your Wan 2.2 workflow
3. Find the **LoadImage** node (will receive pre-generated images)
4. Right-click it → "Node ID for Save"
5. Update `config.py` line 23:
```python
LOAD_IMAGE_NODE_ID = "10"  # Change "10" to your actual node ID
```

### Step 4: Add Video Idea
Edit or create `input/video_idea.txt`:
```
A futuristic city at sunset with flying cars
```

### Step 5: Test Setup
```bash
python test_setup.py
```

### Step 6: Run Pipeline
```bash
python core/main.py
```

**You'll be asked for video length:**
- Enter total length (e.g., `60` for 1 minute) or press Enter
- Enter shot length (e.g., `5` seconds) or press Enter for default
- System calculates shots needed automatically!

## What Happens

1. **Story Generation** - Gemini creates a cinematic story (auto-saved)
2. **Shot Planning** - Breaks story into individual shots (auto-saved)
3. **Image Generation** - Creates image for each shot (~10-30 seconds each)
4. **Video Rendering** - Sends images to ComfyUI for animation

**All progress is automatically saved!** If the system crashes, just run again and it will ask if you want to continue.

## Files Generated

Each video generation creates a session:
```
output/sessions/session_YYYYMMDD_HHMMSS/
├── session_YYYYMMDD_HHMMSS_meta.json  # Progress tracking
├── story.json                          # Generated story
├── shots.json                          # All shot prompts
└── images/
    ├── shot_001.png
    ├── shot_002.png
    └── ...
```

## Crash Recovery

If the system stops or crashes:
```bash
# Just run again - it will detect incomplete session
python core/main.py

# You'll see:
# INCOMPLETE SESSION FOUND
# Do you want to continue this session? (y/n): y

# Type 'y' to continue from where you left off!
```

## View All Sessions

```bash
# List all sessions
python sessions.py list

# View detailed session info
python sessions.py view session_20250208_002238
```

## Cost Estimate

- Text generation: ~$0.001 per request
- Image generation: ~$0.08 per image (2K resolution)
- Example: 10 shots = ~$0.80

## Troubleshooting

**Problem**: "No images generated"
- Check API key is correct
- Verify you have API credits

**Problem**: "LoadImage node error"
- Verify node ID matches your workflow
- Check ComfyUI console for errors

**Problem**: Images not used in video
- Ensure `LOAD_IMAGE_NODE_ID` is correct
- Check workflow has LoadImage node

## Need Help?

- **Detailed Setup**: `README_GEMINI_SETUP.md`
- **Session Management**: `SESSION_GUIDE.md`
- **Troubleshooting**: `SETUP_CHECKLIST.md`
