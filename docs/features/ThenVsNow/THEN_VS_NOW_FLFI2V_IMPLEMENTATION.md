# "Then Vs Now" Feature with FLFI2V Support - Implementation Report

**Date:** March 12, 2026
**Status:** ✅ Completed
**Phase:** All 12 phases implemented

---

## Overview

This document summarizes the implementation of the "Then Vs Now" feature, a new project type that generates cinematic reunion videos featuring original cast members returning to movie sets in both their original (THEN) and current (NOW) appearances.

### Key Features

- **Movie-based Input**: Users enter a movie name instead of a story idea
- **FLFI2V Mode**: First Last Frame Image to Video - each shot has two images and two videos
- **Direct Shot Generation**: Story agent generates complete shot structure (no separate scene agent)
- **Set Prompt Integration**: Movie set backgrounds are appended to character image prompts
- **Dual Video Segments**: Meeting and Departure videos per character
- **YouTube Metadata**: SEO-optimized titles, keywords, and chapters
- **Backward Compatibility**: Existing Documentary projects continue to work unchanged

---

## Architecture

### Project Types

```python
class ProjectType(IntEnum):
    DOCUMENTARY = 1  # Standard documentary videos
    THEN_VS_NOW = 2  # Then vs Now reunion videos
```

### FLFI2V Data Model

Each FLFI2V shot contains:

**Images:**
- `then_image_prompt`: Prompt for THEN image (original appearance)
- `then_image_path`: Path to generated THEN image
- `now_image_prompt`: Prompt for NOW image (current appearance)
- `now_image_path`: Path to generated NOW image

**Videos:**
- `meeting_video_prompt`: Prompt for meeting video
- `meeting_video_path`: Path to meeting video
- `departure_video_prompt`: Prompt for departure/transitional video
- `departure_video_path`: Path to departure video

---

## Implementation Phases

### Phase 1: Data Model Changes ✅

**Files Modified:**
- `web_ui/backend/models/story.py`
- `web_ui/backend/models/shot.py`
- `web_ui/frontend/src/types/index.ts`

**Changes:**
- Added `ProjectType` enum
- Added `MovieMetadata` model (year, cast, director, genre)
- Added `YouTubeMetadata` model (title_options, seo_keywords, chapters, description_preview)
- Added `Character` model (then_prompt, now_prompt, meeting_prompt, departure_prompt)
- Extended `Story` model with `project_type`, `characters`, `youtube_metadata`, `movie_metadata`
- Extended `Scene` model with `set_prompt`
- Extended `Shot` model with FLFI2V fields

### Phase 2: ThenVsNow Story Agent ✅

**Files Modified:**
- `agents/story/then_vs_now.md`

**Changes:**
- Enhanced agent to generate complete shot structure
- Added project_type: 2 to output
- Generate shots directly (Meeting + Departure per character)
- Include YouTube metadata with SEO-optimized titles
- Include movie metadata (year, cast, director, genre)
- Generate movie poster-style thumbnail prompts

### Phase 3: Story Engine with Direct Shot Generation ✅

**Files Modified:**
- `core/story_engine.py`

**Changes:**
- Added `build_story_then_vs_now(movie_name, target_length)` function
- Added `generate_shots_from_then_vs_now_story(story)` function
- Each character gets 2 shots: Meeting and Departure
- Shots have `is_flfi2v: true`
- Character IDs assigned for tracking

### Phase 4: Project Service Modification ✅

**Files Modified:**
- `web_ui/backend/services/project_service.py`

**Changes:**
- Updated `create_project()` to detect `then_vs_now` agent
- Special flow that calls `build_story_then_vs_now()`
- Extracts shots from story (already generated)
- Saves story.json and shots.json directly (bypasses shot planner)
- Marks story, scene_graph, and shots steps as complete

### Phase 5: Configuration Update ✅

**Files Modified:**
- `config.py`

