# Reference Images & Scene Backgrounds Implementation Summary

## Overview

This implementation adds support for reference images (for facial consistency) and scene backgrounds to the ThenVsNow FLFI2V workflow. Users can now upload actual photos of actors and generate reusable scene backgrounds.

## What Was Implemented

### Phase 1: Data Models ✅

**Backend Models (`web_ui/backend/models/story.py`)**
- `Character.then_reference_image_path`: Path to THEN reference photo
- `Character.now_reference_image_path`: Path to NOW reference photo
- `Scene.background_image_path`: Path to scene background image
- `Scene.background_generated`: Whether background exists
- `Scene.background_is_generated`: True if AI-generated, False if uploaded

**Frontend Types (`web_ui/frontend/src/types/index.ts`)**
- Updated `Character` and `Scene` interfaces to match backend models

### Phase 2: API Endpoints ✅

**New Endpoints in `web_ui/backend/api/stories.py`:**

1. **POST** `/api/projects/{project_id}/story/characters/{index}/upload-reference?variant={then|now}`
   - Upload character reference photos
   - Supports drag-drop or file picker
   - Saves to `project/references/` directory
   - Updates story.json with relative paths

2. **POST** `/api/projects/{project_id}/story/scenes/{id}/upload-background`
   - Upload scene background image
   - Saves to `project/backgrounds/` directory
   - Marks as uploaded (not AI-generated)

3. **POST** `/api/projects/{project_id}/story/scenes/{id}/generate-background`
   - Generate background using AI
   - Queues background generation task
   - Broadcasts progress via WebSocket

### Phase 3: Image Generation Support ✅

**ComfyUI Image Generator (`core/comfyui_image_generator.py`)**
- Added `reference_image_path` parameter to `generate_image_comfyui()`
- Injects reference image into LoadImage node when provided
- Logs IP-Adapter usage
- Falls back gracefully when workflow doesn't support references

**Image Generator (`core/image_generator.py`)**
- Updated `generate_image()` to accept `reference_image_path`
- Auto-switches to ComfyUI mode when reference provided
- Warns when mode auto-switch occurs

**Generation Service (`web_ui/backend/services/generation_service.py`)**
- `_regenerate_flfi2v_images()`: Now retrieves character reference images from story
- Auto-selects IP-Adapter workflows when references available:
  - `flux_ipadapter_then` for THEN images
  - `flux_ipadapter_now` for NOW images
- Falls back to standard Flux workflow when no references
- `_generate_single_image()`: Passes `reference_image_path` through to generation
- New `generate_scene_background()`: Generates scene backgrounds from set_prompt

### Phase 4: Configuration ✅

**Config Updates (`config.py`)**
- Added `flux_ipadapter_then` workflow configuration
- Added `flux_ipadapter_now` workflow configuration
- Added `flux_background` workflow configuration
- Each includes node IDs for:
  - `load_reference_node_id`: LoadImage for reference
  - `ipadapter_node_id`: IP-Adapter node
  - Standard text, sampler, VAE, save nodes

### Phase 5: UI Components ✅

**CharacterReferenceUpload Component**
- Location: `web_ui/frontend/src/components/characters/CharacterReferenceUpload.tsx`
- Features:
  - Drag-drop upload for THEN and NOW photos
  - Preview uploaded images
  - Upload progress indicator
  - Replace existing photos
  - Separate upload for each variant

**SceneBackgroundManager Component**
- Location: `web_ui/frontend/src/components/scenes/SceneBackgroundManager.tsx`
- Features:
  - Upload background image
  - Generate background with AI button
  - Preview generated/uploaded background
  - Show source (uploaded vs AI-generated)
  - Warning when set_prompt missing

## How It Works

### Character Reference Images Flow

1. **User uploads reference photos** via CharacterReferenceUpload component
2. **Images saved** to `project/references/` directory
3. **Story updated** with `then_reference_image_path` and `now_reference_image_path`
4. **Generation time**:
   - `_regenerate_flfi2v_images()` retrieves references from story
   - Auto-selects `flux_ipadapter_then` or `flux_ipadapter_now` workflow
   - Passes reference to `generate_image_comfyui()`
   - ComfyUI uses IP-Adapter for facial consistency

### Scene Background Flow

**Option 1: Upload**
1. User uploads background image via SceneBackgroundManager
2. Image saved to `project/backgrounds/`
3. Scene updated with `background_image_path` and `background_is_generated=false`

**Option 2: Generate**
1. User clicks "Generate AI" button
2. API queues background generation task
3. `generate_scene_background()` generates using Flux workflow
4. Progress broadcast via WebSocket
5. Scene updated with `background_image_path` and `background_is_generated=true`

## Integration Points

### For Story Editor Page

To integrate these components into your story editor:

