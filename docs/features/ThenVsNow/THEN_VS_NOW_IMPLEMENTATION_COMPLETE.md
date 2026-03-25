# ThenVsNow Feature Implementation - Complete

**Date:** March 12, 2026
**Status:** ✅ COMPLETE - All 12 Phases Implemented

---

## Overview

The "Then Vs Now" feature with FLFI2V (First Last Frame Image to Video) support has been successfully implemented. This feature allows users to generate cinematic reunion videos featuring original cast members returning to movie sets in both their original (THEN) and current (NOW) appearances.

---

## Implementation Summary

### Phase 1: Data Model Changes ✅

**Files Modified:**
- `web_ui/backend/models/story.py`
- `web_ui/backend/models/shot.py`
- `web_ui/frontend/src/types/index.ts`

**Changes:**
- Added `ProjectType` enum (DOCUMENTARY=1, THEN_VS_NOW=2)
- Added `MovieMetadata` model (year, cast, director, genre)
- Added `YouTubeMetadata` model (title_options, seo_keywords, chapters, description_preview)
- Added `Character` model (name, then_prompt, now_prompt, meeting_prompt, departure_prompt)
- Extended `Story` model with `project_type`, `characters`, `youtube_metadata`, `movie_metadata`
- Extended `Scene` model with `set_prompt` for movie set backgrounds
- Extended `Shot` model with FLFI2V fields (is_flfi2v, then_image_prompt, now_image_prompt, etc.)

---

### Phase 2: ThenVsNow Story Agent ✅

**Files Modified:**
- `agents/story/then_vs_now.md`

**Changes:**
- Complete agent prompt for generating ThenVsNow stories from movie names
- CHARACTER IMAGE PROMPTS section with centered interview style specifications
- 7 mandatory scene detail requirements:
  1. Exact Movie Scene Reference
  2. Accurate Set Recreation
  3. Composition Lock (MANDATORY) - STRAIGHT-ON EYE-LEVEL CAMERA, CENTERED SYMMETRICAL FRAMING
  4. Lighting & Atmosphere
  5. Production Crew (2-5 members)
  6. Character Presence Rule
  7. Rendering Style (ultra-realistic, 4K cinematic)
- NOW image selfie composition with iPhone 15 Pro Max
- YouTube SEO metadata generation
- Movie poster-style thumbnail prompts

---

### Phase 3: Story Engine ✅

**Files Modified:**
- `core/story_engine.py`

**Changes:**
- Added `build_story_then_vs_now()` function
- Added `generate_shots_from_then_vs_now_story()` function
- Direct shot generation bypassing shot planner
- Each character gets 2 shots: Meeting and Departure
- Proper FLFI2V field mapping

---

### Phase 4: Project Service ✅

**Files Modified:**
- `web_ui/backend/services/project_service.py`

**Changes:**
- ThenVsNow agent detection
- Special story generation flow for ThenVsNow projects
- Direct shots.json creation (bypassing shot planner)
- Automatic step completion marking

---

### Phase 5: Configuration ✅

**Files Modified:**
- `config.py`

**Changes:**
- Added `wan22_flfi2v` workflow to VIDEO_WORKFLOWS
- Workflow configuration with dual image input nodes:
  - load_image_first_node_id: "128" (THEN image)
  - load_image_last_node_id: "151" (NOW image)

---

### Phase 6: Image Generation Service ✅

**Files Modified:**
- `web_ui/backend/services/generation_service.py`

**Changes:**
- `regenerate_shot_image()` supports FLFI2V mode
- `image_variant` parameter ("then", "now", "both")
- Set prompt appending to character prompts for ThenVsNow projects
- Dual image generation with proper version tracking
- File naming: `shot_001_then_001.png`, `shot_001_now_001.png`

**Critical Fixes Applied:**
1. Return type fix - returns `results.get('now')` for UI compatibility
2. Path format fix - ensures paths start with 'output/'
3. Shot list update fix - uses `shots[shot_index - 1]` instead of `shot` parameter

---

### Phase 7: Video Generation Service ✅

**Files Modified:**
- `web_ui/backend/services/generation_service.py`

**Changes:**
- `regenerate_shot_video()` supports FLFI2V mode
- `video_variant` parameter ("meeting", "departure", "both")
- `_compile_flfi2v_workflow()` for dual image workflow compilation
- File naming: `shot_001_meeting_001.mp4`, `shot_001_departure_001.mp4`

---

### Phase 8: Prompt Compiler ✅

**Status:** No changes needed - service layer handles workflow compilation

---

### Phase 9: Frontend UI Changes ✅

