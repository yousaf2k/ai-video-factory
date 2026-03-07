# Google Flow & Gemini Web Integration Walkthrough

I have successfully integrated Google Flow and Gemini Web as new video generation backends for the AI Video Factory.

## Key Accomplishments

### 1. Robust Playwright Automation for Google Flow
- **Automated Workflow**: Created `core/flowweb_video_subprocess.py` to handle the end-to-end process on Google Flow: project creation, configuration (16:9/9:16, Veo 3.1 Fast), image upload, prompt injection, and generation monitoring.
- **Reliable Downloads**: Implemented a "Direct DOM Evaluation" strategy to extract video source URLs directly, ensuring successful downloads even when UI elements are hidden or slow to load.

### 2. Core Engine Enhancements
- **Dynamic Routing**: Updated `core/main.py` and `core/video_regenerator.py` to route generation tasks based on the `VIDEO_GENERATION_MODE` setting.
- **API Interfaces**: Created `core/flowweb_video_generator.py` and `core/geminiweb_video_generator.py` as clean interfaces for the subprocess scripts.

### 3. Session & Data Management
- **Multiple Variations**: Updated `SessionManager` to track `video_paths` as an array, allowing users to generate and manage multiple variations of the same shot.
- **Mark Rendered**: Refined `mark_video_rendered` to properly append new video paths to the variation list.

### 4. Frontend UI Updates
- **Mode Selection**: Added "GeminiWeb" and "FlowWeb" options to the global configuration page and the individual shot regeneration modals.
- **Variation Management**: The UI now supports switching between and deleting multiple video variations via the "Layers" gallery modal.

## Verified Components

| Component | Status | Verification Method |
| :--- | :--- | :--- |
| **Flow Automation** | ✓ PASSED | `test_flow_download.py` (Direct fetch succeeded) |
| **Main Pipeline** | ✓ READY | Code integration in `main.py` |
| **Regenerator** | ✓ READY | Code integration in `video_regenerator.py` |
| **UI Config** | ✓ READY | Added Select options in `page.tsx` & `ShotCard.tsx` |

## Proof of Work - Google Flow Download
I successfully verified that we can extract the TRPC media URL from Google Flow and download the video directly using the browser's request context.

```python
# SUCCESS: Video downloaded via direct fetch to c:/AI/ai_video_factory_v1/output/flow_direct_download.mp4
```

## How to use
1. **Configure Mode**: Go to the **Configuration** page in the Web UI and set **Video Mode** to `FlowWeb`.
2. **Generate**: Start a new session or regenerate an existing shot's video using the new backend.
3. **Verify Downloads**: Confirm that the generated videos are correctly saved to the session's folder and appear in the UI.
