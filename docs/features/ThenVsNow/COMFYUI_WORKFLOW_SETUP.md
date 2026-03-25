# ComfyUI Workflow Setup Guide

This guide helps you set up the IP-Adapter workflows for ThenVsNow reference image support.

## Quick Start

### Option 1: Import Pre-Built Workflows (Recommended)

1. **Copy workflow files** to ComfyUI:
   ```bash
   # From your project directory
   cp workflow/image/flux_ipadapter_then.json "E:\ComfyUI\custom_workflows\"
   cp workflow/image/flux_ipadapter_now.json "E:\ComfyUI\custom_workflows\"
   cp workflow/image/flux_background.json "E:\ComfyUI\custom_workflows\"
   ```

2. **Open ComfyUI** and load each workflow

3. **Update model paths** to match your installation:
   - UNETLoader: Change `flux1-dev.sft` to your actual model
   - DualCLIPLoader: Change CLIP/T5 paths if needed
   - VAELoader: Change `ae.safetensors` if needed

4. **Install IP-Adapter** (if not installed):
   - Open ComfyUI Manager
   - Search for "ComfyUI IPAdapter Plus"
   - Click Install

5. **Test each workflow**:
   - Load a reference image
   - Click Queue Prompt
   - Verify output maintains facial features

6. **Export as API format**:
   - Click "Save" → "API Format"
   - Replace the original file with the API version

### Option 2: Build Workflows Manually

See the visual guide below for step-by-step instructions.

## Workflow Structure

### flux_ipadapter_then.json
```
LoadImage (THEN reference) → IPAdapter → Sampler → VAE → Save
                              ↓
                         CLIP Text (THEN prompt)
```

### flux_ipadapter_now.json
```
LoadImage (NOW reference) → IPAdapter → Sampler → VAE → Save
                              ↓
                         CLIP Text (NOW prompt)
```

### flux_background.json
```
CLIP Text (background prompt) → Sampler → VAE → Save
```

## Model Requirements

### Required Models

1. **Flux Model** (UNETLoader)
   - File: `flux1-dev.sft` or similar
   - Location: `ComfyUI/models/unet/`

2. **CLIP Models** (DualCLIPLoader)
   - File: `clip_l.safetensors`
   - File: `t5xxl_fp16.safetensors`
   - Location: `ComfyUI/models/clip/`

3. **VAE Model** (VAELoader)
   - File: `ae.safetensors`
   - Location: `ComfyUI/models/vae/`

4. **IP-Adapter Model** (IPAdapter)
   - File: `ipadapter_flux.safetensors` (or compatible)
   - Location: `ComfyUI/models/ipadapter/`

### Download Models

```bash
# Navigate to ComfyUI models directory
cd "E:\ComfyUI\models"

# Download Flux (from HuggingFace)
# flux1-dev.sft → models/unet/
# ae.safetensors → models/vae/
# clip_l.safetensors → models/clip/
# t5xxl_fp16.safetensors → models/clip/

# Download IP-Adapter for Flux
# ipadapter_flux.safetensors → models/ipadapter/
```

## Customization Guide

### Adjusting IP-Adapter Weight

The IP-Adapter weight controls how much the reference image influences the output:

- **0.5-0.6**: Subtle influence, more creative freedom
- **0.7-0.8**: Balanced (recommended)
- **0.9-1.0**: Strong influence, very faithful to reference

**To change:**
1. Open workflow in ComfyUI
2. Select IPAdapter node (ID: 5)
3. Change `weight` value
4. Save as API format

### Adjusting Image Dimensions

Default: 1344×768 (16:9 aspect ratio)

**To change:**
1. Select EmptyFlux2LatentImage node (ID: 10)
2. Modify width/height values
3. Common ratios:
   - 16:9 → 1344×768
   - 9:16 → 768×1344
   - 1:1 → 1024×1024

### Adjusting Sampling Steps

Default: 20 steps with Euler sampler

**For higher quality** (slower):
- Increase steps to 30-40

**For faster generation** (lower quality):
- Decrease steps to 10-15

**To change:**
1. Select SamplerCustomAdvanced node (ID: 13)
2. Modify `steps` value

## Testing Your Workflows

### Test 1: THEN Workflow