```tsx
import CharacterReferenceUpload from '@/components/characters/CharacterReferenceUpload';
import SceneBackgroundManager from '@/components/scenes/SceneBackgroundManager';

// In character section:
{story.characters?.map((character, index) => (
  <div key={index}>
    {/* Existing character fields */}
    <CharacterReferenceUpload
      character={character}
      characterIndex={index}
      projectId={projectId}
      onUpdate={() => {/* reload story */}}
    />
  </div>
))}

// In scene section:
{story.scenes.map((scene) => (
  <div key={scene.scene_id}>
    {/* Existing scene fields */}
    <SceneBackgroundManager
      scene={scene}
      projectId={projectId}
      onUpdate={() => {/* reload story */}}
    />
  </div>
))}
```

## Backward Compatibility

✅ **Fully backward compatible**
- New fields optional (default to None/false)
- Existing projects without references work as before
- Standard workflows still supported
- IP-Adapter only used when references provided
- No data migration needed

## Workflow Requirements

### IP-Adapter Workflows

To use the reference image feature, you need to create ComfyUI workflows with IP-Adapter support:

**Required Files:**
- `workflow/image/flux_ipadapter_then.json` - THEN generation with IP-Adapter
- `workflow/image/flux_ipadapter_now.json` - NOW generation with IP-Adapter
- `workflow/image/flux_background.json` - Background generation (optional, uses standard Flux)

**Workflow Structure:**
```
LoadImage (reference) → IP-Adapter → KSampler → VAE Decode → Save
                                   ↑
                            CLIP Text Encode (prompt)
```

**IP-Adapter Settings:**
- Weight: 0.7 (recommended)
- Model: IP-Adapter for Flux
- Start/end: 0.0 to 1.0

## Testing

### Test Case 1: Upload Reference Images
1. Create ThenVsNow project
2. Upload THEN reference photo for character 0
3. Upload NOW reference photo for character 0
4. Verify paths saved in story.json
5. Generate images - check IP-Adapter usage in logs

### Test Case 2: Scene Background Generation
1. Generate background for scene 0
2. Verify image saved in project/backgrounds/
3. Check scene model updated
4. Verify `background_is_generated=true`

### Test Case 3: Complete Workflow
1. Upload scene background OR generate with AI
2. Upload character reference photos (THEN and NOW)
3. Generate NOW image (background + NOW reference)
4. Generate THEN image (NOW image + THEN reference)
5. Verify facial consistency in generated images

### Test Case 4: Gemini Web Fallback
1. Set image mode to Gemini
2. Try to generate with reference image
3. Verify auto-switch to ComfyUI with warning

## File Structure

```
web_ui/backend/
├── models/story.py                    # Updated Character & Scene models
├── api/stories.py                     # Added upload endpoints
└── services/generation_service.py     # Updated FLFI2V logic

web_ui/frontend/src/
├── types/index.ts                     # Updated Character & Scene types
└── components/
    ├── characters/
    │   └── CharacterReferenceUpload.tsx  # NEW
    └── scenes/
        └── SceneBackgroundManager.tsx    # NEW

core/
├── image_generator.py                 # Added reference_image_path param
└── comfyui_image_generator.py         # Updated to inject references

config.py                              # Added IP-Adapter workflows

workflow/image/
├── flux_ipadapter_then.json           # TODO: Create this workflow
├── flux_ipadapter_now.json            # TODO: Create this workflow
└── flux_background.json               # TODO: Create this workflow
```

## Next Steps

1. **Create IP-Adapter Workflows**: Build the three ComfyUI workflows listed above
2. **Integrate UI Components**: Add components to story editor page
3. **Test End-to-End**: Verify complete workflow with real reference photos
4. **Documentation**: Add user guide for uploading references and generating backgrounds

## API Examples

### Upload THEN Reference
```bash
curl -X POST \
  "http://localhost:8000/api/projects/{project_id}/story/characters/0/upload-reference?variant=then" \
  -F "file=@then_photo.jpg"
```

### Upload NOW Reference
```bash
curl -X POST \
  "http://localhost:8000/api/projects/{project_id}/story/characters/0/upload-reference?variant=now" \
  -F "file=@now_photo.jpg"
```

### Upload Background
```bash
curl -X POST \
  "http://localhost:8000/api/projects/{project_id}/story/scenes/0/upload-background" \
  -F "file=@background.jpg"
```

### Generate Background
```bash
curl -X POST \
  "http://localhost:8000/api/projects/{project_id}/story/scenes/0/generate-background"
```

## Summary

This implementation provides:
- ✅ Character reference image upload (THEN and NOW)
- ✅ Scene background upload and AI generation
- ✅ IP-Adapter workflow support for facial consistency
- ✅ Reusable scene backgrounds across characters
- ✅ Full backward compatibility
- ✅ Progress tracking via WebSocket
- ✅ Auto-workflow selection based on reference availability

The system now supports the intended sequential generation:
1. NOW first (background + NOW reference)
2. THEN after (NOW image + THEN reference)

This ensures proper temporal flow and visual consistency in ThenVsNow videos.