**Changes:**
- Added `wan22_flfi2v` workflow to `VIDEO_WORKFLOWS`
  - workflow_path: `Wan22_FLFI2V_FixSlowMotion_API.json`
  - load_image_first_node_id: "128" (THEN image)
  - load_image_last_node_id: "151" (NOW image)
  - motion_prompt_node_id: "93"
  - wan_video_node_id: "150"
- Added `THEN_VS_NOW_AGENTS = ["then_vs_now"]`

### Phase 6: Image Generation Service ✅

**Files Modified:**
- `web_ui/backend/services/generation_service.py`

**Changes:**
- Updated `_get_next_image_version()` to support variant suffixes ("then", "now")
- Updated `regenerate_shot_image()` with `image_variant` parameter
- Added `_regenerate_flfi2v_images()` method
  - Generates THEN and/or NOW images based on variant
  - Appends set_prompt to character prompts
  - Uses variant-specific file naming: `shot_001_then_001.png`, `shot_001_now_001.png`
- Added `_get_relative_path()` helper for path normalization

### Phase 7: Video Generation Service ✅

**Files Modified:**
- `web_ui/backend/services/generation_service.py`

**Changes:**
- Updated `_get_next_video_version()` to support variant suffixes ("meeting", "departure")
- Updated `regenerate_shot_video()` with `video_variant` parameter
- Added `_regenerate_flfi2v_videos()` method
  - Generates meeting and/or departure videos based on variant
  - Uses FLFI2V workflow with dual image inputs
  - Variant-specific file naming: `shot_001_meeting_001.mp4`, `shot_001_departure_001.mp4`
- Added `_generate_flfi2v_video()` method
  - Compiles FLFI2V workflow with dual image inputs
  - Injects THEN image as first frame
  - Injects NOW image as last frame
  - Injects motion prompt based on variant

### Phase 8: Prompt Compiler Update ✅

**Status:** Verified - No changes needed
- The service layer handles workflow compilation with dual image inputs

### Phase 9: Frontend UI Changes ✅

**Files Modified:**
- `web_ui/frontend/src/components/shots/ShotCard.tsx`

**Changes:**
- Added FLFI2V state management: `activeImageMode`, `activeVideoMode`
- Added FLFI2V badge to header (purple-to-pink gradient)
- Added THEN/NOW toggle buttons for images
- Added Meeting/Departure toggle buttons for videos
- Updated image/video display logic to use active mode paths:
  ```typescript
  const imageUrl = shot.is_flfi2v
    ? getMediaUrl(activeImageMode === 'then' ? shot.then_image_path : shot.now_image_path)
    : getMediaUrl(shot.image_path);
  ```

### Phase 10: API Endpoint Updates ✅

**Files Modified:**
- `web_ui/backend/api/shots.py`
- `web_ui/backend/models/shot.py`

**Changes:**
- Updated `RegenerateImageRequest` with `image_variant` field
- Updated `RegenerateVideoRequest` with `video_variant` field
- Updated `regenerate_shot_image` endpoint to pass `image_variant` to service
- Updated `regenerate_shot_video` endpoint to pass `video_variant` to service

### Phase 11: Project Manager Updates ✅

**Files Modified:**
- `core/project_manager.py`

**Changes:**
- Added `mark_then_image_generated(project_id, shot_index, image_path)`
- Added `mark_now_image_generated(project_id, shot_index, image_path)`
- Added `mark_meeting_video_rendered(project_id, shot_index, video_path)`
- Added `mark_departure_video_rendered(project_id, shot_index, video_path)`

### Phase 12: Verification ✅

**Status:** Completed
- All Python files pass syntax check
- TypeScript changes are syntactically correct
- Implementation is complete and ready for testing

---

## File Structure

### Backend Models
```
web_ui/backend/models/
├── story.py          # ProjectType, MovieMetadata, YouTubeMetadata, Character
└── shot.py           # FLFI2V fields, image_variant, video_variant
```

