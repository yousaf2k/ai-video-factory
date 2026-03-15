# Creating IP-Adapter Workflows for ThenVsNow

This guide explains how to create the three ComfyUI workflows needed for reference image support in ThenVsNow projects.

## Prerequisites

- ComfyUI installed and running
- Flux model installed
- IP-Adapter installed (ComfyUI-IPAdapter-plus or similar)
- Basic understanding of ComfyUI workflow building

## Workflow 1: flux_ipadapter_then.json

**Purpose**: Generate THEN (young version) character images using IP-Adapter for facial consistency

### Node Configuration

1. **LoadImage (Node ID: 1)** - Reference Image Loader
   - Upload your THEN reference photo
   - Widget: filename = your reference photo

2. **UNETLoader (Node ID: 2)** - Flux Model
   - unet_name: `flux1-dev.sft` or your Flux model
   - weight_dtype: `fp8_e4m3fn` or `fp8_e5m2`

3. **CLIPLoader (Node ID: 3)** - CLIP Model
   - clip_name1: `clip_l.safetensors`
   - clip_name2: `t5xxl_fp16.safetensors` or your T5 model
   - type: `flux`

4. **IP-Adapter (Node ID: 5)** - Facial Consistency
   - weight: `0.7` (adjustable: 0.5-0.9)
   - model: IP-Adapter model for Flux
   - image: Connect from LoadImage (1)
   - model_input: Connect from UNETLoader (2)

5. **CLIPTextEncode (Node ID: 6)** - Positive Prompt
   - text: Your THEN prompt (e.g., "young version, 20 years ago...")
   - clip: Connect from CLIPLoader (3)

6. **SamplerCustomAdvanced (Node ID: 13)** - Sampling
   - sampler: `euler`
   - scheduler: `sgm_uniform`
   - add_noise: `enable`
   - model: Connect from IP-Adapter output (5)
   - positive: Connect from CLIPTextEncode (6)
   - negative: Not used for Flux
   - latent_image: EmptyFlux2LatentImage

7. **EmptyFlux2LatentImage** - Latent Setup
   - width: 1344 (or your desired width)
   - height: 768 (or your desired height)
   - batch_size: 1

8. **VAEDecode (Node ID: 8)** - Decode to Image
   - samples: Connect from SamplerCustomAdvanced (13)
   - vae: Connect from VAELoader

9. **VAELoader** - VAE Model
   - vae_name: `ae.safetensors` or your Flux VAE

10. **SaveImage (Node ID: 9)** - Save Output
    - images: Connect from VAEDecode (8)
    - filename_prefix: `then_character`

### Export Workflow
1. Save workflow as API format
2. Export → API Format
3. Save as `workflow/image/flux_ipadapter_then.json`

## Workflow 2: flux_ipadapter_now.json

**Purpose**: Generate NOW (current version) character images using IP-Adapter

This workflow is nearly identical to flux_ipadapter_then, with the only difference being:
- Use NOW reference photo in LoadImage node
- Use NOW prompt (e.g., "current version, present day...")

### Node Configuration

Copy the exact node configuration from flux_ipadapter_then, but:
- Same node IDs (1, 2, 3, 5, 6, 8, 9, 13)
- Same connections
- Only difference: which reference photo is loaded

### Export Workflow
1. Save workflow as API format
2. Export → API Format
3. Save as `workflow/image/flux_ipadapter_now.json`

## Workflow 3: flux_background.json

**Purpose**: Generate scene backgrounds (standard text-to-image, no IP-Adapter)

This workflow uses standard Flux generation without IP-Adapter since backgrounds don't need reference photos.

### Node Configuration

1. **UNETLoader** - Flux Model
   - Same as workflow 1

2. **CLIPLoader** - CLIP Model
   - Same as workflow 1

3. **CLIPTextEncode (Node ID: 6)** - Background Prompt
   - text: Your background description from set_prompt
   - clip: Connect from CLIPLoader

4. **SamplerCustomAdvanced (Node ID: 13)** - Sampling
   - Same as workflow 1
   - BUT: model connects directly from UNETLoader (no IP-Adapter)

5. **EmptyFlux2LatentImage** - Latent Setup
   - Same dimensions as other workflows

