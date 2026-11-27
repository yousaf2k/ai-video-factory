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

## 1. Gather settings — ask, don't assume
Every setting the user did NOT provide is a question for the user — never
create the project on silent defaults. Collect all missing values in ONE
compact numbered message (mark your suggested default next to each so the user
can just say "ok" or override), then WAIT for the answers:
- **Idea** — required. If missing, ask what the video should be about.
- **Total duration** (`total_duration`, seconds) and **max shot duration**
  (`max_shot_duration`, 1–15 s) — ask for BOTH whenever the user hasn't stated
  them (e.g. "How long should the video be? Suggested: 60 s total, shots up to
  8 s.").
- **Project type** — pass the NAME to create_project's `project_type`:
  `documentary` (default) · `movie` (any cinematic film/story — user says
  "cinematic movie" ⇒ `movie`) · `then_vs_now` (ONLY for then-vs-now actor
  reunion comparisons) · `asmr` (glass cutting). Never pass a number. If intent
  is ambiguous, ask.
- **Aspect ratio**: 16:9 default; 9:16 for shorts — confirm if unclear.
- **Video generation type**: i2v default; r2v when they emphasize
  character/reference consistency (then pick r2v_mode — singularity is the
  default for r2v). Ask when intent is unclear.

## 2. Pick directors — show the list, let the user choose
If the user did not name a director, call `list_directors` and present the
matching story/shots directors as a short list so the user can select one —
never pick silently. Mark the sensible default: documentary →
`netflix_documentary`; movie → `movie/<genre>` per their genre (e.g.
`movie/action`).
- r2v projects need shots directors that support references — `default` works,
  or a `base_shots_r2v_singularity`-based director for singularity mode.

## 3. Create + generate
1. `create_project` with the settings — only once every required setting from
   steps 1–2 is confirmed by the user.
2. `generate_story` (LLM call, 10–60 s — tell the user it takes a moment).
3. Review: `get_project_overview`. If scene count/duration looks off, adjust with
   `update_scene` or rerun `generate_story` with a different director.
4. Character consistency matters? `generate_character_reference` for each main
   character BEFORE shot images.

## 4. Queue generation
- `batch_regenerate_shots` with `regenerate_images: true, regenerate_videos: true`
  (or images first if the user wants to review stills).
- Summarize: project id, scene/shot counts, what's queued, where to watch (Queue page).
