# ComfyUI Image Generation - Setup Checklist

## Quick Checklist for Using ComfyUI for Images

### Prerequisites

- [ ] ComfyUI installed and running
- [ ] ComfyUI accessible at `http://127.0.0.1:8188`
- [ ] Text-to-image workflow created
- [ ] Workflow saved to `workflow/` folder

### Step 1: Create Image Generation Workflow

- [ ] Open ComfyUI
- [ ] Create text-to-image workflow with:
  - [ ] **CheckpointLoader** - Load your model (SDXL, Flux, etc.)
  - [ ] **CLIP Text Encode** - Positive prompt node
  - [ ] **CLIP Text Encode** - Negative prompt node
  - [ ] **KSampler** - Sampler node
  - [ ] **VAEDecode** - Decode node
  - [ ] **SaveImage** - Save output image

### Step 2: Connect the Workflow

```
CheckpointLoader → CLIP Text Encode (positive) ─┐
                 └→ CLIP Text Encode (negative) ──┘
                                                    ↓
                                              KSampler
                                                    ↓
                                              VAEDecode
                                                    ↓
                                              SaveImage
```

### Step 3: Save the Workflow

- [ ] Click "Save" in ComfyUI
- [ ] Name it `image_generation_workflow.json`
- [ ] Save to `workflow/` folder

### Step 4: Find Node IDs

For each node, right-click → "Node ID for Save":

- [ ] **IMAGE_TEXT_NODE_ID** - Get ID from CLIP Text Encode (positive)
- [ ] **IMAGE_NEG_TEXT_NODE_ID** - Get ID from CLIP Text Encode (negative)
- [ ] **IMAGE_KSAMPLER_NODE_ID** - Get ID from KSampler
- [ ] **IMAGE_VAE_NODE_ID** - Get ID from VAEDecode
- [ ] **IMAGE_SAVE_NODE_ID** - Get ID from SaveImage

### Step 5: Configure in config.py

Edit `config.py`:

```python
# Image generation mode
IMAGE_GENERATION_MODE = "comfyui"  # Change to "comfyui"

# ComfyUI workflow path
IMAGE_WORKFLOW_PATH = "workflow/image_generation_workflow.json"

# Node IDs - update these with YOUR node IDs!
IMAGE_TEXT_NODE_ID = "6"        # CLIP Text Encode (positive)
IMAGE_NEG_TEXT_NODE_ID = "7"    # CLIP Text Encode (negative)
IMAGE_KSAMPLER_NODE_ID = "3"    # KSampler
IMAGE_VAE_NODE_ID = "10"        # VAEDecode
IMAGE_SAVE_NODE_ID = "11"       # SaveImage
```

### Step 6: Verify ComfyUI Connection

```bash
# Test ComfyUI is accessible
curl http://127.0.0.1:8188/system_stats

# Should return JSON with system info
```

### Step 7: Test Image Generation

```bash
python core/main.py

# Select mode: 2 (ComfyUI)
# Enter negative prompt if desired
# Generate 1 shot to test
```

---

## Troubleshooting

### "Module not found"

```bash
# Check file exists
ls core/comfyui_image_generator.py
```

### "ComfyUI connection error"

- [ ] ComfyUI is running
- [ ] URL is correct: `http://127.0.0.1:8188`
- [ ] No firewall blocking connection

### "Workflow not found"

- [ ] File exists: `workflow/image_generation_workflow.json`
- [ ] Path in config.py is correct

### "Node ID error"

- [ ] Open workflow in ComfyUI
- [ ] Right-click each node → "Node ID for Save"
- [ ] Update config.py with correct IDs

### "Images not generating"

- [ ] Check ComfyUI console for errors
- [ ] Verify workflow is valid (test in ComfyUI)
- [ ] Check node IDs are correct

---

## Recommended Settings

### SDXL (Recommended Balance)

```
Model: SDXL Base 1.0
Resolution: 1024x1024
Steps: 25
CFG: 7.5
Sampler: euler
Scheduler: normal
```

### Flux (Best Quality)

```
Model: Flux.1-dev
Resolution: 1024x1024
Steps: 24
CFG: 3.5 (Flux uses lower!)
Sampler: euler
Scheduler: simple
```

### Stable Diffusion 1.5 (Fastest)

```
Model: SD 1.5
Resolution: 768x768
Steps: 20
CFG: 7.5
Sampler: ddim
Scheduler: normal
```

---

## Quick Reference

### Enable ComfyUI Mode

**Option 1: Interactive**
```bash
python core/main.py
# Choose: 2 (ComfyUI)
```

**Option 2: Set Default**
```python
# In config.py
IMAGE_GENERATION_MODE = "comfyui"
```

### Good Negative Prompts

```
ugly, blurry, low quality, distorted, deformed, bad anatomy, bad proportions, duplicate, watermark, signature, text
```

### Cost

| Mode | Cost |
|------|------|
| Gemini | ~$0.08 per image |
| ComfyUI | FREE |

---

## Need Help?

- **Complete Guide:** `COMFYUI_IMAGE_GUIDE.md`
- **Quick Reference:** `COMFYUI_IMAGE_QUICKREF.md`
- **Troubleshooting:** Check ComfyUI console for errors
