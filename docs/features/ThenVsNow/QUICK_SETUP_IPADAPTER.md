# Quick Setup: IP-Adapter Plus Installation

This guide helps you install IP-Adapter Plus to enable reference image support for ThenVsNow.

## Prerequisites

- ComfyUI installed and running
- Internet connection
- ~1GB free disk space for IP-Adapter models

## Step 1: Install IP-Adapter Plus (2 minutes)

### Via ComfyUI Manager (Easiest)

1. **Open ComfyUI**: Navigate to http://127.0.0.1:8188

2. **Open Manager**: Click the "Manager" button (top-right, usually a cube icon)

3. **Install Custom Nodes**:
   - Click "Install Custom Nodes" tab
   - Search for: `IPAdapter Plus`
   - Find: `ComfyUI IPAdapter Plus` by cubiq
   - Click "Install" button

4. **Wait for installation** (shows progress bar)

5. **Restart ComfyUI**:
   - Close ComfyUI window
   - Restart ComfyUI
   - Navigate back to http://127.0.0.1:8188

### Manual Installation (Alternative)

```bash
# Navigate to ComfyUI custom_nodes
cd "E:\ComfyUI\custom_nodes"

# Clone IPAdapter Plus
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus

# Restart ComfyUI
```

## Step 2: Verify Installation

```bash
# Check if IPAdapter node is available
curl -s http://127.0.0.1:8188/object_info > objects.json
python -c "import json; data=json.load(open('objects.json')); nodes=[k for k in data.keys() if 'IPAdapter' == k]; print('IPAdapter node:', 'FOUND' if nodes else 'NOT FOUND')"
```

Expected output: `IPAdapter node: FOUND`

## Step 3: Download IP-Adapter Model (5 minutes)

### Option 1: Via ComfyUI (Recommended)

1. Open ComfyUI Manager
2. Go to "Install Models" tab
3. Search for: `ipadapter_flux`
4. Download and install

### Option 2: Manual Download

1. **Visit HuggingFace**: https://huggingface.co/h94/IP-Adapter

2. **Download for Flux**:
   - Look for: `ipadapter_flux_sd3.safetensors` or similar
   - OR: `ipadapter_flux.safetensors`

3. **Save to**:
   ```
   E:\ComfyUI\models\ipadapter\
   ```

### Common IP-Adapter Models

| Model | Purpose | Size |
|-------|---------|------|
| ipadapter_flux_sd3.safetensors | Flux 1.0 | ~1GB |
| ipadapter_flux.safetensors | Flux Dev | ~1GB |
| ipadapter_plus_face_sd15.safetensors | SD1.5 faces | ~300MB |

**Minimum**: Any Flux-compatible IP-Adapter model

## Step 4: Update Workflows (2 minutes)

### Fix Model Paths

Open each workflow file and update model paths:

**flux_ipadapter_then.json**:
```json
"45": {
  "inputs": {
    "unet_name": "flux1-dev-nvfp4.safetensors",  // Your actual model
    "weight_dtype": "default"
  },
  "class_type": "UNETLoader"
}
```

**OR use CheckpointLoaderSimple** (simpler):
```json
"43": {
  "inputs": {
    "ckpt_name": "flux1-dev-fp8.safetensors"  // Your actual model
  },
  "class_type": "CheckpointLoaderSimple"
}
```

## Step 5: Test IP-Adapter Workflow (3 minutes)

### Simple Test

1. **Open ComfyUI** in browser

2. **Load workflow**:
   - Drag `workflow/image/flux_ipadapter_then.json` into ComfyUI
   - OR copy and paste the JSON

3. **Upload reference photo**:
   - Click LoadImage node
   - Upload any portrait photo

4. **Queue Prompt**:
   - Click "Queue Prompt" button
   - Wait ~30 seconds

5. **Check output**:
   - Navigate to `E:\ComfyUI\Output\`
   - Look for `then_character_00001_.png`

### Expected Results

✅ **Success**: Image generated with facial features from reference
❌ **Error**: Check ComfyUI console for error messages

## Troubleshooting

### Issue: "IPAdapter node not found"
**Solution**: IP-Adapter Plus not installed correctly
- Reinstall via Manager
- Check ComfyUI custom_nodes folder

### Issue: "Model not found"
**Solution**: Update model path in workflow
- Check actual filename in `E:\ComfyUI\models\unet\`
- Update workflow JSON

### Issue: "IP-Adapter model not found"
**Solution**: Download IP-Adapter model
- Place in `E:\ComfyUI\models\ipadapter\`
- Verify filename matches workflow

### Issue: Generated image doesn't look like reference
**Solutions**:
1. Increase IP-Adapter weight to 0.8 or 0.9
2. Use a clearer reference photo
3. Verify IP-Adapter model is Flux-compatible

## Verification Checklist

- [ ] ComfyUI restarted after installation
- [ ] IPAdapter node appears in node list
- [ ] IP-Adapter model downloaded
- [ ] THEN workflow loads without errors
- [ ] NOW workflow loads without errors
- [ ] Test generation works with reference photo
- [ ] Generated image maintains facial features

## Next Steps After Installation

1. **Test THEN workflow** with young reference photo
2. **Test NOW workflow** with current reference photo
3. **Verify facial consistency** in generated images
4. **Integrate with backend** for automated generation
5. **Run end-to-end test** with complete ThenVsNow project

## Model Path Reference

### Your Available Models (from ComfyUI)

**UNET Models** (if using UNETLoader):
- `flux1-dev-fp8.safetensors` (Checkpoint)
- `flux1-schnell-fp8.safetensors` (Checkpoint)
- `flux1-dev-nvfp4.safetensors` (UNET) - may not exist
- Other Wan models (not compatible with Flux workflows)

**Checkpoint Models** (recommended):
- `flux1-dev-fp8.safetensors`
- `flux1-schnell-fp8.safetensors`

**Recommendation**: Use `flux1-dev-fp8.safetensors` with CheckpointLoaderSimple

## Quick Command Reference

```bash
# Check IPAdapter installation
curl -s http://127.0.0.1:8188/object_info | python -c "import json,sys; d=json.load(sys.stdin); print('IPAdapter:', 'FOUND' if 'IPAdapter' in d else 'MISSING')"

# Check available Flux models
curl -s http://127.0.0.1:8188/object_info/CheckpointLoaderSimple | python -c "import json,sys; d=json.load(sys.stdin)['CheckpointLoaderSimple']; models=d['input']['required']['ckpt_name'][0]; [print(m) for m in models if 'flux' in m.lower()]"

# View ComfyUI logs
# (Check console window where ComfyUI is running)

# Open ComfyUI output folder
explorer "E:\ComfyUI\Output"
```

## Support

### Documentation
- IP-Adapter Plus: https://github.com/cubiq/ComfyUI_IPAdapter_plus
- ComfyUI: https://github.com/comfyanonymous/ComfyUI

### Common Issues
1. **Slow installation**: Use Git for manual install
2. **Model download fails**: Use HuggingFace direct download
3. **Workflow won't load**: Check JSON syntax
4. **Out of memory**: Use fp8 quantized models

---

**Estimated Total Time**: 15-20 minutes
**Difficulty**: Easy (ComfyUI Manager) / Medium (Manual)
**Required**: YES (for reference image feature)
