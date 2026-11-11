---
name: new-project-wizard
description: Use when the user wants to create a new video project from an idea — sets project type, directors, aspect ratio, r2v mode, generates the story, and queues shot generation.
---

# New project wizard

## 0. Blank projects
If the user wants to write the story themselves ("blank project", "empty
project", "I'll provide the story"), just `create_project` — it is already
blank (no LLM call). Then fill it in from THEIR details with `update_story`
(full story incl. scenes) or `add_scene`/`add_character`/`add_shot`, and skip
`generate_story` entirely.

## 1. Gather settings
If the user didn't specify, confirm (briefly, one question max — propose defaults):
- **Project type** — pass the NAME to create_project's `project_type`:
  `documentary` (default) · `movie` (any cinematic film/story — user says
  "cinematic movie" ⇒ `movie`) · `then_vs_now` (ONLY for then-vs-now actor
  reunion comparisons) · `asmr` (glass cutting). Never pass a number.
- **Aspect ratio**: 16:9 default; 9:16 for shorts
- **Video generation type**: i2v default; r2v when they emphasize character/reference consistency (then pick r2v_mode — singularity is the default for r2v)
- **Length**: total_duration seconds (documentary) or max_shot_duration

## 2. Pick directors
- `list_directors` to see what exists. Sensible defaults: documentary →
  `netflix_documentary`; movie → `movie/action` etc. per genre.
- r2v projects need shots directors that support references — `default` works,
  or a `base_shots_r2v_singularity`-based director for singularity mode.

## 3. Create + generate
1. `create_project` with the settings.
2. `generate_story` (LLM call, 10–60 s — tell the user it takes a moment).
3. Review: `get_project_overview`. If scene count/duration looks off, adjust with
   `update_scene` or rerun `generate_story` with a different director.
4. Character consistency matters? `generate_character_reference` for each main
   character BEFORE shot images.

## 4. Queue generation
- `batch_regenerate_shots` with `regenerate_images: true, regenerate_videos: true`
  (or images first if the user wants to review stills).
- Summarize: project id, scene/shot counts, what's queued, where to watch (Queue page).
