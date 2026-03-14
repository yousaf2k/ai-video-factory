# Reference Images & Scene Backgrounds - Verification Checklist

This checklist helps verify the complete implementation of reference images and scene backgrounds for ThenVsNow projects.

## Pre-Implementation Checks

### Environment Setup
- [ ] ComfyUI running and accessible
- [ ] Flux model installed in ComfyUI
- [ ] IP-Adapter Plus node installed in ComfyUI
- [ ] Backend server can connect to ComfyUI
- [ ] Frontend can connect to backend API
- [ ] WebSocket connection working

### Data Models
- [ ] Character model has `then_reference_image_path` field
- [ ] Character model has `now_reference_image_path` field
- [ ] Scene model has `background_image_path` field
- [ ] Scene model has `background_generated` field
- [ ] Scene model has `background_is_generated` field
- [ ] Frontend TypeScript types match backend models

## Backend Verification

### API Endpoints
- [ ] POST /characters/{index}/upload-reference?variant=then works
- [ ] POST /characters/{index}/upload-reference?variant=now works
- [ ] POST /scenes/{id}/upload-background works
- [ ] POST /scenes/{id}/generate-background works
- [ ] All endpoints return proper error messages
- [ ] All endpoints broadcast WebSocket updates

### Image Generation
- [ ] `generate_image_comfyui()` accepts `reference_image_path` parameter
- [ ] Reference image injected into LoadImage node when provided
- [ ] IP-Adapter usage logged in console
- [ ] Auto-switch to ComfyUI when reference provided with Gemini mode
- [ ] Warning logged when auto-switching modes

### Generation Service
- [ ] `_regenerate_flfi2v_images()` retrieves character references
- [ ] Auto-selects `flux_ipadapter_then` workflow for THEN images
- [ ] Auto-selects `flux_ipadapter_now` workflow for NOW images
- [ ] Falls back to standard Flux when no references provided
- [ ] `generate_scene_background()` generates backgrounds correctly
- [ ] Background images saved to `session/backgrounds/`
- [ ] Story.json updated with background paths

### Configuration
- [ ] `flux_ipadapter_then` in IMAGE_WORKFLOWS
- [ ] `flux_ipadapter_now` in IMAGE_WORKFLOWS
- [ ] `flux_background` in IMAGE_WORKFLOWS
- [ ] All workflows have correct node IDs
- [ ] `load_reference_node_id` configured for IP-Adapter workflows

## Frontend Verification

### Components
- [ ] CharacterReferenceUpload component renders
- [ ] Drag-drop works for THEN reference
- [ ] Drag-drop works for NOW reference
- [ ] File picker opens on click
- [ ] Upload progress shows during upload
- [ ] Preview displays after upload
- [ ] Replace button works for existing photos
- [ ] SceneBackgroundManager component renders
- [ ] Upload button works for backgrounds
- [ ] Generate AI button works for backgrounds
- [ ] Preview displays after upload/generation
- [ ] Source badge shows (Uploaded/AI Generated)
- [ ] Warning shows when set_prompt missing

### UI Integration
- [ ] Components integrated into story editor
- [ ] Character references visible in character list
- [ ] Scene backgrounds visible in scene list
- [ ] Updates propagate via WebSocket
- [ ] Page refreshes don't lose data

## End-to-End Tests

### Test 1: Upload Character References
**Setup**: Create new ThenVsNow session

**Steps**:
1. Navigate to story editor
2. Find character 0
3. Upload THEN reference photo (drag-drop or click)
4. Verify upload progress indicator
5. Verify preview appears
6. Upload NOW reference photo
7. Verify preview appears
8. Check story.json contains both paths
9. Verify paths are relative (start with `output/sessions/`)

**Expected Results**:
- [ ] Both uploads complete without errors
- [ ] Previews display correctly
- [ ] story.json updated with paths
- [ ] Images saved in `session/references/`

### Test 2: Generate Scene Background (Upload)
**Setup**: Existing session with scene that has set_prompt

**Steps**:
1. Navigate to scene 0
2. Click "Upload" button
3. Select background image file
4. Verify upload completes
5. Check preview appears
6. Verify "Uploaded" badge shows
7. Check story.json for `background_image_path`
8. Verify `background_is_generated=false`

**Expected Results**:
- [ ] Upload completes without errors
- [ ] Preview displays
- [ ] Badge shows "Uploaded"
- [ ] Image saved in `session/backgrounds/`

### Test 3: Generate Scene Background (AI)
**Setup**: Existing session with scene that has set_prompt

**Steps**:
1. Navigate to scene 0
2. Verify "Generate AI" button is enabled
3. Click "Generate AI" button
4. Monitor progress via WebSocket
5. Wait for generation to complete
6. Verify preview appears
7. Verify "AI Generated" badge shows
8. Check story.json for `background_image_path`
9. Verify `background_is_generated=true`

**Expected Results**:
- [ ] Generation starts without errors
- [ ] Progress updates received
- [ ] Preview displays after completion
- [ ] Badge shows "AI Generated"
- [ ] Image saved in `session/backgrounds/`

### Test 4: Complete FLFI2V Workflow with References
**Setup**: Session with uploaded references and background

**Steps**:
1. Upload THEN reference for character 0
2. Upload NOW reference for character 0
3. Generate background for scene 0 (upload or AI)
4. Generate NOW image for shot 1
5. Check logs for IP-Adapter usage
6. Verify `flux_ipadapter_now` workflow used
7. Generate THEN image for shot 1
8. Check logs for IP-Adapter usage
9. Verify `flux_ipadapter_then` workflow used
10. Compare generated images with references
11. Verify facial consistency

