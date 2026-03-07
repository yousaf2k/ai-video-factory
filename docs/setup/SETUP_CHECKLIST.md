# Setup Checklist - AI Film Studio Gemini Integration

Use this checklist to verify your setup is complete and ready to run.

## ✅ Pre-Setup Checklist

### Prerequisites
- [ ] Python 3.10 or higher installed
- [ ] pip (Python package installer) available
- [ ] Internet connection for API calls
- [ ] ComfyUI installed on your system
- [ ] ComfyUI running at `http://127.0.0.1:8188`

---

## ✅ Installation Steps

### 1. Install Dependencies
```bash
cd C:\AI\ai_video_factory
pip install -r requirements.txt
```

Verify:
- [ ] `google-genai` package installed
- [ ] `requests` package installed
- [ ] `Pillow` package installed

### 2. Get Gemini API Key
- [ ] Go to https://ai.google.dev/
- [ ] Sign in with Google account
- [ ] Click "Get API Key"
- [ ] Copy the API key

### 3. Configure System

Edit `config.py`:

- [ ] Set `GEMINI_API_KEY` to your actual API key (line 8)
- [ ] Verify `GEMINI_TEXT_MODEL = "gemini-2.0-flash"` (line 11)
- [ ] Verify `GEMINI_IMAGE_MODEL = "gemini-3-pro-image-preview"` (line 14)
- [ ] Verify `COMFY_URL = "http://127.0.0.1:8188"` (line 19)

### 4. Configure ComfyUI Workflow

#### Find LoadImage Node ID
- [ ] Open ComfyUI in your browser
- [ ] Load your Wan 2.2 workflow (`workflow/wan22_workflow.json`)
- [ ] Locate the **LoadImage** node (this will receive pre-generated images)
- [ ] Right-click the LoadImage node
- [ ] Select "Node ID for Save"
- [ ] Copy the node ID (e.g., "10")
- [ ] Update `LOAD_IMAGE_NODE_ID` in `config.py` (line 23)

#### Find Motion Prompt Node ID
- [ ] In ComfyUI, locate the node that receives motion_prompt
- [ ] Right-click it → "Node ID for Save"
- [ ] Verify it matches `MOTION_PROMPT_NODE_ID` in `config.py` (line 26)
- [ ] Update if different (default is "7")

#### Verify Workflow Path
- [ ] Check `WORKFLOW_PATH` in `config.py` (line 29)
- [ ] Ensure the file exists at that location
- [ ] Default: `"workflow/wan22_workflow.json"`

### 5. Prepare Input

- [ ] Create `input/video_idea.txt` if it doesn't exist
- [ ] Add your video idea (e.g., "A futuristic city at sunset")
- [ ] Save the file

---

## ✅ Testing Steps

### Run Automated Tests
```bash
python test_setup.py
```

Expected results:
- [ ] ✓ PASS: Imports
- [ ] ✓ PASS: Configuration
- [ ] ✓ PASS: Workflow File
- [ ] ✓ PASS: Input File
- [ ] ✓ PASS: Gemini Text
- [ ] ✓ PASS: Gemini JSON

Optional tests:
- [ ] ✓ PASS: Gemini Image (if you chose to run it)

### Manual Verification

#### Test Gemini Text Generation
```bash
python -c "from core.gemini_engine import ask; print(ask('Say hello'))"
```
- [ ] Should print "hello" or similar

#### Test Image Generation (Optional - costs money)
```bash
python -c "from core.image_generator import generate_image; generate_image('A red circle', 'test.png')"
```
- [ ] Should create `test.png` in output directory

---

## ✅ First Run Verification

### Run Full Pipeline
```bash
python core/main.py
```

Expected console output:
```
STEP 1: Idea
STEP 2: Story
STEP 3: Scene Graph
STEP 4: Shot Planning
STEP 4.5: Image Generation

Generating X images...
[1/X] Generating image for: ...
✓ Generated: output/generated_images/session_XXX/shot_001.png
[2/X] Generating image for: ...
✓ Generated: output/generated_images/session_XXX/shot_002.png
...

Image generation complete. Images saved to: output/generated_images/session_XXX

STEP 5: Rendering X shots
ALL RENDERS COMPLETE
```

