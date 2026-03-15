# Gemini Web & Google Flow Video Generation

This plan outlines the steps to add support for generating videos using the Gemini Web UI (Veo 3.1) and Google Flow, and to support video variations in the UI.

> [!NOTE]
> All tasks for this implementation plan are now COMPLETE.

## Proposed Changes

### Core Engine & Playwright (Gemini Web Video)

#### [MODIFY] [config.py](file:///c:/AI/ai_video_factory_v1/config.py)
- Explicitly add `VIDEO_GENERATION_MODE = "comfyui"` to the file to make it easily configurable and configurable by the web API.

#### [NEW] [core/geminiweb_video_generator.py](file:///c:/AI/ai_video_factory_v1/core/geminiweb_video_generator.py)
- Create a new script containing `generate_video_geminiweb()`.
- Wait for a generation lock.
- Construct the command to launch the `geminiweb_video_subprocess.py`.
- Handle the subprocess output to extract the downloaded video path.

#### [NEW] [core/geminiweb_video_subprocess.py](file:///c:/AI/ai_video_factory_v1/core/geminiweb_video_subprocess.py)
- Standalone Playwright script for Gemini Web.
- Read `image_path`, `motion_prompt`, and `output_path` from command line arguments.
- Navigate to `gemini.google.com/app`.
- Upload the `image_path`.
- Inject the prompt: "Generate a video: [motion_prompt]" into the chat box.
- Submit and wait for response. 
- Wait for the download button or intercept network to download the `.mp4` file to `output_path`.

#### [NEW] [core/flowweb_video_generator.py](file:///c:/AI/ai_video_factory_v1/core/flowweb_video_generator.py)
- Create a new script containing `generate_video_flowweb()`.
- Wait for a generation lock.
- Construct the command to launch the `flowweb_video_subprocess.py`.
- Handle the subprocess output to extract the downloaded video path.

#### [NEW] [core/flowweb_video_subprocess.py](file:///c:/AI/ai_video_factory_v1/core/flowweb_video_subprocess.py)
- Standalone Playwright script for Google Flow.
- Read `image_path`, `motion_prompt`, `aspect_ratio`, and `output_path` from command line arguments.
- Navigate to `labs.google/fx/tools/flow`.
- Create new project, configure options (Landscape/Portrait, Veo 3.1 Fast).
- Upload image reference and wait for processing.
- Type prompt and click Create button.
- Monitor grid for completion, click download, and rename video to `output_path`.

#### [MODIFY] [core/main.py](file:///c:/AI/ai_video_factory_v1/core/main.py)
- Enhance the video generation loop to route based on `VIDEO_GENERATION_MODE`.

#### [MODIFY] [core/video_regenerator.py](file:///c:/AI/ai_video_factory_v1/core/video_regenerator.py)
- Update regeneration logic to handle the new backend modes.

### Project Management

#### [MODIFY] [core/project_manager.py](file:///c:/AI/ai_video_factory_v1/core/project_manager.py)
- Track multiple `video_paths` in the shot object to allow variations.

### Backend API

#### [MODIFY] [web_ui/backend/api/shots.py](file:///c:/AI/ai_video_factory_v1/web_ui/backend/api/shots.py)
- Add endpoints for selecting and deleting video variations.

### Frontend UI

#### [MODIFY] [web_ui/frontend/src/types/index.ts](file:///c:/AI/ai_video_factory_v1/web_ui/frontend/src/types/index.ts)
- Update `Shot` interface with `video_paths`.

#### [MODIFY] [web_ui/frontend/src/components/shots/ShotCard.tsx](file:///c:/AI/ai_video_factory_v1/web_ui/frontend/src/components/shots/ShotCard.tsx)
- Add variation management UI for videos.
- Update regeneration modal with new mode options.