**Expected Results**:
- [ ] NOW generation uses `flux_ipadapter_now`
- [ ] THEN generation uses `flux_ipadapter_then`
- [ ] Logs show IP-Adapter usage
- [ ] Generated images maintain facial likeness
- [ ] Background incorporated into both images
- [ ] No errors in console or logs

### Test 5: Fallback Without References
**Setup**: Session without reference images

**Steps**:
1. Create new session (no references)
2. Generate NOW image
3. Verify standard Flux workflow used
4. Generate THEN image
5. Verify standard Flux workflow used
6. Check logs for no IP-Adapter warnings

**Expected Results**:
- [ ] Generation succeeds without references
- [ ] Standard `flux` workflow used
- [ ] No IP-Adapter errors in logs
- [ ] Images generated normally

### Test 6: Gemini Web Auto-Switch
**Setup**: Image mode set to Gemini, reference image provided

**Steps**:
1. Set IMAGE_GENERATION_MODE to "gemini" in config
2. Upload reference photo
3. Attempt image generation
4. Check console for auto-switch warning
5. Verify ComfyUI mode used instead

**Expected Results**:
- [ ] Warning logged about auto-switch
- [ ] Generation uses ComfyUI mode
- [ ] IP-Adapter works correctly
- [ ] No Gemini errors

## Workflow Verification

### flux_ipadapter_then.json
- [ ] Workflow file exists in `workflow/image/`
- [ ] LoadImage node (ID: 1) present
- [ ] IP-Adapter node (ID: 5) present
- [ ] CLIPTextEncode node (ID: 6) present
- [ ] SamplerCustomAdvanced node (ID: 13) present
- [ ] VAEDecode node (ID: 8) present
- [ ] SaveImage node (ID: 9) present
- [ ] Workflow in API format
- [ ] Manual test in ComfyUI succeeds
- [ ] Reference image influences output

### flux_ipadapter_now.json
- [ ] Workflow file exists in `workflow/image/`
- [ ] Same node structure as flux_ipadapter_then
- [ ] Manual test in ComfyUI succeeds
- [ ] Reference image influences output

### flux_background.json
- [ ] Workflow file exists in `workflow/image/`
- [ ] No IP-Adapter node
- [ ] Standard Flux text-to-image
- [ ] Manual test in ComfyUI succeeds
- [ ] Background quality acceptable

## Error Handling

### Upload Errors
- [ ] Non-image file rejected
- [ ] Oversized file handled gracefully
- [ ] Network error shows user-friendly message
- [ ] Invalid character index returns 400 error
- [ ] Invalid scene ID returns 404 error

### Generation Errors
- [ ] Missing set_prompt shows warning
- [ ] ComfyUI connection error handled
- [ ] Workflow not found error handled
- [ ] Invalid reference path handled
- [ ] WebSocket error doesn't crash generation

## Performance Checks

### Upload Performance
- [ ] Large image (>5MB) uploads in reasonable time
- [ ] Progress indicator updates smoothly
- [ ] Multiple concurrent uploads don't block UI
- [ ] Preview loads quickly after upload

### Generation Performance
- [ ] IP-Adapter generation completes in reasonable time
- [ ] Progress updates sent regularly
- [ ] Background generation doesn't block other operations
- [ ] Memory usage stable during generation

## Documentation

### User Documentation
- [ ] User guide for uploading references exists
- [ ] User guide for generating backgrounds exists
- [ ] Troubleshooting section covers common issues
- [ ] Screenshots/visuals provided

### Developer Documentation
- [ ] API documented with examples
- [ ] Component props documented
- [ ] Workflow creation guide exists
- [ ] Integration guide for UI components

## Backward Compatibility

### Existing Projects
- [ ] Old projects load without errors
- [ ] Projects without references work normally
- [ ] Old shots still generate correctly
- [ ] No data migration required

### Optional Fields
- [ ] Reference fields default to None
- [ ] Background fields default to None/false
- [ ] UI handles missing fields gracefully
- [ ] API handles missing fields gracefully

## Sign-off

### Developer
- [ ] All code changes reviewed
- [ ] All tests pass
- [ ] Documentation complete
- [ ] Ready for QA

### QA
- [ ] All test cases executed
- [ ] All checks pass
- [ ] No critical bugs found
- [ ] Ready for production

### Product Owner
- [ ] Feature meets requirements
- [ ] User experience acceptable
- [ ] Documentation sufficient
- [ ] Approved for release

## Notes

Use this section to document any issues found, workarounds, or special considerations during testing:

```
Date: ___________
Tester: ___________
Build: ___________

Notes:




```

## Quick Reference

### Key Files to Check
- Backend: `web_ui/backend/models/story.py`
- Backend: `web_ui/backend/api/stories.py`
- Backend: `web_ui/backend/services/generation_service.py`
- Core: `core/comfyui_image_generator.py`
- Core: `core/image_generator.py`
- Config: `config.py`
- Frontend: `web_ui/frontend/src/types/index.ts`
- Component: `web_ui/frontend/src/components/characters/CharacterReferenceUpload.tsx`
- Component: `web_ui/frontend/src/components/scenes/SceneBackgroundManager.tsx`

### Quick Test Commands

```bash
# Test API endpoints
curl -X POST "http://localhost:8000/api/sessions/{session_id}/story/characters/0/upload-reference?variant=then" \
  -F "file=@then.jpg"

curl -X POST "http://localhost:8000/api/sessions/{session_id}/story/scenes/0/generate-background"

# Check backend logs
tail -f output/logs/backend.log | grep -i "ipadapter"

# Verify workflow files
ls -la workflow/image/flux_ipadapter_*.json
```
