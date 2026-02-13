# ComfyUI Image Generation Guide

## Overview

You can now choose between **TWO image generation methods**:

1. **Gemini** (cloud API) - Fast, easy, ~$0.08 per image
2. **ComfyUI** (local) - FREE, uses your GPU, more control

## Quick Comparison

| Feature | Gemini | ComfyUI |
|---------|--------|---------|
| **Cost** | ~$0.08 per image | FREE |
| **Speed** | Fast (~10-30s) | Depends on GPU |
| **Quality** | Consistent, high | Varies by model |
| **Control** | Prompt only | Full workflow control |
| **Models** | Gemini only | SDXL, Flux, Stable Diffusion, etc. |
| **Internet** | Required | Local only |
| **Setup** | API key only | ComfyUI + workflow |

## How to Use

### Interactive Mode (Easiest)

Run the pipeline:
```bash
python core/main.py
```

When prompted:
```
==================================================================
IMAGE GENERATION MODE
==================================================================

Choose image generation method:
  1. Gemini (cloud API) - Fast, easy, ~$0.08 per image
  2. ComfyUI (local) - Free, uses your GPU, more control

Current default: gemini

Select mode [1/2] (or press Enter for default):
```

### Configuration Mode

Edit `config.py` to set default:
```python
# Image generation mode: "gemini" or "comfyui"
IMAGE_GENERATION_MODE = "comfyui"  # Change default here
```

### Command-Line Options

```bash
# Use config default
python core/main.py

# Will prompt for mode if not set
```

## Setting Up ComfyUI Image Generation

### Step 1: Create Image Generation Workflow

1. Open ComfyUI
2. Create a text-to-image workflow with:
   - CLIP Text Encode (positive prompt)
   - CLIP Text Encode (negative prompt)
   - KSampler
   - VAEDecode
   - SaveImage

3. Connect the nodes properly

### Step 2: Save the Workflow

1. Click "Save" in ComfyUI
2. Save as `image_generation_workflow.json` in the `workflow/` folder

### Step 3: Find Node IDs

For each node, right-click → "Node ID for Save":
- **TEXT_NODE_ID**: CLIP Text Encode (positive prompt)
- **NEG_TEXT_NODE_ID**: CLIP Text Encode (negative prompt)
- **KSAMPLER_NODE_ID**: KSampler
- **VAE_NODE_ID**: VAEDecode
- **SAVE_NODE_ID**: SaveImage

### Step 4: Configure in config.py

```python
# ComfyUI image generation workflow path
IMAGE_WORKFLOW_PATH = "workflow/image_generation_workflow.json"

# Node IDs for image generation workflow
IMAGE_TEXT_NODE_ID = "6"        # CLIPTextEncode (positive)
IMAGE_NEG_TEXT_NODE_ID = "7"    # CLIPTextEncode (negative)
IMAGE_KSAMPLER_NODE_ID = "3"    # KSampler
IMAGE_VAE_NODE_ID = "10"        # VAEDecode
IMAGE_SAVE_NODE_ID = "11"       # SaveImage
```

## Recommended ComfyUI Workflows

### Option 1: SDXL (Recommended)

**Model:** SDXL Base 1.0

**Pros:**
- High quality
- Fast generation
- Good prompt adherence

**KSampler Settings:**
- Steps: 20-30
- CFG Scale: 7-8
- Sampler Name: euler
- Scheduler: normal

**Example Workflow Structure:**
```
CLIP Text Encode (pos) → KSampler → VAEDecode → SaveImage
     ↓                      ↑
CLIP Text Encode (neg) ───────┘
     ↓
CheckpointLoader (SDXL)
```

### Option 2: Flux

**Model:** Flux.1-dev

**Pros:**
- Excellent quality
- Great for portraits
- Good text rendering

**Cons:**
- Slower
- Needs more VRAM

**KSampler Settings:**
- Steps: 20-28
- CFG Scale: 3.5 (Flux is lower!)
- Sampler Name: euler
- Scheduler: simple

### Option 3: Stable Diffusion 1.5

**Model:** SD 1.5

**Pros:**
- Fast
- Many checkpoints available
- Lower VRAM requirement

**Cons:**
- Lower resolution than SDXL
- Requires 512x512 or 768x768

## Usage Examples

### Example 1: Use ComfyUI (Free)

```bash
python core/main.py

# When prompted:
Select mode [1/2]: 2

Enter negative prompt (optional): blurry, low quality, distorted

# Rest of pipeline continues normally
```

### Example 2: Use Gemini (Default)

```bash
python core/main.py

# When prompted:
Select mode [1/2]: [press Enter]
# Uses default (gemini)
```

### Example 3: Change Default in Config

```python
# In config.py
IMAGE_GENERATION_MODE = "comfyui"

# Now every run uses ComfyUI by default
python core/main.py
```

## Negative Prompts

### Good Negative Prompts

**General Purpose:**
```
ugly, blurry, low quality, distorted, deformed, disfigured, bad anatomy, bad proportions, duplicate, watermark, signature, text, logo
```

