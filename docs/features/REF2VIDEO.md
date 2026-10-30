# Ref2Video & Video Generation Types

> 📚 [Docs Index](../DOCS_INDEX.md) › Features › Ref2Video
>
> Implementation plan: [development/plans/REF2VIDEO_MODE_PLAN.md](../development/plans/REF2VIDEO_MODE_PLAN.md)

## Overview

Projects carry a standalone **video generation type setting** — the visual input strategy
for shot videos, independent of (and combinable with) the existing project types
(documentary, then-vs-now, movie, ASMR):

| Type | Name | Visual inputs | Pipeline |
| --- | --- | --- | --- |
| `i2v` | Image to Video (default) | generated first-frame image per shot | today's standard pipeline |
| `r2v` | Reference to Video | character / background / prop **reference sheets** — no first frame | MiniMax H3 Reference-to-Video |
| `t2v` | Text to Video | none — prompt only | MiniMax H3 r2v workflow with zero refs, or any no-reference workflow |

The type is a **project-level setting** (`video_generation_type` in project meta), chosen
in the creation form's "Video Generation" selector (or via `--video-generation-type`) and
stored on `meta.json`; the existing `ProjectType` values are unchanged. All backend logic
branches on this field — never on the project-type enum.

```bash
# CLI
python core/main.py --idea "A baker opens his shop at dawn" \
  --video-generation-type r2v \
  --video-workflow minimax_h3_r2v

# r2v with the enhanced Singularity prompt format (also the web UI default)
python core/main.py --idea "A baker opens his shop at dawn" \
  --video-generation-type r2v --r2v-mode singularity

# t2v: the simplest path — prompt in, video out
python core/main.py --idea "A storm over the mountains" --video-generation-type t2v
```

## r2v Prompt Modes (Standard vs Singularity)

`r2v` projects additionally carry an **`r2v_mode`** — which full-reference prompt format
the shots director uses (and which checkpoint family renders by default):

| Mode | Shots director | Format | Default video workflow |
| --- | --- | --- | --- |
| `standard` | `base/base_shots_r2v` | six-section full-reference prompt ([Ref2VA guide](../guides/Minimax_H3_VIDEO_PROMPT_WRITING_GUIDE_ref_en.md)) | `minimax_h3_r2v` |
| `singularity` | `base/base_shots_r2v_singularity` | enhanced `id` + six-section prompt per the [Singularity specification](../guides/MiniMax_H3_Singularity_Prompt_Writing_Specification_Enhanced_EN.md) | `minimax_h3_r2v_singularity_v20_4s` (falls back to any `minimax_h3_r2v_singularity*`, then `minimax_h3_r2v`) |

- **Singularity** prompts keep the six named sections (so the composer's structural
  validation and voice-text embedding work unchanged) but add the enhanced writing rules:
  action chains (preparation → trigger → contact → recovery), five-element camera specs,
  VFX as trigger + form + motion + consequence, physical feedback, observable
  lighting/material behavior, micro-acting, and cross-shot continuity/damage carry-forward.
- Mode is set at creation (`r2v_mode` on create/update requests; CLI `--r2v-mode`;
  web UI "Reference Mode" sub-select, defaulting to **Singularity**) and stored on
  `meta.json`. Projects without the field (pre-Singularity) resolve to `standard`.
- Changing the mode swaps the sibling r2v base director on replan; rendering then targets
  the matching checkpoint family unless a workflow was chosen explicitly.
- The Singularity workflows differ from the standard r2v ones **only in the UNET
  checkpoint** (`Minimax-h3_Singularity_ref2va_v2_pruned_int8` for the `v20` variants,
  `..._v1.3_Pruned_w4a8` for `v13`); the `_4s`/`_8s` suffix is the usual steps preset.

## r2v Pipeline

```
Idea → Story → Scene Graph → Shots (r2v director)
                          ↓
   Character sheets (8-view)  +  Scene backgrounds  +  Prop sheets   (once each, idempotent)
                          ↓
   sync_shot_video_refs: attach refs to shots in priority order
   (characters → scene background → props, capped at 9 image slots)
                          ↓
   MiniMax H3 Reference-to-Video per shot (NO first-frame image)
                          ↓
   video with native audio (dialogue, SFX, music — all authored in the prompt)
```

- **Shot prompts** use the MiniMax H3 **full-reference format** (six sections:
  `subject_definitions`, `summary`, `retention_analysis`, `detailed_description`,
  `overall_soundscape`, `non_diegetic_music`) — see the
  [Ref2VA guide](../guides/Minimax_H3_VIDEO_PROMPT_WRITING_GUIDE_ref_en.md). Prompts are
  capped at 7000 characters (validated + LLM-repaired).
