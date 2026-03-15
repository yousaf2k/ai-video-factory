# Implementation Plan for Narration and Scene-Shot Mapping

## Overview of the Problem

You correctly identified three major architectural issues in the current pipeline:

1. **Static Narration Length**: The story agents (`agents/story/default.md` etc.) hardcode instructions to write "2-3 sentences" regardless of the `scene_duration`. A 15s scene and a 90s scene get the exact same amount of narration.
2. **Narration in Shots vs Scenes**: Currently, `shot_planner.py` asks the LLM to put "narration" inside each shot, and `narration_generator.py` concats all shot narrations together. This is dangerous because an LLM might repeat the scene's narration for every shot in that scene, or poorly slice sentences across 5-second shots.
3. **Missing Scene Reference**: Flat shot lists don't easily map back to the scene they originated from.

## Proposed Changes

### Phase 1: Fix Narration Generation Logic

We should generate narration proportionally to `scene_duration`.

- **Modify Story Prompts**: Update `agents/story/*.md` files to replace static "2-3 sentences" with dynamic instructions: "For the narration field, generate exactly enough text to fit the scene_duration. Since average reading speed is ~2.5 words per second, a 60-second scene needs about 150 words of voice-over script, while a 15-second scene needs about 35 words."

### Phase 2: Relocate Narration to the Right Place

- **The Correct Place**: Narration belongs in the **Scene** (or the master Story), NOT broken up into individual 5-second shots. Splitting speech across 5-second shots causes awkward pauses and makes context-aware TTS fail.
- **Update Shot Planner**: Remove `narration` from the expected JSON output in `shot_planner.py` and the `image` agent prompts.
- **Update Narration Generator**: Change `narration_generator.py` to read narration from `story.json`'s `scenes` list instead of `shots.json`. It should iterate over scenes, extracting their narration.
- **Link Shots to Scenes**: Add a `scene_index` field to each generated shot so we know exactly which scene it belongs to. In `shot_planner.py`, we inject the parent `scene_index` into each shot generated for that scene.

### Phase 3: Master Story Generation

- It is highly beneficial to generate a high-level `story.txt` or a `story.json` with a single unified `master_script` field first, before breaking it down into scenes and shots. This ensures thematic consistency and exact timing control.

### Phase 4: Web UI Updates

- **Project Dashboard**: Extract `story` content during project loading so the generated `master_script` preview can be displayed directly on the front page of the web UI.
- **Dynamic Config Initialization**: Enable the backend `/api/config` endpoint to deliver the `default_max_shots` value based on `config.py`. Update the `shots planner dialog` initialization hook to default the `Max Shots` explicitly to `0` (Auto) out-of-the-box instead of `15`.

## Verification

- Run a small test pipeline to see if scenes generate proportional word counts.
- Check `shots.json` to ensure `scene_index` is present and `narration` is removed.
- Check `story.json` to ensure narration words roughly match `scene_duration * 2.5`.