**Files Modified:**
- `web_ui/frontend/src/components/shots/ShotCard.tsx`
- `web_ui/frontend/src/types/index.ts`

**Changes:**
- FLFI2V state management (activeImageMode, activeVideoMode)
- FLFI2V gradient badge
- THEN/NOW toggle buttons for images
- Meeting/Departure toggle buttons for videos
- Color-coded badges (purple for THEN/Meeting, pink for NOW/Departure)
- Prompt display based on active mode
- Copy button copies active mode's prompt
- Regenerate pre-populates with active mode's prompt

---

### Phase 10: API Endpoint Updates ✅

**Files Modified:**
- `web_ui/backend/api/shots.py`

**Changes:**
- Added `image_variant` to RegenerateImageRequest
- Added `video_variant` to RegenerateVideoRequest
- Variant parameter passing to service layer

---

### Phase 11: Project Manager Updates ✅

**Files Modified:**
- `core/project_manager.py`

**Changes:**
- Added `get_story()` method
- Added `_load_story()` method
- FLFI2V marker methods:
  - `mark_then_image_generated()`
  - `mark_now_image_generated()`
  - `mark_meeting_video_rendered()`
  - `mark_departure_video_rendered()`

---

### Phase 12: Backward Compatibility ✅

**Status:** Verified
- All existing projects default to `project_type: 1` (Documentary)
- New fields are optional with sensible defaults
- No migration needed

---

## Bug Fixes Applied

### Fix 1: Missing get_story() Method
**Error:** `'ProjectManager' object has no attribute 'get_story'`
**Solution:** Added `get_story()` and `_load_story()` methods to ProjectManager
**File:** `core/project_manager.py`

### Fix 2: Images Not Visible in UI
**Error:** Images created but not showing on UI
**Cause:** Wrong return type (dict vs string) and incorrect path format
**Solution:** Return `results.get('now')` for compatibility, ensure paths start with 'output/'
**File:** `web_ui/backend/services/generation_service.py`

### Fix 3: Images Not Saved to shots.json
**Error:** Images generated but JSON file not updated
**Cause:** Modified `shot` parameter but saved different `shots` list
**Solution:** Changed to `shots[shot_index - 1]['key'] = value`
**File:** `web_ui/backend/services/generation_service.py`

### Fix 4: Toggle Buttons Not Showing
**Error:** No THEN/NOW toggle buttons visible
**Cause:** Required both image_path AND video_path, but images generate first
**Solution:** Changed condition to check for any FLFI2V paths with OR logic
**File:** `web_ui/frontend/src/components/shots/ShotCard.tsx`

---

## Documentation Created

### Guides
1. `THEN_VS_NOW_QUICKSTART.md` - Quick start guide for users
2. `THEN_VS_NOW_SCENE_REQUIREMENTS.md` - 7 mandatory scene elements
3. `VIEWING_FLFI2V_PROMPTS.md` - How to view THEN/NOW prompts
4. `FLFI2V_SELFIE_COMPOSITION.md` - Selfie composition details

### Fixes Documentation
1. `FLFI2V_SESSION_MANAGER_FIX.md`
2. `FLFI2V_TOGGLE_BUTTONS_FIX.md`
3. `IMAGE_VISIBILITY_FIX.md`
4. `SHOTS_NOT_SAVED_FIX.md`

### Plans & Testing
1. `THEN_VS_NOW_FLFI2V_IMPLEMENTATION.md` - Full implementation plan
2. `THEN_VS_NOW_TEST_REPORT.md` - Test results

---

## Verification Steps

### ✅ Create a ThenVsNow Project
1. Select "then_vs_now" story agent
2. Enter a movie name (e.g., "The Godfather")
3. Verify story.json has `project_type: 2`, characters array, movie metadata
4. Verify shots.json has `is_flfi2v: true` for all shots

### ✅ Generate Images
1. Run batch image generation
2. Verify both THEN and NOW images are generated per shot
3. Verify file naming: `shot_001_then_001.png`, `shot_001_now_001.png`
4. Verify set prompt is appended to character prompts

### ✅ Generate Videos
1. Run batch video generation
2. Verify both Meeting and Departure videos are generated per shot
3. Verify file naming: `shot_001_meeting_001.mp4`, `shot_001_departure_001.mp4`
4. Verify FLFI2V workflow uses both THEN and NOW images

### ✅ UI Verification
1. FLFI2V badge appears on shot cards
2. THEN/NOW toggle switches between images
3. Meeting/Departure toggle switches between videos
4. Prompt badges show correct mode (purple/pink)
5. Copy button copies active mode's prompt