- **Shots directors**: `base/base_shots_r2v` (r2v standard), `base/base_shots_r2v_singularity`
  (r2v singularity) and `base/base_shots_t2v` (t2v) — enforced for r2v/t2v projects in both
  the CLI and the web UI: the unset default, the I2VA `base/base_shots_standard` base, or a
  sibling r2v base is swapped for the format-correct one (camera/style/context packs are
  kept); other explicit directors pass through unchanged.
- **`<Picture N>` convention**: references attach characters-first, then the scene
  background, then props; the composer prunes citations for refs the 12-file/9-slot budget
  dropped and embeds each character's **voice text** verbatim so voices stay consistent
  across separately generated clips.
- **Voice IDs**: characters carry `voice: {type: "text"|"audio", text: "...", ref: "..."}`.
  The text voice is embedded in every shot prompt where the character appears; an audio
  voice additionally references a sample asset (timbre anchor — used by the pipeline once
  the node's audio inputs land).
- **Workflow**: `workflow/video/minimax_h3_r2v.json` wires 9 tagged `[ref_0..8]`
  reference slots; unfilled slots are simply omitted from the submission. The `Ns` suffix
  in H3 workflow filenames = N sampling **steps** (speed/quality preset), never seconds.
- r2v/t2v require the ComfyUI engine (`VIDEO_GENERATION_MODE=comfyui`).

## What each piece is

- **Character sheet** — one 8-view identity image per character (4 full-body + 4 face
  close-ups), `images/` dir, stored at `characters[].character_reference_image_path`.
  Optional per-character **expression sheet** (6-expression grid) as an identity anchor for
  close-ups.
- **Background sheet** — one environment image per scene (no characters), `backgrounds/`
  dir, `scenes[].background_image_path`.
- **Prop sheet** — one product-style image per story prop (`props[]` in story.json with
  `name/category/image_prompt/owner`), `references/` dir, `props[].reference_image_path`;
  queue type `PROP_IMAGE`, API `POST /api/projects/{id}/stories/props/{idx}/generate-reference`.
- **Reference attachment** — `ProjectManager.sync_shot_video_refs()` fills each shot's
  `reference_asset_ids` in priority order (r2v projects only; supersedes the character-ref
  sync there; manual refs preserved; idempotent).

## Web API additions

- `CreateProjectRequest` / `UpdateProjectRequest`: `video_generation_type` (`t2v| i2v| r2v`)
  and `r2v_mode` (`standard` | `singularity`, r2v only) — standalone validated fields;
  existing project types are untouched and any type can run any video generation type.
- Batch generation for r2v queues **reference sheets first** (characters → backgrounds →
  props); video items don't wait on images, and an explicit batch image request is honored
  (parity with single-shot generation).
- Single-shot video generation works without an image in r2v/t2v projects.
- **Background styles**: `styles.json` (repo root) holds named `name`/`style` pairs served by
  `GET /api/config/styles` (re-read per call — edits apply without a restart). The story tab's
  scene-background manager and the r2v batch-images modal offer a style dropdown; the selected
  style text is appended to the **end** of the background prompt at generation time
  (`background_style` request/queue field, `apply_background_style()` helper).
- **Background prompt comes from `set_prompt`**: the story directors' shared schema
  (`directors/story/_base/base_story_format.md`) has the story LLM write a detailed environment
  description into each scene's `set_prompt` (location stays a short setting name). Background
  sheets build from `set_prompt` (`background_base_text()`; `location` is the fallback for
  stories generated before the field existed). The per-scene sheet template and the batch
  sheet queue both use it — batch items carry no `prompt_override`, which used to replace the
  built prompt with the raw location.

## Regeneration

`python regenerate.py --project <id> --videos` renders r2v/t2v shots without images (the
CLI image precondition is relaxed for these projects).

## Related docs

- [Ref2VA prompt guide](../guides/Minimax_H3_VIDEO_PROMPT_WRITING_GUIDE_ref_en.md)
- [Singularity prompt specification](../guides/MiniMax_H3_Singularity_Prompt_Writing_Specification_Enhanced_EN.md)
- [Base prompt guide (T2VA/I2VA)](../guides/Minimax_H3_VIDEO_PROMPT_WRITING_GUIDE_base_en.md)
- [Configuration reference](../getting-started/CONFIGURATION.md)
- [Implementation plan](../development/plans/REF2VIDEO_MODE_PLAN.md)
