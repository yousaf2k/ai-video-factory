# Batch Video Generation from Images

Generate videos from existing images using ComfyUI's video generation models.

## Features

- **Load images from folder**: Automatically discovers all images in a directory
- **Smart camera detection**: Detects camera movement from filename
- **Customizable video length**: Set video duration in seconds
- **Session tracking**: Optional session management for progress tracking
- **Resume support**: Resume interrupted generations
- **Unique filenames**: Automatically handles duplicate filenames with suffixes (a, b, c)

## Installation

No additional installation required if you have the main system set up. Ensure:
- ComfyUI is running and accessible
- Video generation workflow is configured (`config.WORKFLOW_PATH`)

## Usage

### Basic Usage

```bash
python batch_videos.py input_images/ output_videos/
```

This will:
1. Load all images from `input_images/`
2. Use the filename (without extension) as the motion prompt
3. Detect camera type from filename
4. Generate videos and save to `output_videos/`

### Specify Video Length

```bash
python batch_videos.py input_images/ output_videos/ --length 10
```

### Create a Session for Tracking

```bash
python batch_videos.py input_images/ output_videos/ --session my_project
```

Sessions are saved to `output/sessions/<session_id>/` and include:
- Progress tracking
- Video paths
- Generation statistics

### List Supported Camera Types

```bash
python batch_videos.py --list-cameras
```

## Camera Detection

The system automatically detects camera movement from the filename using these patterns:

| Camera Type | Filename Patterns |
|------------|------------------|
| `static` | `static camera` |
| `zoom` | `zoom camera`, `zoom in`, `zoom out` |
| `pan` | `pan camera`, `pan left`, `pan right`, `pan up`, `pan down` |
| `tilt` | `tilt camera`, `tilt up`, `tilt down` |
| `dolly` | `dolly camera`, `dolly in`, `dolly out` |
| `truck` | `truck camera`, `truck left`, `truck right` |
| `pedestal` | `pedestal camera`, `pedestal up`, `pedestal down` |
| `orbit` | `orbit camera`, `orbit left`, `orbit right` |
| `crane` | `crane up`, `crane down`, `crane in`, `crane out` |
| `handheld` | `handheld camera` |
| `tracking` | `tracking shot` |
| `push` | `push in`, `push on` |
| `pull` | `pull back`, `pull out` |

### Filename Examples

```
beautiful_girl_dancing_static_camera.png
  → Motion: "beautiful girl dancing"
  → Camera: "static"

sunset_zoom_camera.jpg
  → Motion: "sunset"
  → Camera: "zoom"

city_pan_left-camera.gif
  → Motion: "city"
  → Camera: "pan"

ocean_waves_zoom_in.webp
  → Motion: "ocean waves"
  → Camera: "zoom"

eiffel_tower_tilt_up.png
  → Motion: "eiffel tower"
  → Camera: "tilt up"

no_camera_specified.jpg
  → Motion: "no camera specified"
  → Camera: "static" (default)
```

## Supported Image Formats

- PNG (`.png`)
- JPEG (`.jpg`, `.jpeg`)
- WebP (`.webp`)
- BMP (`.bmp`)
- TIFF (`.tiff`)
- GIF (`.gif`)

## Output

Videos are saved as MP4 files with the naming pattern:
- `shot_001.mp4`, `shot_002.mp4`, etc.
- If a file exists, suffixes are added: `shot_001a.mp4`, `shot_001b.mp4`, etc.

## Session Tracking

When you use `--session`, the system:

1. Creates a session in `output/sessions/<session_id>/`
2. Saves progress after each video generation
3. Tracks which shots are complete
4. Enables resume if interrupted

Session files:
- `{session_id}_meta.json`: Session metadata and progress
- `videos/`: Generated videos

### Resume a Session

If a session is interrupted, you can't currently resume from where it left off.
This feature may be added in future versions.

## Examples

### Example 1: Simple Batch Generation

```bash
# Input folder structure:
# input_images/
#   ├── cat_sleeping_static_camera.png
#   ├── dog_running_zoom_camera.jpg
#   └── bird_flying_pan_camera.gif

python batch_videos.py input_images/ output_videos/

# Output:
# output_videos/
#   ├── shot_001.mp4  (cat sleeping, static)
#   ├── shot_002.mp4  (dog running, zoom)
#   └── shot_003.mp4  (bird flying, pan)
```

### Example 2: Long Videos with Session

```bash
python batch_videos.py my_photos/ my_videos/ --length 15 --session vacation_2024

# Creates session: output/sessions/vacation_2024/
# Session contains:
#   - vacation_2024_meta.json (progress tracking)
#   - videos/ (generated videos)
```

### Example 3: Using Underscores in Filenames

```
Input Filename: beautiful_sunset_beach_zoom_camera.png

Detected:
  Motion Prompt: "beautiful sunset beach"
  Camera: "zoom"

Generated Video: output_videos/shot_001.mp4
```

## Troubleshooting

### No Images Found

**Error**: `No image files found in {folder}`

**Solutions**:
- Check the folder path is correct
- Ensure files have valid image extensions (.png, .jpg, etc.)
- Check file permissions

### ComfyUI Connection Failed

**Error**: `Failed to load workflow` or `Connection refused`

**Solutions**:
- Ensure ComfyUI is running
- Check `config.WORKFLOW_PATH` is correct
- Verify ComfyUI API URL in config

### Video Generation Failed

**Error**: `No output files generated`

**Solutions**:
- Check ComfyUI has the required video generation model
- Verify workflow template is compatible
- Check ComfyUI logs for errors
- Try increasing `--length` if video is too short/long

### Camera Not Detected

If camera type is not found in filename, it defaults to `static`.

**Solution**:
- Add camera type to filename (e.g., `zoom camera`)
- Or manually specify in filename using supported patterns

## Tips

1. **Organize files**: Use descriptive filenames with camera info
2. **Consistent naming**: Use consistent patterns (e.g., `scene_description_camera.jpg`)
3. **Test first**: Try with a few images before processing large batches
4. **Use sessions**: Enable sessions for large batches to track progress
5. **Check storage**: Ensure enough disk space for output videos

## Advanced: Camera Detection Patterns

The camera detection uses regex patterns. You can modify `CAMERA_PATTERNS` in `batch_videos.py` to add custom patterns:

```python
CAMERA_PATTERNS = {
    'static': r'\bstatic\s*camera\b',
    'zoom': r'\bzoom\s*camera\b|\bzoom\s*(in|out)\b',
    # Add your custom patterns here
}
```

## Integration with Main Pipeline

This batch script is standalone but can be integrated into the main pipeline:

1. Videos generated here can be used in sessions
2. Session metadata is compatible with main system
3. Can be used for pre-processing existing images before full pipeline

## Future Enhancements

Potential features for future versions:
- Resume from interrupted sessions
- Batch size control
- Custom motion prompts file
- Image preprocessing (resize, format conversion)
- Progress bar
- Parallel processing for faster generation