Verify:
- [ ] Story generated successfully
- [ ] Shots planned successfully
- [ ] Images generated in `output/generated_images/session_XXX/`
- [ ] Image files exist (shot_001.png, shot_002.png, etc.)
- [ ] Workflows submitted to ComfyUI
- [ ] ComfyUI queue shows jobs
- [ ] Videos rendered successfully

---

## ✅ Output Verification

### Check Generated Images
- [ ] Navigate to `output/generated_images/session_XXX/`
- [ ] Verify all shot images are present
- [ ] Open images to check quality
- [ ] Verify images match the prompts

### Check Rendered Videos
- [ ] Check ComfyUI output directory
- [ ] Verify video files are generated
- [ ] Play videos to check quality
- [ ] Verify motion matches motion_prompt

---

## ✅ Troubleshooting

### If Tests Fail

**Import Error:**
- [ ] Check you're in the correct directory
- [ ] Verify dependencies installed: `pip list`
- [ ] Try: `pip install -r requirements.txt --force-reinstall`

**API Key Error:**
- [ ] Verify `GEMINI_API_KEY` is set in `config.py`
- [ ] Check for extra spaces or quotes
- [ ] Verify key is valid at https://ai.google.dev/

**Node ID Error:**
- [ ] Re-check node IDs in ComfyUI
- [ ] Ensure IDs are strings (e.g., "10" not 10)
- [ ] Verify workflow is loaded in ComfyUI

**Image Generation Failed:**
- [ ] Check API quota/billing
- [ ] Verify internet connection
- [ ] Check `GEMINI_IMAGE_MODEL` is correct
- [ ] Try a simpler prompt

**No Images Rendered:**
- [ ] Check ComfyUI is running
- [ ] Verify `COMFY_URL` is correct
- [ ] Check ComfyUI console for errors
- [ ] Ensure workflow is valid

---

## ✅ Optimization Checklist

### Performance Tuning
- [ ] Adjust `IMAGE_RESOLUTION` if generation is slow
  - "512" = faster, lower quality
  - "1024" = balanced
  - "2048" = slower, higher quality

- [ ] Adjust `IMAGE_ASPECT_RATIO` based on your needs
  - "16:9" = widescreen
  - "9:16" = vertical/mobile
  - "1:1" = square

### Cost Management
- [ ] Monitor API usage at https://ai.google.dev/
- [ ] Start with fewer shots to test
- [ ] Use lower resolution for testing
- [ ] Batch similar prompts if possible

---

## ✅ Production Ready Checklist

Before using for production:
- [ ] All tests passing
- [ ] First run successful
- [ ] Image quality verified
- [ ] Video quality verified
- [ ] Node IDs confirmed correct
- [ ] Cost estimates acceptable
- [ ] Backup workflow saved
- [ ] Documentation read and understood

---

## 🎯 Quick Reference

### Key Files to Edit
- `config.py` - All configuration
- `input/video_idea.txt` - Your video idea
- `workflow/wan22_workflow.json` - ComfyUI template

### Key Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Test setup
python test_setup.py

# Run pipeline
python core/main.py
```

### Important Paths
- Config: `C:\AI\ai_video_factory\config.py`
- Output: `C:\AI\ai_video_factory\output\generated_images\`
- Input: `C:\AI\ai_video_factory\input\video_idea.txt`
- Docs: `C:\AI\ai_video_factory\README_GEMINI_SETUP.md`

---

## 📞 Need Help?

1. **Setup Issues** → See `README_GEMINI_SETUP.md`
2. **Quick Start** → See `QUICK_START.md`
3. **Understanding Flow** → See `WORKFLOW_DIAGRAM.md`
4. **What Changed** → See `IMPLEMENTATION_SUMMARY.md`

---

## ✅ Final Sign-Off

- [ ] I have completed all checklist items
- [ ] All tests are passing
- [ ] I successfully ran my first video
- [ ] I understand how to use the system
- [ ] I know where to find help if needed

**Status:** Ready to create AI films! 🎬

---

*Last Updated: February 7, 2026*
