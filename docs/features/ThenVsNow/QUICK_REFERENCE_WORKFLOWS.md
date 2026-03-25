# ComfyUI Workflows - Quick Reference Card

Quick reference for the three IP-Adapter workflows used in ThenVsNow projects.

## Workflow Files Location
```
workflow/image/
├── flux_ipadapter_then.json    # THEN character (young version)
├── flux_ipadapter_now.json     # NOW character (current version)
└── flux_background.json        # Scene background generation
```

## Node ID Quick Reference

### flux_ipadapter_then.json & flux_ipadapter_now.json

| ID | Node Type | Purpose | Key Settings |
|----|-----------|---------|--------------|
| 1 | LoadImage | Reference photo | Upload THEN/NOW photo |
| 2 | UNETLoader | Flux model | flux1-dev.sft, fp8_e4m3fn |
| 3 | DualCLIPLoader | Text encoder | clip_l, t5xxl_fp16, flux |
| 5 | IPAdapter | Facial consistency | **weight: 0.7** |
| 6 | CLIPTextEncode | Prompt | "young/current version..." |
| 8 | VAEDecode | Decode latent | - |
| 9 | SaveImage | Save output | filename_prefix |
| 10 | EmptyFlux2LatentImage | Latent setup | W: 1344, H: 768 |
| 13 | SamplerCustomAdvanced | Sampling | euler, 20 steps |
| 14 | VAELoader | VAE model | ae.safetensors |

### flux_background.json

| ID | Node Type | Purpose | Key Settings |
|----|-----------|---------|--------------|
| 2 | UNETLoader | Flux model | flux1-dev.sft, fp8_e4m3fn |
| 3 | DualCLIPLoader | Text encoder | clip_l, t5xxl_fp16, flux |
| 6 | CLIPTextEncode | Prompt | "movie set background..." |
| 8 | VAEDecode | Decode latent | - |
| 9 | SaveImage | Save output | scene_background |
| 10 | EmptyFlux2LatentImage | Latent setup | W: 1344, H: 768 |
| 13 | SamplerCustomAdvanced | Sampling | euler, 20 steps |
| 14 | VAELoader | VAE model | ae.safetensors |

**Note**: Background workflow has NO IPAdapter node!

## Connection Patterns

### IP-Adapter Workflows (THEN/NOW)
```
LoadImage(1).IMAGE → IPAdapter(5).image
UNETLoader(2).MODEL → IPAdapter(5).model
DualCLIPLoader(3).CLIP[1] → IPAdapter(5).clip

IPAdapter(5).MODEL → Sampler(13).model
CLIPTextEncode(6).CONDITIONING → Sampler(13).positive
EmptyFlux2LatentImage(10).LATENT → Sampler(13).latent_image

Sampler(13).LATENT → VAEDecode(8).samples
VAELoader(14).VAE → VAEDecode(8).vae
VAEDecode(8).IMAGE → SaveImage(9).images
```

### Background Workflow
```
UNETLoader(2).MODEL → Sampler(13).model [DIRECT, no IPAdapter!]
CLIPTextEncode(6).CONDITIONING → Sampler(13).positive
EmptyFlux2LatentImage(10).LATENT → Sampler(13).latent_image

Sampler(13).LATENT → VAEDecode(8).samples
VAELoader(14).VAE → VAEDecode(8).vae
VAEDecode(8).IMAGE → SaveImage(9).images
```

## IP-Adapter Weight Guide

| Weight | Effect | Use Case |
|--------|--------|----------|
| 0.5-0.6 | Subtle | Creative freedom needed |
| **0.7** | **Balanced** | **Default (recommended)** |
| 0.8-0.9 | Strong | High facial fidelity needed |
| 1.0 | Very strong | Exact likeness required |

## Dimension Quick Reference

| Aspect Ratio | Width | Height | Use In |
|--------------|-------|--------|--------|
| 16:9 | 1344 | 768 | Standard video |
| 9:16 | 768 | 1344 | Vertical video |
| 1:1 | 1024 | 1024 | Square format |

## Sampling Settings

