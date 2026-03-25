# Visual Guide: Building IP-Adapter Workflows in ComfyUI

This step-by-step guide shows you how to build the IP-Adapter workflows manually in ComfyUI.

## Prerequisites

Before starting, ensure you have:
- ✅ ComfyUI installed and running
- ✅ Flux model downloaded (flux1-dev.sft)
- ✅ CLIP models (clip_l.safetensors, t5xxl_fp16.safetensors)
- ✅ VAE model (ae.safetensors)
- ✅ IP-Adapter Plus node installed
- ✅ IP-Adapter model for Flux

## Workflow 1: flux_ipadapter_then (Building from Scratch)

### Step 1: Open ComfyUI
1. Navigate to `http://127.0.0.1:8188`
2. You should see an empty canvas

### Step 2: Add LoadImage Node (Node ID: 1)
1. Right-click canvas → Add Node → image → LoadImage
2. Position: Left side (x: 50, y: 100)
3. **Important**: Note the node ID (should show as "1" or similar)
4. Upload a test THEN reference photo

```
┌─────────────────┐
│   LoadImage     │
│                 │
│  [upload img]   │
└─────────────────┘
```

### Step 3: Add UNETLoader (Node ID: 2)
1. Right-click → Add Node → loaders → UNETLoader
2. Position: Below LoadImage (x: 400, y: 100)
3. Select your Flux model:
   - unet_name: `flux1-dev.sft`
   - weight_dtype: `fp8_e4m3fn`

```
┌─────────────────┐
│   UNETLoader    │
│                 │
│ Model: flux1    │
│ Dtype: fp8_e4m3  │
└─────────────────┘
```

### Step 4: Add DualCLIPLoader (Node ID: 3)
1. Right-click → Add Node → loaders → DualCLIPLoader
2. Position: Below UNETLoader (x: 400, y: 250)
3. Configure:
   - clip_name1: `clip_l.safetensors`
   - clip_name2: `t5xxl_fp16.safetensors`
   - type: `flux`

```
┌─────────────────┐
│  DualCLIPLoader │
│                 │
│ CLIP1: clip_l   │
│ CLIP2: t5xxl    │
│ Type: flux      │
└─────────────────┘
```

### Step 5: Add IPAdapter Node (Node ID: 5) ⭐ KEY NODE
1. Right-click → Add Node → ipadapter → IPAdapter
2. Position: Right side (x: 800, y: 100)
3. Configure:
   - weight: `0.7` (adjustable 0.5-0.9)
   - ipadapter_file: Select your IP-Adapter model

```
┌─────────────────┐
│    IPAdapter    │
│                 │
│ Weight: 0.7     │
│ Model: ipadapter│
└─────────────────┘
```

### Step 6: Connect Model to IPAdapter
1. Drag from UNETLoader.MODEL output
2. Drop on IPAdapter.model input
3. Drag from LoadImage.IMAGE output
4. Drop on IPAdapter.image input
5. Drag from DualCLIPLoader.CLIP output (second one, slot 1)
6. Drop on IPAdapter.clip input

```
UNETLoader.MODEL → IPAdapter.model
LoadImage.IMAGE → IPAdapter.image
DualCLIPLoader.CLIP[1] → IPAdapter.clip
```

### Step 7: Add CLIPTextEncode (Node ID: 6)
1. Right-click → Add Node → conditioning → CLIP Text Encode
2. Position: Below IPAdapter (x: 800, y: 400)
3. Enter test prompt: "young version, 20 years ago"
4. Connect: DualCLIPLoader.CLIP → CLIPTextEncode.clip

```
┌─────────────────┐
│  CLIPTextEncode │
│                 │
│ "young version, │
│  20 years ago"  │
└─────────────────┘
```

### Step 8: Add EmptyFlux2LatentImage (Node ID: 10)
1. Right-click → Add Node → latent → Empty Flux Latent Image
2. Position: Below CLIPTextEncode (x: 800, y: 650)
3. Configure:
   - width: `1344`
   - height: `768`
   - batch_size: `1`

```
┌─────────────────┐
│EmptyFlux2Latent │
│                 │
│ W: 1344 H: 768  │
└─────────────────┘
```

### Step 9: Add SamplerCustomAdvanced (Node ID: 13)
1. Right-click → Add Node → sampling → Sampler Custom Advanced
2. Position: Right side (x: 1250, y: 100)
3. Configure:
   - sampler: `euler`
   - scheduler: `sgm_uniform`
   - steps: `20`

