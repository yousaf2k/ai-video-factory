# ComfyUI Image Generation - Quick Reference

> 📚 [Docs Index](../DOCS_INDEX.md) › Guides › ComfyUI Image Generation - Quick Reference
## Two Modes Available

**Gemini (Default)**
- ✅ Fast, easy
- ✅ ~$0.08 per image
- ✅ Consistent quality
- ❌ Requires internet

**ComfyUI (Free Alternative)**
- ✅ FREE (no API cost)
- ✅ Local generation
- ✅ Many models (SDXL, Flux, etc.)
- ❌ Needs ComfyUI setup
- ❌ Requires powerful GPU

## Quick Start

### Use ComfyUI (Free)

```bash
python core/main.py

# When prompted:
Select mode [1/2]: 2

# If ComfyUI mode selected:
Enter negative prompt (optional): ugly, blurry, low quality

# Rest of pipeline works normally
```

### Set Default to ComfyUI

Edit `config.py`:
```python
IMAGE_GENERATION_MODE = "comfyui"
```

Now every run uses ComfyUI by default.

## Setup Requirements

### 1. ComfyUI Running
```bash
# Check ComfyUI is accessible
curl http://127.0.0.1:8188/system_stats
```

### 2. Image Workflow
- Create in ComfyUI
- Save as `workflow/image_generation_workflow.json`
- Must have: CLIP Text Encode → KSampler → VAEDecode → SaveImage

### 3. Find Node IDs
Right-click each node → "Node ID for Save"
- IMAGE_TEXT_NODE_ID (positive prompt)
- IMAGE_NEG_TEXT_NODE_ID (negative prompt)
- IMAGE_KSAMPLER_NODE_ID
- IMAGE_VAE_NODE_ID
- IMAGE_SAVE_NODE_ID

### 4. Configure config.py
```python
IMAGE_WORKFLOW_PATH = "workflow/image_generation_workflow.json"
IMAGE_TEXT_NODE_ID = "6"
IMAGE_NEG_TEXT_NODE_ID = "7"
IMAGE_KSAMPLER_NODE_ID = "3"
IMAGE_VAE_NODE_ID = "10"
IMAGE_SAVE_NODE_ID = "11"
```

## Cost Comparison

| Shots | Gemini | ComfyUI |
|-------|--------|---------|
| 12     | $0.96  | $0      |
| 24     | $1.92  | $0      |
| 50     | $4.00  | $0      |

**ComfyUI saves ~$0.08 per image!**

## Recommended Settings

### SDXL (Recommended)
```
Steps: 20-30
CFG: 7-8
Sampler: euler
Resolution: 1024x1024
```

### Flux (Best Quality)
```
Steps: 20-28
CFG: 3.5 (Flux uses lower CFG!)
Sampler: euler
Resolution: 1024x1024
```

### Stable Diffusion 1.5 (Fastest)
```
Steps: 20
CFG: 7-8
Sampler: ddim
Resolution: 768x768
```

## Negative Prompts

### Good All-Purpose
```
ugly, blurry, low quality, distorted, bad anatomy, watermark
```

### For ComfyUI Mode
```
# Enter when prompted:
ugly, blurry, distorted, bad composition, cropped
```

## When to Use Each

### Use Gemini When:
- ✅ Don't have powerful GPU
- ✅ Want fast, easy generation
- ✅ Consistent quality needed
- ✅ Don't want to manage models

### Use ComfyUI When:
- ✅ Want to save money
- ✅ Have powerful GPU
- ✅ Want specific model (Flux, SDXL, etc.)
- ✅ Need offline generation
- ✅ Want full control

## Troubleshooting

**"ComfyUI not connected"**
→ Make sure ComfyUI is running at http://127.0.0.1:8188

**"Workflow not found"**
→ Check IMAGE_WORKFLOW_PATH in config.py
→ Verify file exists in workflow/ folder

**"Node ID error"**
→ Open workflow in ComfyUI
→ Right-click nodes → "Node ID for Save"
→ Update IDs in config.py

**"Slow generation"**
→ Reduce KSampler steps (try 15-20)
→ Use faster sampler (euler, ddim)
→ Lower resolution

## Commands

### Interactive Mode
```bash
python core/main.py
# Choose mode when prompted
```

### Config Default
```python
# In config.py
IMAGE_GENERATION_MODE = "comfyui"  # Set default

# Then run
python core/main.py
```

## Speed Guide

| Model | GPU | Time per Image |
|-------|-----|----------------|
| SD 1.5 | RTX 3060 | ~5 seconds |
| SDXL | RTX 3060 | ~12 seconds |
| Flux | RTX 3060 | ~15 seconds |
| SDXL | RTX 4090 | ~5 seconds |
| Flux | RTX 4090 | ~8 seconds |

## Tips

💡 **Start with default** - Try Gemini first, then experiment with ComfyUI
💡 **Test workflow** - Generate 1 image before full batch
💡 **Monitor ComfyUI** - Watch console for errors during generation
💡 **Save workflows** - Keep backups of working configurations
💡 **Use negative prompts** - Improves quality for ComfyUI mode

## Need More?

See `COMFYUI_IMAGE_GUIDE.md` for complete documentation.

## Summary

```
Gemini = Fast + Easy + Cost
ComfyUI = Free + Control + Quality
Choose what works for you!
```

---
**Related docs:** [Workflow Guide](WORKFLOW_GUIDE.md) · [Configuration Guide](../getting-started/CONFIGURATION.md) · [Camera LoRA Guide](CAMERA_LORA_GUIDE.md) · [API Reference](../reference/API_REFERENCE.md) · [📚 Index](../DOCS_INDEX.md)
