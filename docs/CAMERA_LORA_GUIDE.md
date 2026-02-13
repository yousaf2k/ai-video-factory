# Camera LoRA System Guide

## Overview

The AI Video Factory uses a sophisticated **Multi-Camera LoRA System** that allows you to combine multiple camera movements in a single shot. Each camera type loads specific LoRA (Low-Rank Adaptation) files to enhance video generation with particular motion characteristics.

## System Architecture

### LORA_NODES Array

The system supports up to **4 simultaneous cameras** per shot, with each camera assigned to a pair of LoRA nodes:

```python
LORA_NODES = [
    {"HIGH_NOISE_LORA_NODE_ID": "128", "LOW_NOISE_LORA_NODE_ID": "127"},  # Pair 0
    {"HIGH_NOISE_LORA_NODE_ID": "130", "LOW_NOISE_LORA_NODE_ID": "131"},  # Pair 1
    {"HIGH_NOISE_LORA_NODE_ID": "132", "LOW_NOISE_LORA_NODE_ID": "133"},  # Pair 2
    {"HIGH_NOISE_LORA_NODE_ID": "134", "LOW_NOISE_LORA_NODE_ID": "135"},  # Pair 3
]
```

### Sequential Assignment

When a shot has multiple cameras, they are assigned sequentially:

- **First camera** → LORA_NODES[0]
- **Second camera** → LORA_NODES[1]
- **Third camera** → LORA_NODES[2]
- **Fourth camera** → LORA_NODES[3]

If you have more than 4 cameras, additional cameras will be skipped with a warning.

## Camera Types

### Available Cameras

| Camera Type | High Noise LoRA | Low Noise LoRA | Trigger Keyword | Strength Low | Strength High | Description |
|-------------|-----------------|----------------|-----------------|--------------|---------------|-------------|
| **slow pan** | (empty) | (empty) | "slow pan" | 0.5 | 0.6 | Gentle panning motion |
| **pan** | (empty) | (empty) | "pan" | 0.6 | 0.7 | Standard panning |
| **static** | (empty) | (empty) | "static shot" | 0.3 | 0.4 | Stationary camera |
| **dolly** | (empty) | (empty) | "dolly" | 0.7 | 0.8 | Dolly in/out movement |
| **orbit** | Surround_Camera_S1440.safetensors | (empty) | "ymq" | 0.0 | 1.0 | Orbiting around subject |
| **zoom** | (empty) | (empty) | "zoom in" | 0.8 | 0.9 | Zoom in/out |
| **tracking** | (empty) | (empty) | "tracking shot" | 0.7 | 0.8 | Tracking/following movement |
| **drone** | wan22-video8-drone-16-sel-2.safetensors | (empty) | "drone footage aerial" | 0.7 | 0.9 | Drone aerial footage |
| **arc** | wan22-video10-arcshot-16-sel-7-high.safetensors | (empty) | "arc shot" | 0.7 | 0.9 | Arcing camera movement |
| **walk** | Walk01_HighWan2_2.safetensors | Walk01_LowWan2_2.safetensors | "walking into the direction of the moving camera" | 0.7 | 0.9 | Walking with camera |
| **default** | (empty) | (empty) | "" | 0.8 | 0.8 | Default/no specific motion |

## How Multi-Camera Works

### Input Formats

You can specify multiple cameras in three formats:

1. **Comma-separated string**: `"dolly, pan"`
2. **List**: `["drone", "zoom"]`
3. **Single camera**: `"static"`

### Example Workflow

For a shot with camera: `"drone, orbit"`

```
[LORA] Processing camera 1/2: 'drone' -> Pair 0
  Low Node 127: SKIPPED (empty filename)
  High Node 128: wan22-video8-drone-16-sel-2.safetensors (strength: 0.9)

[LORA] Processing camera 2/2: 'orbit' -> Pair 1
  Low Node 131: SKIPPED (empty filename)
  High Node 130: Surround_Camera_S1440.safetensors (strength: 1.0)

[TRIGGERS] Added: drone footage aerial, ymq
```

The motion prompt will be enhanced to:
```
<original motion prompt>, drone footage aerial, ymq
```

## LoRA Configuration Structure

Each camera type in `CAMERA_LORA_MAPPING` has the following structure:

```python
"camera_name": {
    "high_noise_lora": "filename.safetensors",  # LoRA for high noise (dynamic motion)
    "low_noise_lora": "filename.safetensors",   # LoRA for low noise (stable motion)
    "trigger_keyword": "keyword phrase",        # Text appended to motion prompt
    "strength_low": 0.7,                         # Low noise LoRA strength (0.0 - 1.0)
    "strength_high": 0.9                         # High noise LoRA strength (0.0 - 1.0)
}
```