### ✅ Backward Compatibility
1. Existing Documentary projects still work
2. Shots without `is_flfi2v` use standard generation flow

---

## Key Features

### FLFI2V Mode
- Each shot has two images: THEN (younger) and NOW (older with selfie)
- Each shot has two videos: Meeting and Departure
- Toggle buttons to switch between modes
- Color-coded badges for visual clarity

### NOW Image Composition
- Medium shot showing both characters side-by-side
- Younger (THEN) character on left
- Older (NOW) character on right taking selfie with iPhone 15 Pro Max
- iPhone clearly visible with titanium frame and triple camera system
- Both characters looking at camera
- Nostalgic expression on older character

### Scene Requirements
- 7 mandatory elements in every scene description
- Composition lock: STRAIGHT-ON EYE-LEVEL CAMERA, CENTERED SYMMETRICAL FRAMING
- Ultra-realistic, 4K cinematic rendering
- Production crew (2-5 members) for authenticity
- Exact movie scene references
- Accurate set recreation

### Prompt Viewing
- Image prompts show THEN or NOW based on active mode
- Motion prompts show Meeting or Departure based on active mode
- Color-coded badges match toggle buttons
- Copy button copies active prompt

---

## Technical Specifications

### Image Generation
- **THEN Image:** Younger character alone on movie set
- **NOW Image:** Both characters with selfie composition
- **Resolution:** Standard workflow resolution
- **Format:** PNG
- **File Naming:** `shot_XXX_variant_YYY.png`

### Video Generation
- **Meeting Video:** Arrival at set with iPhone
- **Departure Video:** Leaving set with final memory
- **Workflow:** wan22_flfi2v (dual image input)
- **Resolution:** Standard workflow resolution
- **Format:** MP4
- **File Naming:** `shot_XXX_variant_YYY.mp4`

### Data Flow
1. User enters movie name
2. Story agent generates JSON with characters, scenes, metadata
3. Shots generated directly (2 per character: Meeting + Departure)
4. Images generated with set prompts appended
5. Videos generated using FLFI2V workflow with both images
6. UI displays with toggle controls for mode switching

---

## File Structure

### New Files
```
agents/story/then_vs_now.md
docs/guides/THEN_VS_NOW_QUICKSTART.md
docs/guides/THEN_VS_NOW_SCENE_REQUIREMENTS.md
docs/guides/VIEWING_FLFI2V_PROMPTS.md
docs/guides/FLFI2V_SELFIE_COMPOSITION.md
docs/fixes/FLFI2V_SESSION_MANAGER_FIX.md
docs/fixes/FLFI2V_TOGGLE_BUTTONS_FIX.md
docs/fixes/IMAGE_VISIBILITY_FIX.md
docs/fixes/SHOTS_NOT_SAVED_FIX.md
docs/plans/THEN_VS_NOW_FLFI2V_IMPLEMENTATION.md
docs/testing/THEN_VS_NOW_TEST_REPORT.md
docs/verification/THEN_VS_NOW_IMPLEMENTATION_COMPLETE.md
```

### Modified Files
```
config.py
core/project_manager.py
core/story_engine.py
web_ui/backend/api/config.py
web_ui/backend/api/shots.py
web_ui/backend/models/shot.py
web_ui/backend/models/story.py
web_ui/backend/services/generation_service.py
web_ui/backend/services/project_service.py
web_ui/frontend/src/app/config/page.tsx
web_ui/frontend/src/components/shots/ShotCard.tsx
web_ui/frontend/src/components/shots/ShotGrid.tsx
web_ui/frontend/src/types/index.ts
```

---

## Status: ✅ COMPLETE

All 12 phases of the implementation plan have been successfully completed. The feature is ready for use with comprehensive documentation, bug fixes, and testing verification.

---

## Next Steps for Users

1. **Create a ThenVsNow Project:**
   - Navigate to Create Project page
   - Select "then_vs_now" from Story Agent dropdown
   - Enter a movie name (e.g., "The Godfather", "Titanic", "Back to the Future")
   - Set desired video length
   - Click "Create Project"

2. **Generate Content:**
   - Review generated story with characters and scenes
   - Generate images (both THEN and NOW will be generated)
   - Use toggle buttons to switch between THEN and NOW views
   - Generate videos (both Meeting and Departure will be generated)

3. **Export and Share:**
   - Videos can be compiled into final output
   - YouTube metadata is auto-generated for SEO optimization
   - Thumbnail prompts are movie poster-style with "THEN VS NOW" text

---

**Implementation Date:** March 12, 2026
**Total Phases:** 12
**Status:** Complete ✅
**Documentation:** Complete ✅
**Testing:** Complete ✅
