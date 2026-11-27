---
name: empty-project-builder
description: Use when the user wants a project built BY HAND with no LLM story generation — create an empty project, ask for duration/max shot duration/aspect ratio, then add characters, props and scenes, budget shots per scene until the total duration is filled, attach references per generation mode (i2v/r2v), and write MiniMax H3 video prompts.
---

# Empty (hand-built) project builder

Build a complete project shot-by-shot WITHOUT `generate_story` — the user (or
you, with their approval) authors every character, prop, scene and shot
directly. For an LLM-generated story use `new-project-wizard` instead.

## 0. Ask first — never assume

Collect anything the user has NOT already provided in ONE compact numbered
message (mark your suggested default next to each) and WAIT for the answers:
- **Idea / project name** — required.
- **Total duration** (`total_duration`, seconds) — the shot budget target.
- **Max shot duration** (`max_shot_duration`, 1–15 s) — e.g. 8; H3 renders
  1–15 s clips.
- **Aspect ratio** — 16:9 (default) / 9:16 (shorts) / 21:8.
- **Generation mode** — i2v or r2v (r2v when they emphasize character/reference
  consistency). This decides the whole reference flow (step 5) and the prompt
  format (step 6).

## 1. Create the blank project

`create_project` with the confirmed settings. Rules:
- `project_type` MUST be `movie` or `documentary` — `then_vs_now` and `asmr`
  auto-run LLM story generation at creation and are NOT blank.
- Set `prompt_mode: "video"` (H3 timestamped `video_prompt`s). For r2v also
  set `video_generation_type: "r2v"` (+ `r2v_mode: "singularity"` unless the
  user picked standard).
- Keep the returned `project_id`. The project has NO story yet.

## 2. Seed the story skeleton

`add_character` / `add_scene` fail while `story.json` is missing, so FIRST call
`update_story` with a minimal skeleton (it must contain a `scenes` array):

```json
{"title": "<name>", "style": "<look/genre>", "total_duration": <n>,
 "scenes": [], "characters": [], "props": []}
```

## 3. Characters and props

- One `add_character` per character: `name` + a concrete `image_prompt`
  describing stable identity (face, hair, body, outfit colors) — this exact
  text feeds the reference sheet, so make it repeatable. Add `attire`,
  `personality`, `voice_type` when known.
- Props live in `story.props` and there is NO add_prop tool: `get_story`,
  append `{"name": ..., "image_prompt": ...}` objects to `props`, then
  `update_story` with the FULL story object (it replaces everything — never
  send a partial story).

## 4. Scenes

One `add_scene` per scene with `location`, `action`, `characters` (comma-
separated names), `emotion` and `scene_duration` (int >= 5). Plan the scene
durations so they sum to the total duration.

## 5. Shot budget — stop when the duration is filled

Track a running `remaining = total_duration`. For each scene in order:
- `shots = max(1, ceil(scene_duration / max_shot_duration))`; more shots for
  denser action, fewer for slow establishing beats.
- Give each shot an integer `duration` so the scene's shots sum to its
  `scene_duration` (let the last shot take the remainder) and the whole
  project sums to `total_duration`. Every duration stays within
  1..max_shot_duration (H3 clip limit 15 s).
- **STOP adding shots the moment the allocated duration is reached** — never
  overrun `total_duration`.
- One `add_shot` per shot: `image_prompt` (first-frame description — required
  by the tool even in r2v), `motion_prompt` (one-paragraph action summary),
  `camera`, `duration`, `scene_id`, `narration`, `soundfx_prompt`.
- r2v cast link: per-shot reference resolution uses the shot's `characters`
  list (fallback `character_name`) and `props` list. `add_shot` can't set
  them — after adding shots, set `character_name` via `update_shot` per shot,
  or one `update_shots_bulk` pass to add `characters`/`props` name arrays.
- Verify at the end: `get_project_overview` / `list_shots` —
  sum(durations) must equal `total_duration`; trim or extend the final shots
  if not.

## 6. References per generation mode

Queue these AFTER the story is complete (check `get_queue`):
- **r2v** — NO per-shot images, never call `generate_shot_image`:
  `generate_character_reference` per character, `generate_scene_background`
  per scene, `generate_prop_reference` per prop. Sheets auto-attach to shots
  in order **characters → scene background → props** (max 9 slots) and
  `<Picture N>` numbering follows that exact order.
- **i2v** — `generate_character_reference` per main character first, then
  `generate_shot_image` per shot (first frames; videos are generated after
  images complete).
- **t2v** — nothing: no references, no shot images at all.

## 7. Video prompts — MiniMax H3 format

Every shot gets a `video_prompt` and `prompt_type: "video"` (the project's
`prompt_mode: "video"` also covers this). READ the authoritative format first
with `read_director` (`director_type: "shots"`) — never write H3 prompts from
memory:
- i2v → `videoprompt/videoprompt_minimax_h3` — starts with the first-frame
  line ("For the target video, at 0.00 seconds… <Picture 1> (from [Shot 1])…"),
  then `integrated_multimodal_description` (timestamped sub-shots, camera
  motion, `<d>` dialogue), `overall_soundscape`, `non_diegetic_music`.
- r2v → `videoprompt/videoprompt_minimax_h3_r2v` — six sections
  (`subject_definitions` citing `<Picture N>`, `summary` with the
  `[reference generation]` prefix, `retention_analysis`,
  `detailed_description`, `overall_soundscape`, `non_diegetic_music`).
  Singularity projects (`r2v_mode: singularity`) →
  `videoprompt/videoprompt_minimax_h3_r2v_singularity` (adds action chains,
  five-element camera specs, VFX grammar).
- t2v → `videoprompt/videoprompt_minimax_h3_t2v`.
Keep subject and voice definitions IDENTICAL across shots of the same
character. The enhanced Singularity spec lives at
`docs/guides/MiniMax_H3_Singularity_Prompt_Writing_Specification_Enhanced_EN.md`
(read with `read_file` if you need the full ruleset).

## 8. Generate and verify

- i2v: `batch_regenerate_shots` images first (review stills), then videos.
- r2v: wait for the sheets, then `batch_regenerate_shots` with
  `regenerate_images: false, regenerate_videos: true`.
- `get_queue` for progress; `get_project_overview` shows `reference_ready`.
- Summarize: project id, scene/shot table with durations, total duration vs
  target, what's queued, where to watch (Queue page).