| Parameter | Value | Notes |
|-----------|-------|-------|
| Sampler | euler | Fast, good quality |
| Scheduler | sgm_uniform | Standard for Flux |
| Steps | 20 | Default (adjustable 10-40) |
| Denoise | 1.0 | Full denoising |

## Prompt Templates

### THEN Prompt
```
"young version, 20 years ago, {character description}, portrait style,
high quality, detailed"
```

### NOW Prompt
```
"current version, present day, {character description}, portrait style,
high quality, detailed"
```

### Background Prompt
```
"movie set, {scene description}, cinematic lighting, high quality,
detailed background"
```

## Backend Auto-Injection

The backend automatically:
- ✅ Injects reference image path into node 1
- ✅ Injects prompt text into node 6
- ✅ Sets dimensions in node 10
- ✅ Sets unique filename in node 9

## Model File Checklist

```
ComfyUI/models/
├── unet/
│   └── flux1-dev.sft                    ✅ Required
├── clip/
│   ├── clip_l.safetensors               ✅ Required
│   └── t5xxl_fp16.safetensors           ✅ Required
├── vae/
│   └── ae.safetensors                   ✅ Required
└── ipadapter/
    └── ipadapter_flux.safetensors       ✅ Required for THEN/NOW only
```

## Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| "Model not found" | Update model paths in nodes 2, 3, 14 |
| "IPAdapter node missing" | Install IP-Adapter Plus |
| Wrong dimensions | Check node 10 settings |
| Low quality | Increase sampling steps to 30 |
| Too slow | Decrease steps to 15 |
| Doesn't look like reference | Increase IP-Adapter weight to 0.8 |
| Too similar to reference | Decrease weight to 0.6 |

## Export Format

**Required**: API Format (not UI Format)

**How to export**:
1. Save workflow in ComfyUI
2. Click "Save" → "API Format"
3. Overwrite original file

**Verify**: File should NOT contain "nodes" array, but have node IDs as keys

## Testing Command

```bash
# Test workflow conversion
python scripts/convert_workflow.py workflow/image/flux_ipadapter_then.json flux_ipadapter_then

# Expected output:
# ✅ flux_ipadapter_then: All required nodes present with correct IDs
```

## Integration Status

| Component | Status | Notes |
|-----------|--------|-------|
| Backend code | ✅ Complete | Supports reference images |
| Config | ✅ Complete | Workflows configured |
| API endpoints | ✅ Complete | Upload/generate working |
| UI components | ✅ Complete | React components built |
| Workflows | ⚠️ Needs Setup | Import & customize |
| Testing | ⏳ Pending | User to test |

## Next Actions

1. ✅ Workflow files created
2. ⚠️ Import into ComfyUI
3. ⚠️ Update model paths
4. ⚠️ Test with reference photos
5. ⚠️ Export as API format
6. ⚠️ Validate with backend
7. ⏳ Integrate into UI
8. ⏳ End-to-end test

## File Paths

**Workflows**: `workflow/image/flux_*.json`
**Config**: `config.py` (IMAGE_WORKFLOWS section)
**Docs**: `docs/guides/COMFYUI_WORKFLOW_SETUP.md`
**Script**: `scripts/convert_workflow.py`

## Quick Copy-Paste Config

```python
# config.py
IMAGE_WORKFLOWS = {
    "flux_ipadapter_then": {
        "workflow_path": resolve_path("workflow/image/flux_ipadapter_then.json"),
        "load_reference_node_id": "1",
        "ipadapter_node_id": "5",
        "text_node_id": "6",
        "save_node_id": "9",
    },
    "flux_ipadapter_now": {
        "workflow_path": resolve_path("workflow/image/flux_ipadapter_now.json"),
        "load_reference_node_id": "1",
        "ipadapter_node_id": "5",
        "text_node_id": "6",
        "save_node_id": "9",
    },
    "flux_background": {
        "workflow_path": resolve_path("workflow/image/flux_background.json"),
        "text_node_id": "6",
        "save_node_id": "9",
    },
}
```

---

**Last Updated**: 2025-01-14
**Version**: 1.0
**Status**: Workflows Created, Ready for Import