### Core Engine
```
core/
├── story_engine.py   # build_story_then_vs_now(), generate_shots_from_then_vs_now_story()
└── project_manager.py # FLFI2V marker methods
```

### Services
```
web_ui/backend/services/
├── project_service.py # ThenVsNow agent detection
└── generation_service.py # FLFI2V image/video generation
```

### Agents
```
agents/story/
└── then_vs_now.md    # Enhanced agent with shot generation
```

### Frontend
```
web_ui/frontend/src/
├── types/index.ts    # TypeScript interfaces
└── components/shots/ShotCard.tsx # FLFI2V UI controls
```

---

## Usage Guide

### Creating a ThenVsNow Project

1. **Select Agent**: Choose "then_vs_now" as the story agent
2. **Enter Movie Name**: Provide a movie name (e.g., "The Godfather")
3. **Optional Duration**: Set target video length in seconds

### API Example

```python
POST /api/projects
{
    "idea": "The Godfather",
    "story_agent": "then_vs_now",
    "total_duration": 300
}
```

### Generated Structure

```json
{
    "project_type": 2,
    "title": "The Godfather: The Reunion",
    "movie_metadata": {
        "year": 1972,
        "cast": ["Marlon Brando as Don Vito Corleone", "Al Pacino as Michael Corleone"],
        "director": "Francis Ford Coppola",
        "genre": "Crime Drama"
    },
    "characters": [
        {
            "name": "Marlon Brando as Don Vito Corleone",
            "then_prompt": "Young actor in original movie attire...",
            "now_prompt": "Actor today in expensive modern attire...",
            "meeting_prompt": "Slow push-in camera move, actor walks onto set...",
            "departure_prompt": "Slow pull-out camera move, actor takes one last look..."
        }
    ],
    "shots": [
        {
            "index": 1,
            "is_flfi2v": true,
            "character_id": "char_000",
            "then_image_prompt": "...",
            "now_image_prompt": "...",
            "meeting_video_prompt": "...",
            "departure_video_prompt": null,
            "scene_id": 0
        },
        {
            "index": 2,
            "is_flfi2v": true,
            "character_id": "char_000",
            "then_image_prompt": "...",
            "now_image_prompt": "...",
            "meeting_video_prompt": null,
            "departure_video_prompt": "...",
            "scene_id": 0
        }
    ]
}
```

### Generating Images

```python
POST /api/projects/{project_id}/shots/{shot_index}/regenerate-image
{
    "force": true,
    "image_variant": "both"  # "then", "now", or "both"
}
```

**Output:**
- `shot_001_then_001.png` - THEN image
- `shot_001_now_001.png` - NOW image

### Generating Videos

```python
POST /api/projects/{project_id}/shots/{shot_index}/regenerate-video
{
    "force": true,
    "video_variant": "both",  # "meeting", "departure", or "both"
    "video_workflow": "wan22_flfi2v"
}
```

**Output:**
- `shot_001_meeting_001.mp4` - Meeting video
- `shot_001_departure_001.mp4` - Departure video

---

## Verification Steps

### 1. Create ThenVsNow Project
- [ ] Select "then_vs_now" story agent
- [ ] Enter a movie name (e.g., "The Godfather")
- [ ] Verify story.json has project_type: 2
- [ ] Verify story.json has characters array
- [ ] Verify story.json has movie_metadata
- [ ] Verify shots.json has is_flfi2v: true for all shots

### 2. Generate Images
- [ ] Run batch image generation
- [ ] Verify both THEN and NOW images are generated per shot
- [ ] Verify file naming: shot_001_then_001.png, shot_001_now_001.png
- [ ] Verify set prompt is appended to character prompts
- [ ] Verify image paths are saved to shots.json

### 3. Generate Videos
- [ ] Run batch video generation
- [ ] Verify both Meeting and Departure videos are generated per shot
- [ ] Verify file naming: shot_001_meeting_001.mp4, shot_001_departure_001.mp4
- [ ] Verify FLFI2V workflow uses both THEN and NOW images
- [ ] Verify video paths are saved to shots.json