Connect:
- IPAdapter.MODEL → SamplerCustomAdvanced.model
- CLIPTextEncode.CONDITIONING → SamplerCustomAdvanced.positive
- EmptyFlux2LatentImage.LATENT → SamplerCustomAdvanced.latent_image

```
┌─────────────────┐
│SamplerCustomAdv │
│                 │
│ Sampler: euler  │
│ Steps: 20       │
└─────────────────┘
```

### Step 10: Add VAELoader (Node ID: 14)
1. Right-click → Add Node → loaders → VAE Loader
2. Position: Left side (x: 400, y: 400)
3. Select: `ae.safetensors`

### Step 11: Add VAEDecode (Node ID: 8)
1. Right-click → Add Node → latent → VAE Decode
2. Position: Below Sampler (x: 1250, y: 400)
3. Connect:
   - SamplerCustomAdvanced.LATENT → VAEDecode.samples
   - VAELoader.VAE → VAEDecode.vae

### Step 12: Add SaveImage (Node ID: 9)
1. Right-click → Add Node → image → Save Image
2. Position: Right side (x: 1500, y: 400)
3. filename_prefix: `then_character`
4. Connect: VAEDecode.IMAGE → SaveImage.images

### Step 13: Test the Workflow
1. Click "Queue Prompt" (bottom right)
2. Wait for generation
3. Check output in ComfyUI output folder
4. Verify facial features match reference

### Step 14: Export as API Format
1. Click "Save" button (top right)
2. Select "API Format"
3. Save as `flux_ipadapter_then_api.json`
4. **Important**: Replace the original file with API version

## Workflow 2: flux_ipadapter_now

Repeat the exact same steps as Workflow 1, with only these changes:

1. **Node ID 1 (LoadImage)**: Upload NOW reference photo instead
2. **Node ID 9 (SaveImage)**: Change filename_prefix to `now_character`
3. **Node ID 6 (CLIPTextEncode)**: Change prompt to "current version, present day"

That's it! The structure is identical, only the content changes.

## Workflow 3: flux_background (Simpler - No IP-Adapter)

### Steps 1-3: Same as above
Add UNETLoader, DualCLIPLoader, LoadImage

**Skip IPAdapter node!** We don't need it for backgrounds.

### Step 4: Connect Model Directly
```
UNETLoader.MODEL → (will connect to Sampler later)
```

### Step 5: Add CLIPTextEncode (Node ID: 6)
- Position: x: 450, y: 100
- Prompt: "movie set background, cinematic lighting"
- Connect: DualCLIPLoader.CLIP → CLIPTextEncode.clip

### Step 6: Add EmptyFlux2LatentImage (Node ID: 10)
- Position: x: 450, y: 350
- Same dimensions as before

### Step 7: Add SamplerCustomAdvanced (Node ID: 13)
- Position: x: 900, y: 100
- Connect:
  - UNETLoader.MODEL → SamplerCustomAdvanced.model (direct, no IPAdapter!)
  - CLIPTextEncode.CONDITIONING → SamplerCustomAdvanced.positive
  - EmptyFlux2LatentImage.LATENT → SamplerCustomAdvanced.latent_image

### Step 8: Add VAELoader, VAEDecode, SaveImage
- Same positions and connections as before
- SaveImage filename_prefix: `scene_background`

## Visual Workflow Diagrams

### flux_ipadapter_then/now Structure

```
┌──────────┐
│LoadImage │◄──── Upload reference photo
└────┬─────┘
     │ IMAGE
     ↓
┌─────────────┐     ┌──────────────┐
│ IPAdapter   │◄────│ UNETLoader   │◄── Flux model
└──────┬──────┘     └──────────────┘
       │ MODEL
       ↓
┌──────────────────┐
│SamplerCustomAdv  │◄─── EmptyFlux2LatentImage (dimensions)
└──────────┬───────┘
           │ LATENT
           ↓
┌──────────┐
│ VAEDecode│◄─── VAE Loader
└────┬─────┘
     │ IMAGE
     ↓
┌──────────┐
│ SaveImage│
└──────────┘

Side connections:
- DualCLIPLoader.CLIP → IPAdapter.clip
- DualCLIPLoader.CLIP → CLIPTextEncode.clip → Sampler.positive
```

