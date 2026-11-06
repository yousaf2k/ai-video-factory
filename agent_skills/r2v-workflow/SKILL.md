---
name: r2v-workflow
description: Use for ANY task on a Reference-to-Video (r2v) project — fixing shots, changing how characters/scenes/props look, editing video prompts (six-section full-reference format), or deciding which generation tool to call. Prevents the classic mistake of trying to generate per-shot images.
---

# Reference-to-Video (r2v) workflow

r2v projects render each shot's video from **reference images + a full-reference
prompt** (MiniMax H3). There are **no per-shot first-frame images** — never call
`generate_shot_image` and never batch-regenerate images.

## Where visuals come from

| Reference | Tool | Stored on |
|---|---|---|
| Character 8-view sheet (4 full-body + 4 face close-ups) | `generate_character_reference` | `characters[].character_reference_image_path` |
| Scene background (environment only, no characters) | `generate_scene_background` | `scenes[].background_image_path` |
| Prop sheet (product-style) | `generate_prop_reference` | `props[].reference_image_path` |

References auto-attach to every shot via `sync_shot_video_refs` in priority order
**characters → scene background → props**, capped at 9 image slots; manual
`reference_asset_ids` on a shot are preserved. Check readiness with
`get_project_overview` (it lists `reference_ready` per character/scene/prop).

## Decision table for "shot N is wrong"

| User complaint | Real cause | Fix |
|---|---|---|
| Character looks wrong / wrong face / wrong outfit | character sheet | `update_character` image_prompt → `generate_character_reference` → re-render affected shots |
| Location/setting wrong | scene background | `update_scene` → `generate_scene_background` |
| A prop/object looks wrong | prop sheet | `update_story` prop image_prompt → `generate_prop_reference` |
| Action, motion, timing, camera, dialogue, SFX wrong | the shot's prompt | `update_shot` video_prompt (keep section structure) → `generate_shot_video` |
| Wrong character in the shot at all | story/scene cast or shot prompt | `update_scene` characters or rewrite the shot's subject section, then re-render |

After regenerating a reference, the *already rendered* videos keep the old look —
re-render the shots (`generate_shot_video`, `force: true`) once the new reference
is done.

## The video prompt format (six sections)

Shots in r2v projects carry a `video_prompt` in the MiniMax H3 **full-reference
format** (≤7000 chars). When editing, PRESERVE the structure — edit the section
that's wrong, don't rewrite the whole prompt:

```
subject_definitions:   each character/prop with its <Picture N> reference citation + voice
summary:               one-paragraph what happens in this shot
retention_analysis:    which reference features must persist (face, outfit, prop details)
detailed_description:  action beats, camera, lighting — the part that fixes "wrong action"
overall_soundscape:    diegetic audio (dialogue, SFX, ambience)
non_diegetic_music:    music direction
```

- `<Picture N>` numbers refer to the auto-attached references (characters first,
  then background, then props). Don't invent numbers — check how existing shots
  cite them (`get_shot`).
- Character **voice text** is embedded verbatim in every shot the character
  appears in — keep it identical across shots so voices stay consistent.
- `r2v_mode: singularity` projects add action chains
  (preparation → trigger → contact → recovery), five-element camera specs and
  VFX grammar (trigger + form + motion + consequence) inside the same sections.
- Prefer `replan_shots` (uses the r2v-aware shots director) over hand-writing
  all shots when the story itself changed.
