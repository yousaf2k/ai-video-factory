# Plan: Full Automation Pipeline for AI Video Generation

## Objective

To achieve full automation of the AI video generation system, focusing on improving story cohesion, narration timing, and generating a master story script that orchestrates the entire process.

## Key Features & Phases

### Phase 1: Dynamic Narration Length

- **Problem**: Narration was statically constrained to `(2-3 sentences)` across 16 different story agents. This caused pacing issues where 60s or 75s scenes had dead air.
- **Solution**: Replaced hardcoded constraints with a dynamic instruction: `Write EXACTLY enough text to fill the scene_duration. Since average speaking rate is ~2.5 words per second, a 60-second scene needs ~150 words of narration.`

### Phase 2: Scene-Level Narration & Shot Linking

- **Problem**: Narration generation logic existed inside `shots.json`, which lacked context about the overall scene flow. Shots were detached from scenes.
- **Solution**: Removed narration generation from shot-level config. Moved narration extraction and logic to the _Scene_ level so the voiceover matches the entire scene block simultaneously while individual visual `<shots>` render underneath.

### Phase 3: Master Story Generation

- **Problem**: No single source of truth existed for a generated story, making scene regenerations difficult.
- **Solution**: Created a `master_script` (inside `story.json`) that dictates the comprehensive narrative flow BEFORE breaking down into distinct scenes and shots.

### Phase 4: UI Enhancements & Stability

- Added the generated `master_script` as a preview string on the `/projects` Next.js frontend dashboard.
- Mapped Max Shots dynamically from `config.py` as a configuration dialog setting (`0` = Auto).
- Fixed `[WinError 10055]` socket exhaustion by pooling REST API calls to ComfyUI and LLMs via `requests.Project`.