### LoRA File Placement

Place your LoRA files in ComfyUI's models directory:

```
ComfyUI/models/loras/
├── wan22-video8-drone-16-sel-2.safetensors
├── wan22-video10-arcshot-16-sel-7-high.safetensors
├── Walk01_HighWan2_2.safetensors
├── Walk01_LowWan2_2.safetensors
├── Surround_Camera_S1440.safetensors
└── ...
```

## Adding New Camera Types

To add a new camera type:

1. **Edit `config.py`** and add an entry to `CAMERA_LORA_MAPPING`:

```python
"my_camera": {
    "high_noise_lora": "MyCamera_High.safetensors",
    "low_noise_lora": "MyCamera_Low.safetensors",
    "trigger_keyword": "my custom camera movement",
    "strength_low": 0.7,
    "strength_high": 0.9
}
```

2. **Place LoRA files** in `ComfyUI/models/loras/`

3. **Use the camera** in your story:
   ```json
   {
     "camera": "my_camera",
     "motion_prompt": "gentle movement forward"
   }
   ```

4. **Or combine with other cameras**:
   ```json
   {
     "camera": "my_camera, zoom",
     "motion_prompt": "dynamic entrance"
   }
   ```

## Trigger Keywords

Trigger keywords are automatically appended to motion prompts to activate specific LoRA effects. They are **only added to motion prompts**, not image prompts.

### Example

Original motion prompt:
```
Camera moves slowly toward the subject
```

With camera `"drone, zoom"`:
```
Camera moves slowly toward the subject, drone footage aerial, zoom in
```

## High vs Low Noise LoRAs

The Wan 2.2 workflow uses **both LoRAs simultaneously**:

- **High Noise LoRA**: Applied for more dynamic, pronounced motion effects
- **Low Noise LoRA**: Applied for subtle, stable motion enhancements

Some camera types only use high noise (low_noise_lora is empty), while others like "walk" use both.

## Strength Settings

Strength values control LoRA influence:

- **0.0 - 0.3**: Subtle effect
- **0.4 - 0.6**: Moderate effect
- **0.7 - 0.9**: Strong effect
- **1.0**: Maximum effect

Each camera type can have different strength values for high and low noise LoRAs.

## Troubleshooting

### Camera Not Working

```
[WARN] Camera 'my_camera' skipped - no available LoRA node pairs (max 4 cameras)
```

**Solution**: You have more than 4 cameras. Remove some or split into multiple shots.

### LoRA File Not Found

```
[ERROR] Failed to load LoRA: filename.safetensors
```

**Solution**: Ensure LoRA files are in `ComfyUI/models/loras/`

### Trigger Not Appearing

Check that:
1. Camera type exists in `CAMERA_LORA_MAPPING`
2. `trigger_keyword` is not empty
3. Motion prompt exists in the shot

## Workflow Integration

The camera LoRA system is integrated into:

1. **Shot Planning** (`core/shot_planner.py`): Assigns cameras to shots
2. **Prompt Compiler** (`core/prompt_compiler.py`): Loads LoRAs and adds triggers
3. **Main Pipeline** (`core/main.py`): Enhances motion prompts

## Best Practices

1. **Start Simple**: Test with one camera before combining multiple
2. **Compatible Combinations**: Some combinations work better than others
   - Good: `"drone, orbit"`, `"dolly, zoom"`
   - Test: `"static, tracking"` (conflicting motions)
3. **Strength Tuning**: Adjust strength values based on results
4. **Trigger Keywords**: Keep them descriptive and consistent with LoRA intent
5. **LoRA Quality**: Use high-quality LoRA files trained for specific motions

## Examples

### Single Camera
```json
{
  "shot": 1,
  "camera": "drone",
  "motion_prompt": "Flying over mountain landscape"
}
```

### Dual Camera
```json
{
  "shot": 2,
  "camera": "dolly, zoom",
  "motion_prompt": "Approaching the ancient temple"
}
```

### Triple Camera
```json
{
  "shot": 3,
  "camera": ["drone", "orbit", "zoom"],
  "motion_prompt": "Epic reveal of the castle"
}
```

## See Also

- [Configuration Guide](CONFIGURATION.md)
- [Workflow Guide](WORKFLOW_GUIDE.md)
- [API Reference](API_REFERENCE.md)