```python
# Test in Python
import requests
import json

# Load workflow
with open('workflow/image/flux_ipadapter_then.json', 'r') as f:
    workflow = json.load(f)

# Submit to ComfyUI
response = requests.post(
    'http://127.0.0.1:8188/prompt',
    json={'prompt': workflow}
)

prompt_id = response.json()['prompt_id']
print(f"THEN test queued: {prompt_id}")
```

### Test 2: NOW Workflow

```python
# Load workflow
with open('workflow/image/flux_ipadapter_now.json', 'r') as f:
    workflow = json.load(f)

# Submit to ComfyUI
response = requests.post(
    'http://127.0.0.1:8188/prompt',
    json={'prompt': workflow}
)

prompt_id = response.json()['prompt_id']
print(f"NOW test queued: {prompt_id}")
```

### Test 3: Background Workflow

```python
# Load workflow
with open('workflow/image/flux_background.json', 'r') as f:
    workflow = json.load(f)

# Submit to ComfyUI
response = requests.post(
    'http://127.0.0.1:8188/prompt',
    json={'prompt': workflow}
)

prompt_id = response.json()['prompt_id']
print(f"Background test queued: {prompt_id}")
```

## Troubleshooting

### Error: "Model not found"

**Solution**: Update model paths in workflow nodes
- Check actual filenames in ComfyUI/models/ directories
- Update UNETLoader, DualCLIPLoader, VAELoader nodes

### Error: "IPAdapter node not found"

**Solution**: Install IP-Adapter Plus
```bash
# Via ComfyUI Manager
# Or manually:
cd E:\ComfyUI\custom_nodes
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus
```

### Generated images don't look like reference

**Solutions**:
1. Increase IP-Adapter weight (try 0.8 or 0.9)
2. Check reference image quality (use clear, well-lit photos)
3. Verify IP-Adapter model is loaded correctly

### Workflow is too slow

**Solutions**:
1. Reduce sampling steps (try 15 instead of 20)
2. Use fp8_e4m3fn quantization (already default)
3. Consider using Flux Dev (smaller than Flux Pro)

### "API format" vs "UI format"

**API format**: Required by backend, uses node IDs as keys
```json
{
  "1": {"class_type": "LoadImage", "inputs": {...}},
  "2": {"class_type": "UNETLoader", "inputs": {...}}
}
```

**UI format**: Used by ComfyUI UI editor, has "nodes" array
```json
{
  "nodes": [
    {"id": 1, "type": "LoadImage", ...},
    {"id": 2, "type": "UNETLoader", ...}
  ]
}
```

**Always export as API format for backend use!**

## Verification Checklist

- [ ] All three workflows imported into ComfyUI
- [ ] Model paths updated to match your installation
- [ ] IP-Adapter Plus node installed
- [ ] THEN workflow generates images with reference
- [ ] NOW workflow generates images with reference
- [ ] Background workflow generates scenes
- [ ] All workflows exported as API format
- [ ] Files located in `workflow/image/` directory
- [ ] Backend can load workflows without errors

## Next Steps

After workflows are set up:

1. **Test with actual reference photos**
2. **Adjust IP-Adapter weights** for optimal results
3. **Integrate with story editor UI**
4. **Run end-to-end test** with complete ThenVsNow project

## API Integration Notes

The backend automatically:
- Injects reference images into LoadImage node (ID: 1)
- Injects prompts into CLIPTextEncode node (ID: 6)
- Sets dimensions in EmptyFlux2LatentImage (ID: 10)
- Uses unique filenames in SaveImage (ID: 9)

Ensure these node IDs match your workflow!

## Support

For issues or questions:
1. Check ComfyUI console for error messages
2. Verify all models are downloaded
3. Check IP-Adapter Plus is latest version
4. Review workflow in ComfyUI UI for connection errors

## Example Node IDs

| Node | THEN Workflow | NOW Workflow | Background Workflow |
|------|--------------|--------------|-------------------|
| LoadImage (ref) | 1 | 1 | N/A |
| UNETLoader | 2 | 2 | 2 |
| DualCLIPLoader | 3 | 3 | 3 |
| IPAdapter | 5 | 5 | N/A |
| CLIPTextEncode | 6 | 6 | 6 |
| EmptyFlux2LatentImage | 10 | 10 | 10 |
| SamplerCustomAdvanced | 13 | 13 | 13 |
| VAELoader | 14 | 14 | 14 |
| VAEDecode | 8 | 8 | 8 |
| SaveImage | 9 | 9 | 9 |

These IDs must match the `config.py` workflow configurations!