### flux_background Structure

```
┌──────────────┐
│ UNETLoader   │◄── Flux model
└──────┬───────┘
       │ MODEL
       ↓
┌──────────────────┐
│SamplerCustomAdv  │◄─── EmptyFlux2LatentImage (dimensions)
└──────────┬───────┘
           │ LATENT
           ↓
┌──────────┐
│ VAEDecode│◄─── VAE Loader
└────┬─────┘
     │ IMAGE
     ↓
┌──────────┐
│ SaveImage│
└──────────┘

Side connections:
- DualCLIPLoader.CLIP → CLIPTextEncode.clip → Sampler.positive
```

## Node Position Reference (for consistency)

| Node | X Position | Y Position | THEN | NOW | BG |
|------|-----------|------------|------|-----|-----|
| LoadImage | 50 | 100 | ✅ | ✅ | ❌ |
| UNETLoader | 400 | 100 | ✅ | ✅ | ✅ |
| DualCLIPLoader | 400 | 250 | ✅ | ✅ | ✅ |
| IPAdapter | 800 | 100 | ✅ | ✅ | ❌ |
| CLIPTextEncode | 800 | 400 | ✅ | ✅ | ✅ |
| EmptyFlux2LatentImage | 800 | 650 | ✅ | ✅ | ✅ |
| SamplerCustomAdvanced | 1250 | 100 | ✅ | ✅ | ✅ |
| VAELoader | 400 | 400 | ✅ | ✅ | ✅ |
| VAEDecode | 1250 | 400 | ✅ | ✅ | ✅ |
| SaveImage | 1500 | 400 | ✅ | ✅ | ✅ |

## Tips & Tricks

### Tip 1: Organize Your Canvas
- Keep related nodes grouped together
- Use consistent positions across workflows
- Leave space for connections

### Tip 2: Label Your Workflows
- Add a "Primitive Node" with text label
- Position at top left of canvas
- Example: "THEN Character Generator (IP-Adapter)"

### Tip 3: Test Incrementally
1. Test model loading first (UNET → Sampler → VAE → Save)
2. Add CLIPTextEncode
3. Add IPAdapter last
4. This makes debugging easier

### Tip 4: Save Multiple Versions
- Save working versions with suffixes
- Example: `flux_ipadapter_then_v1_working.json`
- Keep last known good version

### Tip 5: Use Queue Prompt for Testing
- Start with low steps (10) for fast testing
- Increase to 20-30 for final quality
- Use fixed seed for reproducibility

## Common Building Mistakes

### Mistake 1: Wrong CLIP Output
❌ **Wrong**: Connecting first CLIP output (slot 0) to IPAdapter
✅ **Right**: Connecting second CLIP output (slot 1) to IPAdapter

### Mistake 2: Forgetting Dimensions
❌ **Wrong**: Leaving default dimensions in EmptyFlux2LatentImage
✅ **Right**: Setting width/height to match your aspect ratio

### Mistake 3: Incorrect Node IDs
❌ **Wrong**: Accepting auto-assigned node IDs
✅ **Right**: Ensuring node IDs match config.py (use Save/Load to reassign)

### Mistake 4: Not Exporting API Format
❌ **Wrong**: Saving in UI format (default)
✅ **Right**: Exporting as API format for backend use

## Validation Checklist

After building each workflow, verify:

- [ ] All nodes connected (no dangling inputs)
- [ ] Node IDs match config.py requirements
- [ ] Model paths point to actual files
- [ ] IP-Adapter weight set to 0.7
- [ ] Dimensions correct (1344×768 for 16:9)
- [ ] Sampler steps set to 20
- [ ] Workflow tests successfully
- [ ] Output quality acceptable
- [ ] Exported as API format
- [ ] File saved in workflow/image/ directory

## Next Steps After Building

1. **Test with real reference photos**
2. **Adjust IP-Adapter weight** for optimal results
3. **Verify backend can load workflows**
4. **Run conversion script** to validate node IDs
5. **Test end-to-end** with the backend

## Getting Help

If you're stuck:
1. Check ComfyUI Reddit for similar workflows
2. Review IP-Adapter Plus documentation
3. Compare with provided template JSON files
4. Use the conversion script to validate

Remember: The workflows are now provided as templates, so you can import them directly into ComfyUI and customize!