**Photorealistic:**
```
cartoon, anime, painting, drawing, illustration, low quality, blurry, distorted
```

**Cinematic:**
```
low quality, blurry, noise, grain, artifacts, overexposed, underexposed, amateur, snapshot, phone photo
```

**For ComfyUI Mode:**

When selecting ComfyUI mode, you'll be prompted:
```
Enter negative prompt (optional, press Enter to skip):
```

Enter your negative prompt or press Enter to skip.

## Workflow Examples

### Complete Workflow with ComfyUI Images

```bash
# 1. Set default to ComfyUI (edit config.py)
IMAGE_GENERATION_MODE = "comfyui"

# 2. Run pipeline
python core/main.py

# 3. Select video config
Total length: 60
Shot length: 5

# 4. Generate images (now using ComfyUI)
# → Each image submitted to ComfyUI
# → Downloaded to session folder
# → No API cost!

# 5. Render videos
# → Uses ComfyUI images for Wan 2.2
```

### Hybrid Workflow

```bash
# Generate images with Gemini (fast, paid)
# First run:
IMAGE_GENERATION_MODE = "gemini"
python core/main.py

# Later, regenerate images with ComfyUI (free, local)
# Use regeneration tool to re-render images (coming soon!)
```

## Troubleshooting

### "ComfyUI connection error"

Make sure ComfyUI is running:
```bash
# Check ComfyUI is accessible
curl http://127.0.0.1:8188/system_stats
```

### "Workflow not found"

Check the path in `config.py`:
```python
IMAGE_WORKFLOW_PATH = "workflow/image_generation_workflow.json"
```

Verify the file exists in the workflow folder.

### "Node ID not found"

Open your workflow in ComfyUI and find the correct node IDs:
1. Right-click the node
2. Select "Node ID for Save"
3. Update the corresponding ID in `config.py`

### "Images not generating"

Check:
1. ComfyUI is running
2. Workflow is valid
3. Node IDs are correct
4. ComfyUI console for errors

### "Slow image generation"

Optimize ComfyUI workflow:
- Reduce steps in KSampler
- Use faster sampler (euler, ddim)
- Lower resolution if needed
- Use GPU acceleration if available

## Cost Comparison

### Gemini (Cloud API)

| Shots | Cost |
|-------|------|
| 6      | $0.48 |
| 12     | $0.96 |
| 24     | $1.92 |

### ComfyUI (Local)

| Shots | Cost | Electricity (est.) |
|-------|------|-------------------|
| 6      | $0    | ~$0.01 |
| 12     | $0    | ~$0.02 |
| 24     | $0    | ~$0.04 |

**Savings with ComfyUI:** ~$0.08 per image

## Performance

### Speed Comparison

| Method | Typical Time Per Image |
|--------|----------------------|
| Gemini | 10-30 seconds |
| ComfyUI (SDXL, 20 steps) | 5-15 seconds |
| ComfyUI (Flux, 20 steps) | 10-20 seconds |
| ComfyUI (SD 1.5, 20 steps) | 3-8 seconds |

*Times vary based on hardware and settings*

## Tips

### When to Use Gemini

✅ **Don't have powerful GPU**
✅ **Want consistent quality**
✅ **No time to setup ComfyUI**
✅ **Need fast generation**
✅ **Don't want to manage models**

### When to Use ComfyUI

✅ **Want to save money**
✅ **Have powerful GPU**
✅ **Want full control**
✅ **Have specific model preference**
✅ **Offline environment**

### Best Practices

1. **Test First**: Try with 1-2 shots before full generation
2. **Monitor ComfyUI**: Watch ComfyUI console for errors
3. **Save Workflows**: Keep backups of working workflows
4. **Document Settings**: Note which models/settings work best
5. **Balance Quality/Speed**: Adjust steps based on your needs

## Advanced: Multiple Models

### Switching Between Models

```bash
# For cinematic shots
# Use Flux (slower, better quality)
IMAGE_WORKFLOW_PATH = "workflow/images/flux_workflow.json"
python core/main.py

# For fast preview
# Use SD 1.5 (faster, good enough)
IMAGE_WORKFLOW_PATH = "workflow/images/sd15_workflow.json"
python core/main.py
```

### Custom Workflows per Project

```
├── workflow/image/
|    ├── flux_workflow.json          # Portrait-heavy
|    ├── sdxl_workflow.json          # General purpose
|    ├── sd15_workflow.json          # Fast preview
|    └── realistic_workflow.json     # Photorealistic
├── workflow/video/
|    ├── wan22_workflow.json         # General purpose
|    └── workflow/voice/
└── workflow/voice/
     └── tts_workflow_example.json   # General purpose

```

Update config.py to switch workflows:
```python
IMAGE_WORKFLOW_PATH = "workflow/flux_workflow.json"
```

## Summary

✅ **Dual Mode** - Choose Gemini or ComfyUI
✅ **Interactive** - Easy mode selection at runtime
✅ **Configurable** - Set default in config.py
✅ **Free Option** - ComfyUI generates locally (no API cost)
✅ **Flexible** - Switch anytime, use different models

**You have full control over image generation!**
