---
name: project-health-check
description: Use when the user asks for a project audit/status/checkup — missing media, failed steps, stale queue items, incomplete narration, and suggested next actions.
---

# Project health check

Produce a compact report:

## 1. Snapshot
- `get_project_overview` → steps completed, stats, per-shot status grid, errors map.

## 2. Find gaps
- Shots where `image_generated` is false but the queue has no pending IMAGE item
  → stuck; requeue with `generate_shot_image`.
- Shots with an image but `video_rendered` false → queue `generate_shot_video`.
- `soundfx_generated` false where the project uses SFX.
- Scenes without `narration_path` → offer `generate_scene_narration`.
- `meta.errors` non-empty → summarize each failed step and its error.

## 3. Queue sanity
- `get_queue` filtered by status failed/paused → list items with `error_message`;
  offer `queue_action` (requeue/resume) or cancellation.

## 4. Files
- `list_files` (root=project) → flag empty videos/ or images/ dirs while stats
  claim generations (paths may point at deleted files).

## 5. Report format
A markdown table: Shot | Image | Video | SFX | Narration — then a "Suggested
next actions" list. ALWAYS ask before queueing anything (batch regeneration
spends GPU time).