6. **VAEDecode (Node ID: 8)** - Decode
   - Same as workflow 1

7. **VAELoader** - VAE
   - Same as workflow 1

8. **SaveImage (Node ID: 9)** - Save
   - filename_prefix: `scene_background`

### Export Workflow
1. Save workflow as API format
2. Export → API Format
3. Save as `workflow/image/flux_background.json`

## Key Differences Summary

| Feature | flux_ipadapter_then | flux_ipadapter_now | flux_background |
|---------|---------------------|-------------------|-----------------|
| IP-Adapter | ✅ Yes | ✅ Yes | ❌ No |
| Reference Photo | THEN photo | NOW photo | None |
| Prompt | Young version | Current version | Background only |
| Use Case | Character THEN | Character NOW | Scene background |

## Testing Your Workflows

### Test 1: IP-Adapter THEN
1. Load workflow in ComfyUI
2. Upload THEN reference photo
3. Set prompt: "young version, 20 years ago, [character description]"
4. Execute and verify facial consistency

### Test 2: IP-Adapter NOW
1. Load workflow in ComfyUI
2. Upload NOW reference photo
3. Set prompt: "current version, present day, [character description]"
4. Execute and verify facial consistency

### Test 3: Background
1. Load workflow in ComfyUI
2. Set prompt: "movie set, [scene background description]"
3. Execute and verify quality

## IP-Adapter Settings Reference

### Recommended Settings

| Parameter | Value | Notes |
|-----------|-------|-------|
| Weight | 0.7 | Range: 0.5-0.9 |
| Start | 0.0 | Start of IP-Adapter influence |
| End | 1.0 | End of IP-Adapter influence |
| Model | IP-Adapter for Flux | Specific to your model |

### Troubleshooting

**Problem**: Generated images don't look like reference
**Solution**: Increase IP-Adapter weight to 0.8 or 0.9

**Problem**: Generated images too similar to reference (no creativity)
**Solution**: Decrease IP-Adapter weight to 0.5 or 0.6

**Problem**: Workflow fails with "node not found" error
**Solution**: Verify IP-Adapter is properly installed in ComfyUI

## Integration with Code

Once workflows are created and saved:

1. Copy to correct location:
   ```
   workflow/image/flux_ipadapter_then.json
   workflow/image/flux_ipadapter_now.json
   workflow/image/flux_background.json
   ```

2. Restart the backend server

3. Workflows are auto-detected and available in:
   - `config.IMAGE_WORKFLOWS['flux_ipadapter_then']`
   - `config.IMAGE_WORKFLOWS['flux_ipadapter_now']`
   - `config.IMAGE_WORKFLOWS['flux_background']`

4. Auto-selection happens in `generation_service._regenerate_flfi2v_images()`:
   - When `then_reference_image_path` exists → uses `flux_ipadapter_then`
   - When `now_reference_image_path` exists → uses `flux_ipadapter_now`
   - Background generation → uses `flux_background`

## Example API Format Workflow

Here's a minimal example of what the API format should look like:

```json
{
  "1": {
    "class_type": "LoadImage",
    "inputs": {
      "image": "reference_photo.png"
    }
  },
  "5": {
    "class_type": "IPAdapter",
    "inputs": {
      "weight": 0.7,
      "image": ["1", 0],
      "model": ["2", 0]
    }
  },
  "6": {
    "class_type": "CLIPTextEncode",
    "inputs": {
      "text": "prompt here",
      "clip": ["3", 1]
    }
  },
  "13": {
    "class_type": "SamplerCustomAdvanced",
    "inputs": {
      "model": ["5", 0],
      "positive": ["6", 0]
    }
  }
}
```

## Next Steps

After creating workflows:

1. Test each workflow manually in ComfyUI
2. Verify node IDs match config.py expectations
3. Test with actual reference photos
4. Integrate with story editor UI
5. Run end-to-end test with complete ThenVsNow project

## Resources

- ComfyUI: https://github.com/comfyanonymous/ComfyUI
- IP-Adapter Plus: https://github.com/cubiq/ComfyUI_IPAdapter_plus
- Flux Model: https://huggingface.co/black-forest-labs/FLUX.1-dev