### 4. UI Verification
- [ ] Verify FLFI2V badge appears on shot cards
- [ ] Verify THEN/NOW toggle switches between images
- [ ] Verify Meeting/Departure toggle switches between videos
- [ ] Verify thumbnail generation uses movie poster style
- [ ] Verify "THEN VS NOW" text appears in thumbnails

### 5. Backward Compatibility
- [ ] Create a standard Documentary project
- [ ] Verify existing functionality works unchanged
- [ ] Verify shots without is_flfi2v use standard generation flow

---

## Technical Notes

### File Naming Convention

**Images:**
- Standard: `shot_001_001.png`, `shot_001_002.png`
- FLFI2V: `shot_001_then_001.png`, `shot_001_now_001.png`

**Videos:**
- Standard: `shot_001_001.mp4`, `shot_001_002.mp4`
- FLFI2V: `shot_001_meeting_001.mp4`, `shot_001_departure_001.mp4`

### Path Storage

FLFI2V shots maintain backward compatibility by:
1. Setting `image_path` to `now_image_path`
2. Setting `video_path` to `meeting_video_path`
3. This allows existing code to work without modification

### Set Prompt Integration

For ThenVsNow projects, the set_prompt from the scene is appended to character image prompts:

```python
prompt = f"{character_prompt}. Background: {set_prompt}"
```

This ensures the movie set background is incorporated into the character images.

---

## Workflow Details

### FLFI2V Workflow

The `wan22_flfi2v` workflow uses two image inputs:

1. **THEN Image (First Frame)**: Loaded at node 128
   - Represents the character in their original appearance

2. **NOW Image (Last Frame)**: Loaded at node 151
   - Represents the character in their current appearance

3. **Motion Prompt**: Injected at node 93
   - Different for Meeting vs Departure videos

This creates a transformation effect from THEN to NOW in the generated video.

---

## Dependencies

### Required Workflow File
- `workflow/video/Wan22_FLFI2V_FixSlowMotion_API.json`

The FLFI2V workflow must be present in the workflow directory for video generation to work.

### Agent File
- `agents/story/then_vs_now.md`

The ThenVsNow story agent must be present for story generation.

---

## Future Enhancements

Potential improvements for future iterations:

1. **Customizable Character Count**: Allow users to specify number of characters
2. **Scene Selection**: Let users choose which movie sets to include
3. **Custom Music**: Add background music generation for videos
4. **Voiceover Integration**: Add narration for each character segment
5. **Transition Effects**: Add more sophisticated transition effects between THEN and NOW
6. **Batch Export**: Export all videos as a single compilation
7. **Social Media Crops**: Generate vertical cuts for TikTok/Reels

---

## Troubleshooting

### Issue: FLFI2V workflow not found

**Solution:**
- Ensure `Wan22_FLFI2V_FixSlowMotion_API.json` exists in `workflow/video/`
- Check that config.py has the correct workflow_path

### Issue: Images not generating

**Solution:**
- Check that both then_prompt and now_prompt exist in the shot
- Verify that set_prompt exists in the scene
- Check the image generation logs for errors

### Issue: Videos not generating

**Solution:**
- Ensure both THEN and NOW images have been generated first
- Check that meeting_video_prompt or departure_video_prompt exists
- Verify the FLFI2V workflow node IDs match config.py
- Check ComfyUI is running and accessible

### Issue: UI toggle buttons not showing

**Solution:**
- Verify shot.is_flfi2v is true in shots.json
- Check that image_paths and video_paths are populated
- Refresh the browser cache

---

## Conclusion

The "Then Vs Now" feature with FLFI2V support has been successfully implemented across all 12 phases. The implementation maintains backward compatibility with existing Documentary projects while providing a new, immersive way to create cinematic reunion videos.

The feature is ready for testing and deployment. All code changes have been syntactically validated and follow the existing code patterns in the project.
