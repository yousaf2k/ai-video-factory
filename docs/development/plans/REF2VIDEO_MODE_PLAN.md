# Ref2Video Mode — Design & Implementation Plan

> 📚 [Docs Index](../../DOCS_INDEX.md) › Development › Plans › Ref2Video Mode Plan
>
> Status: **implemented (phases 0–4)** — see [docs/features/REF2VIDEO.md](../../features/REF2VIDEO.md)
> for usage. Phase 5 (audio/video reference attachment, voice sample synthesis) remains
> future work pending the updated node's video/audio inputs.
> Feature: a **new project type** whose creation flow lets the user select a video
> generation type — text-to-video (`t2v`), image-to-video (`i2v`, today's pipeline), or
> reference-to-video (`r2v`). This plan details the r2v pipeline — reference sheets
> (characters + scene backgrounds + props) attached directly to a MiniMax H3
> **Reference-to-Video** generation, with all dialogue and audio authored in the prompt —
> plus the shared machinery all three types need (project type, image-gate bypass, prompt
> formats).

---

## 1. Concept

Today the pipeline is I2VA-based: for every shot it generates a first-frame image
(Krea/Gemini/GeminiWeb), then animates that image with an image-to-video workflow
(default `minimax_h3_i2v`).

The video generation type is chosen at **project creation** (D1): `i2v` keeps this
pipeline, `r2v` is this plan's pipeline, and `t2v` generates directly from the prompt with
no visual inputs at all.

**ref2video** removes the per-shot image stage:

```
Idea → Story → Scene Graph → Shots
              ↓                ↓
   Character sheets      Background sheet per scene     (once per character / scene)
              ↘                ↙
        (attach as reference images per shot)
                       ↓
          MiniMax H3 Reference-to-Video                (per shot, NO first frame)
                       ↓
        video with native audio (dialogue, SFX, music generated from the prompt)
```

Key properties:

1. **Character sheets** (already exist): one 8-view sheet per character
   (4 full-body + 4 face close-ups), stored at `characters[].character_reference_image_path`.
2. **Background sheets** (mostly exists): one environment reference image per scene,
   stored at `scenes[].background_image_path` in the project `backgrounds/` dir.
3. **No first-frame image generation** — the shot image stage is skipped entirely.
4. **Per-shot video** via `MiniMaxH3ReferenceToVideo`: the shot's relevant character
   sheets + its scene's background sheet are attached as `ref_images`, and the prompt is
   written in the **full-reference format** (`subject_definitions` / `summary` /
   `retention_analysis` / `detailed_description` / `overall_soundscape` /
   `non_diegetic_music`) per `docs/guides/Minimax_H3_VIDEO_PROMPT_WRITING_GUIDE_ref_en.md`.
5. **All audio in the prompt**: dialogue as `<d>[Language] ...</d>` with stable speaker IDs
   `(S1)…`, ambience in `overall_soundscape`, score in `non_diegetic_music`. The H3 model
   generates the audio track natively (the workflow already decodes it via `VAEDecodeAudio`).
6. **Props** (v2 addition): recurring objects — vehicles, weapons, electronics, wearables,
   notable outfits — get a story-level definition and an optional reference sheet each, and
   are attached to the shots that use them (see D10).
7. **Optional expression sheets** (v2 addition): per-character, user-triggered facial
   expression grids that can auto-attach on close-up shots (see D11).
8. **Optional post audio layers**: existing per-shot SFX (MMAudio) and BGM/narration mixing
   at export keep working because shot MP4s carry their own audio track.

---

## 2. What already exists (reuse map)

| Piece | Location | State |
| --- | --- | --- |
| R2V ComfyUI workflow (2 wired ref slots, prompt node, duration math, Lightning-LoRA switch, audio decode) | `workflow/video/video_minimax_h3_r2v.json`, `video_minimax_h3_r2v_8s.json` | ✅ present — **we modify these in place to our requirements** (D5); currently not pipeline-ready (see §4) |
| Workflow registered in `VIDEO_WORKFLOWS` | `config.py` dynamic discovery | ⚠️ detected as FLFI2V-style (`load_image_first/last_node_id`), no `motion_prompt_node_id` |
| Full-reference prompt format guide | `docs/guides/Minimax_H3_VIDEO_PROMPT_WRITING_GUIDE_ref_en.md` | ✅ |
| I2VA shots director (dialogue, cuts, camera, soundscape rules) | `directors/shots/videoprompt/videoprompt_minimax_h3.md` | ✅ — basis for the R2V director |
| Character sheet generation (single 8-view image, `images/` dir, queue type `CHARACTER_IMAGE`) | `web_ui/backend/services/generation_service.py:476-619` | ⚠️ backend-only — port to `core/` (D6) |
| Scene background generation (`backgrounds/` dir, `scene.background_image_path`) | `generation_service.py:762-796`, `:2714-2823` | ⚠️ latent bug — `_generate_single_image` called with 11 positional args vs 10-param signature (`:2762-2776`); fix first |
| Asset-reference system (`p/{pid}/{media_dir}/{file}`), `collect_shot_image_refs` | `web_ui/backend/services/asset_service.py:786-870` | ✅ |
| Character-ref→shot attachment pattern | `core/project_manager.py:112-191` (`sync_character_asset_refs`) | ✅ — template for the new ref sync |
| Prompt/duration/seed injection into video workflows | `core/prompt_compiler.py` (`compile_workflow`) | ✅ — needs multi-ref extension |
| Per-request workflow/mode overrides in queue items | `generation_service.py:887-978` | ✅ |
| Multi-track export with audio mixing | `web_ui/backend/services/export_service.py` | ✅ |

---

## 3. Design decisions (with alternatives considered)

### D1 — A new project type with a video-generation-type selection

This is **not** a generation *engine* mode — `VIDEO_GENERATION_MODE` already means engine
(`comfyui` / `geminiweb`) and stays untouched. It is a **new project type**: creating a
project of this type asks the user for its **video generation type**:

| `video_generation_type` | Pipeline | Visual inputs |
| --- | --- | --- |
| `i2v` (image to video) | today's standard pipeline | generated per-shot first-frame image |
| `r2v` (reference to video) | this plan's pipeline | character/prop/background sheets, no first frame |
| `t2v` (text to video) | simplest: text prompt in, video out — no image stage, no sheets, no refs | none |

- **`video_generation_type` is a standalone project setting** (`"t2v" | "i2v" | "r2v"`,
  default `"i2v"`) on `meta.json` — chosen in the creation form's "Video Generation"
  selector or via `--video-generation-type`. The existing `ProjectType` members
  (documentary, movie, then-vs-now, ASMR) are **unchanged** — any project type can run
  any video generation type. (An earlier draft added enum members 5/6/7; rejected in
  favor of the standalone setting during review.)
- **All backend logic branches on `meta.video_generation_type`, never on the ProjectType
  enum** — one field drives the image-stage skip, the gate bypass, the ref sync, and
  workflow defaults: r2v → `video_minimax_h3_r2v`, t2v → the r2v workflow with zero
  refs attached (Q6; H3, native audio) or any no-reference workflow the user picks
  (e.g. Wan t2v); the t2v prompt strategy follows the workflow family (D6). i2v →
  today's default. Editable later in project settings (only while the affected stages
  haven't run).
- CLI: `--video-generation-type t2v|i2v|r2v` (implies the matching workflow unless
  overridden).
- The web queue still honors per-request workflow overrides (`GenerationDialog`), but the
  stage structure (image stage, sheets, sync) follows the project's type.
- *Alternative considered*: infer the type from the selected video workflow name. Rejected
  as the only signal (too implicit); kept as validation (an r2v project requires an r2v
  workflow — warn otherwise).

### D2 — Which references attach to a shot, and in what order (slot budget)

Per shot: **the sheets of characters appearing in that shot, the scene's background sheet,
and the sheets of props used in that shot** — bounded by the workflow's wired slots.

- Shot schema gains `characters: ["Name A", "Name B"]` (ordered: primary/speaking character
  first) and `props: ["Car", "Revolver"]` (ordered by visual prominence in the shot). Today
  shots only have `character_name` (singular) — the new R2V shots director emits the lists;
  `character_name` stays for back-compat (= first entry of `characters`).
- **Slot budget & priority** — reference demand now exceeds slots, so attachment is a
  priority fill. Default order (config `REF2VIDEO_REF_PRIORITY`, default
  `"characters,background,props"`; also accepts `"background,characters,props"` etc.):
  1. characters (speaking first, then present),
  2. scene background,
  3. props in the shot's `props` order.
  Stop when slots are full; the label renumbering post-processor (D3) keeps the prompt
  consistent with what was attached. **Unattached subjects are never dropped from the
  prompt** — they stay in `subject_definitions` as text-only descriptions (appearance prose
  from story.json), just without a `<Picture N>` citation; the director instructions must
  define subjects independently of whether a picture citation survives.
- The R2V shots director may override the default fill per shot with an optional explicit
  `reference_subjects: ["background", "Car", "Name A"]` field for shots where the default
  order is wrong (e.g. a car chase where the car outranks the background). Everything still
  passes through renumbering + slot cap.
- The official image budget is **9** (§5): extend the template to wire 9 `LoadImage` slots
  so character + background + prop sheets fit for virtually every shot. `compile_workflow`
  injects only into wired slots; the effective image budget is `min(9, 12 − non-image refs)`
  since images, audio, and video refs share the **12-file mixed cap** (D8/D12).
- The one priority knob is `REF2VIDEO_REF_PRIORITY` (ordered list, default
  `"characters,background,props"`). `continuity` is a valid list token for where the
  previous-clip tail sits when D12 is enabled (default then:
  `"characters,continuity,background,props"`). Audio refs don't take part in the list —
  they fill the 3-clip audio budget independently, **voices before BGM** (D8).

### D3 — `<Picture N>` label alignment

The director writes the prompt with a **documented label convention** (characters in listed
order, then background); a small post-processor renumbers labels when refs were dropped or
reordered so the prompt always matches what is actually wired. Labels are per-prompt local,
so renumbering is safe. This runs in the same place prompts are finalized (core, before
`compile_workflow`) so CLI and Web UI share it.

### D4 — Background sheets: single establishing frame first, environment sheet later

- Start: reuse the existing scene-background pipeline with an r2v-specific prompt template —
  wide establishing shot of the environment, **no characters**, matching the story's
  style descriptor. No resizing/AR constraints on our side — the workflow auto-handles
  reference-image sizing (Q2 resolved), though generating at the project's video aspect
  ratio (`VIDEO_ASPECT_RATIO`) remains the sensible default so sheets preview well in the
  UI. Multi-angle "environment sheet" (4-view, like character sheets) is a later
  enhancement.
- Prerequisite: fix the `_generate_single_image` signature bug (§2).
- Prompt template lives in `directors/story/_base/` or a new `directors/contexts` include so story
  directors can compose it (`{{include:...}}`).

### D5 — Workflow authoring & compiler/loader integration

- **We own and modify the H3 workflow JSONs to our requirements** — they are part of this
  feature's deliverable, not frozen upstream templates. The r2v JSONs are edited in place:
  - wire 9 `LoadImage` slots with `[ref_0]`…`[ref_8]` title tags and their
    `ref_images.ref_image_0..8` links on the R2V node (§5 limits);
  - `[prompt]` on the `PrimitiveStringMultiline` node, `[video_out]` on `SaveVideo`, keep
    the lone `PrimitiveFloat` duration node (`[duration]` detection already works);
    the frame-count math (`max(5, round(a*24))` …) floors at 5 **frames** (~0.2 s), not
    5 seconds — verified correct during implementation and left untouched;
  - in lockstep with the node update (Q1), add `[ref_video_0..2]` / `[ref_audio_0..2]`
    inputs;
  - optionally rename to `minimax_h3_r2v.json` for family consistency with the
    `minimax_h3_i2v*` files (the marker/dimension detection keys off the filename).
  Edits stay in ComfyUI **API format** with string node IDs (repo requirement) and land in
  git together with the node change.
- **t2v needs no dedicated workflow** (Q6): the r2v workflow with zero refs attached is
  the H3 t2v path (native audio retained). Optionally ship a thin
  `minimax_h3_t2v.json` (same graph, no ref `LoadImage` wiring) purely so the workflow
  selector shows an explicit t2v entry.
- **Naming convention (documented to prevent confusion)**: an `Ns` suffix in H3 workflow
  filenames = **N sampling steps** — a speed/quality preset (full model 20 steps vs
  Lightning 4/8 steps), never seconds. Keep step presets as separate workflow files
  (rename only the base file for family consistency, if at all); clip duration always
  comes from the `[duration]` node. Includes fixing `video_minimax_h3_r2v_8s.json`
  (Lightning enabled but 4 steps wired — Q5).
- `workflow_loader`/`config.py` discovery:
  - new `reference_image_node_ids` (ordered list from `[ref_N]` tags, falling back to
    counted `LoadImage`s when the workflow is r2v). Keep `load_image_first/last` mapping
    for FLFI2V untouched.
  - new **`is_ref2video: true`** flag, set when a `MiniMaxH3ReferenceToVideo` node class is
    present in the workflow (class detection, not name sniffing). This flag drives the
    image-gate bypass (D6) and r2v capability checks at submit time.
  - prompt-node discovery must accept a `[prompt]`-tagged **`PrimitiveStringMultiline`** —
    today's fallback only scans `CLIPTextEncode`, which is why the current r2v
    registration has no `motion_prompt_node_id` at all.
- `compile_workflow(...)` prompt injection: the input-name resolution (`text` vs `prompt`,
  `prompt_compiler.py:302-306`) needs a third case — `PrimitiveStringMultiline` prompt
  nodes take **`value`**. Without it the prompt is written to a nonexistent `text` input
  and silently ignored by ComfyUI.
- Ref injection: copy each image to the ComfyUI input dir
  (`prepare_comfyui_input_image`) and write `node.inputs.image` on each `[ref_N]`
  `LoadImage` node; the `ref_images.ref_image_{i}` links on the r2v node are already baked
  in the template, so only the `LoadImage` filename fields need setting. Audio/video refs
  resolve from the shot's `video_ref_asset_ids` (D6) into the `[ref_audio_N]` /
  `[ref_video_N]` node inputs once the updated node lands (Q1).
- Fewer refs than slots: **leave unfilled slots unattached — ComfyUI/the workflow
  auto-handles omitted reference inputs** (confirmed, Q1). The template wires all 9 image
  slots once; each shot's submission attaches only the refs it has, and unfilled inputs
  are simply omitted — no neutral/placeholder fill (identity-bleed risk), no per-shot
  slot removal, no template variants with fewer wired slots.

### D6 — Pipeline flow changes (`core/main.py` + services)

**Prerequisite — move sheet generation into `core/`.** Character-sheet and
background-sheet generation currently live only in the backend
(`generation_service.py:476-619`, `:2714-2823`), including the 8-view prompt template, so
the CLI cannot run ref2video end-to-end (and the repo workflow is CLI-first). Extract both
into a core module (e.g. `core/sheet_generator.py`); the web processors become thin
wrappers. This also fixes the `_generate_single_image` arg bug in the one shared place
(§4, gap 1).

Generation order for r2v projects:

1. story → scene graph → shots plan (R2V shots director)
2. character sheets for all characters (skip if present — idempotent)
3. background sheet per scene + prop sheets for story `props` (skip if present)
4. **new**: `sync_shot_video_refs(project_id)` in `project_manager.py`:
   - attaches, per shot, in the D2 priority fill: character-sheet refs of
     `shot.characters` (expression-sheet swap on close-ups, D11), the scene's background
     ref, and prop-sheet refs of `shot.props` — into `reference_asset_ids` (image refs
     only), tracked via `synced_video_ref_asset_refs` so regeneration swaps instead of
     accumulates; manual refs untouched; idempotent.
   - **scoped to r2v projects** (`video_generation_type == "r2v"`), and supersedes
     `sync_character_asset_refs` there — otherwise the character ref is attached twice
     under two different tracking keys and the bookkeeping desyncs. i2v projects keep the
     old character sync unchanged; t2v projects run no sync at all.
   - non-image refs (voice clips D13, continuity tails D12) go into a separate shot field
     **`video_ref_asset_ids`** (typed entries, e.g. `{"kind": "audio", "ref":
     "a/9f3ab21c"}`), never into `reference_asset_ids` — that field feeds image generation
     (`collect_shot_image_refs`) and would be polluted. The inverse-ref helper
     `_project_media_asset_ref` (`project_manager.py:179-191`) must be extended to map the
     `audio/` and `videos/` media dirs so project-local samples/tails can be referenced.
5. video generation per shot — **image gate bypassed**.

**t2v projects** are the simplest case — a text prompt in, a video out. Steps 2–4 (sheets
+ sync) are skipped entirely and the image gate bypass applies identically. The prompt
depends on the video workflow:

- **MiniMax H3** (native audio): shots use the T2VA-format `video_prompt` from the t2v
  director (D7 — no image instruction line, base guide §2.1); composer voice-text injection
  (D13) still applies.
- **Any other t2v workflow** (e.g. Wan t2v — no native audio): no special director; the
  standard shot planner output is used and the effective prompt **defaults to
  image_prompt + motion_prompt combined** — with no generated image, the image
  description has to travel in the text (same semantics as `APPEND_IMAGE_TO_MOTION_PROMPT`).
  The user can change the prompt (per-shot editing / prompt selection) as with any shot.

Both paths work everywhere (Q6): H3 t2v = the r2v workflow with zero refs (native audio
kept); non-H3 t2v workflows trade the native audio for combined image+motion prompts.

Image-stage skip points and gates to touch:

- CLI batch flow in `main.py` (skip `generate_images_for_shots`).
- CLI regeneration: `regenerate.py` → `core/video_regenerator.py` has its own image
  precondition (the CLI mirror of the web guard) — relax it for r2v/t2v shots.
- Web queue: `run_batch_generation` builds no IMAGE items; `_queue_processor_loop`
  dependency gate (`generation_service.py:330-352`) skips the `image_generated` wait when
  the project's `video_generation_type` is `r2v` or `t2v` **or the item's workflow has
  `is_ref2video`** (D5); `regenerate_shot_video` (`:1930-1931`) drops the "no image" hard
  error for the same cases.

### D7 — The R2V shots director

New `directors/shots/videoprompt/videoprompt_minimax_h3_r2v.md` (composable via
`{{include:...}}` with existing style/context packs):

- Six-section full-reference output (guide §1): `subject_definitions` (one `<Subject N>` per
  character + one per environment, citing `<Picture N>`; dialogue voices described with
  stable attributes), `summary` (`[reference generation]` prefix), `retention_analysis`,
  `detailed_description` (style sentence(s) **before** `[Shot 1]`; no first-frame anchor
  line; sub-shot/cut/camera rules inherited from the I2VA director; dialogue `<d>` rules
  unchanged), `overall_soundscape`, `non_diegetic_music`.
- Emits per shot: `video_prompt` (the six sections), `characters` (ordered), `props`
  (ordered, exact names from story.json `props`), optional `reference_subjects` override
  (D2), optional `continues_from_previous` (bool, D12 — true only when the shot directly
  continues the previous shot's action within a scene), `duration`, `camera` (kept for
  close-up expression heuristic + future use; H3 workflows don't use camera LoRAs),
  optional `soundfx_prompt` (used only when post-SFX layer is enabled).
- Speaker voice prose: the director writes voice descriptions for **unbound** characters only;
  the composer overwrites/injects the character's voice text verbatim (D13), so the
  director instructions note that its voice wording may be replaced — no need for the LLM to
  repeat it perfectly.
- **The composer is a named core module** (`core/r2v_composer.py`): everything applied to
  the director's raw output — voice-text injection (D13), `<Picture N>`/`<Audio N>` label
  renumbering against the actually-attached refs (D3), text-only subject fallbacks, and
  `<Audio N>` definition insertion — lives there exactly once, called by both the CLI flow
  and the backend video path, so the logic never forks between them.
- **T2V sibling director** (`videoprompt_minimax_h3_t2v`) for t2v projects **on MiniMax H3**
  (non-H3 t2v needs no special director — the combined-prompt default covers it, D6): the
  same rules minus everything reference-related — T2VA has no image instruction line, no
  `subject_definitions`, and no labels; it begins directly with the three core fields
  (base guide §2.1), and subjects get full prose descriptions in every shot since nothing
  is referenced. It reuses the composer for voice-text injection (D13 still applies);
  label renumbering is a no-op with zero refs.
- Still emits `image_prompt` (per-character/environment prose) — not rendered, but reused as
  the description source for background-sheet prompts and the editor UI.
- `validate_video_prompt` in `shot_planner.py` gains an r2v variant (six-section checks,
  label convention, cut-time rules unchanged, and the 7000-character R2V prompt cap —
  Q4 — repaired via the existing LLM repair loop).

### D8 — Audio strategy

- **Primary (in-prompt)**: dialogue `<d>`, ambience, music — native H3 audio. Narration /
  voiceover is authored as off-screen voiceover `<d>` in the prompt (recommended default:
  keeps one consistent voice per character and avoids a separate TTS mix).
- **Audio reference clips (v2, per §5 limits: 3 clips, 2–15 s each)** — attaches real audio
  files as `<Audio N>` labels per the full-reference guide:
  - **Voice timbre per character** (the big win for cross-shot voice consistency, D9):
    a 5–10 s sample synthesized once from the character's **text voice** via any configured
    TTS backend (D13), stored as a **project audio asset** (or library asset) and bound as
    the character's audio voice (`voice.ref`); shots where that character speaks attach it,
    and the composer writes `<Audio 1> is the voice-timbre reference for <Subject 1> (S1)`
    and cites it at the character's spoken lines ("in the voice timbre referenced from
    `<Audio 1>`"). Text-only characters gracefully degrade to prompt-text-only voicing. The
    voice-description prose stays in the prompt either way (the guides require it) — the
    clip biases H3's native TTS toward the same voice across separately generated clips,
    and the description text is injected deterministically by the composer (D13) so wording
    is byte-identical across shots.
  - **Scene BGM anchor** (optional): one music clip per scene attached to each of its shots
    so score transitions survive cuts. Audio slots fill **voices before BGM**: the 3-clip
    cap fits 2 speaking voices + BGM exactly; with 3 speakers the BGM anchor drops first
    and stays prompt-only in `non_diegetic_music`.
  - `<Audio N>` numbering follows attachment order with the same renumbering machinery as
    `<Picture N>` (D3); audio refs count against the 12-file mixed cap (D2).
  - Config: `REF2VIDEO_VOICE_REFS` (default off in v1; enabled only when the active
    workflow carries wired `[ref_audio_N]` inputs — names per the Q1 contract), with
    per-character opt-out (some users prefer pure text-described voices).
  - Voice samples are synthesized from the character's **text voice** with any configured
    TTS backend (D13) — a `VOICE_SAMPLE` queue item mirroring `CHARACTER_IMAGE`, reusing
    `narration_generator`; characters without a text voice get no clip and no voice prose.
- **Optional post layers** (phase 5): per-project `audio_strategy`:
  - `native` (default) — H3 audio as-is;
  - `native+sfx` — run existing MMAudio soundfx pass and mix under the native track;
  - `replace_music` — keep dialogue/SFX, swap BGM via export audio mixing.
- Because shot MP4s already contain audio, the export mixer needs no change for `native`;
  the other two reuse existing soundfx/export paths.

### D12 — Reference-video continuity (opt-in, v2)

The official mode allows up to 3 reference videos (2–15 s) — the plan's D9 continuity
weakness ("no shared first frame") can be attacked directly: attach the **tail of the
previous generated clip** (last 2–5 s) of the same scene as `<Video N>` and upgrade the
prompt's task prefix to `[reference generation + video continuation]` with
`retention_analysis` noting the continuation relationship (guide §2.3/§3).

- Scope: within a scene only (cross-scene continuations would smear location changes);
  **off by default — used only where required**. Config
  `REF2VIDEO_CONTINUITY_MODE = "off" | "auto"`; in `auto` mode a tail ref is attached
  **only to shots that directly continue their predecessor** — the R2V director marks them
  `continues_from_previous: true` (D7), users can toggle per shot in the UI, and
  scene-opening/standalone beats never get one.
- Cost: serialization is bounded by the mechanism itself — only chains of consecutive
  `continues_from_previous` shots run in order (shot N+1 waits for shot N); everything
  else stays fully parallel.
- Priority in the 12-file budget: a continuity video occupies one file slot and joins the
  D2 fill as the `continuity` token (default when enabled:
  `"characters,continuity,background,props"`).
- Implementation note: the tail clip needs an ffmpeg trim helper (last 2–5 s of the
  previous shot's mp4 — none exists in core today); the trimmed file is stored as project
  media in the `videos/` dir and referenced via `video_ref_asset_ids` (D6).
- Wiring: `ref_videos.ref_video_0..2` per the Q1 contract (node, workflow, and compile
  step land together in Phase 0).

### D13 — Character voices: text-based and audio-based voice IDs (v2)

Per the H3 guides, a character's voice in a prompt is **a descriptive phrase plus a stable
speaker ID**, placed outside `<d>` at every dialogue line (base guide §4.4: character type,
age, gender, pitch, timbre, speaking rate, accent — e.g. `The young woman with a quiet,
breathy voice (S1) says: <d>[English] …</d>`), optionally *anchored* by an attached audio
clip cited as `<Audio N>` ("the voice-timbre reference for `<Subject N>` (Sx)", ref guide
§2.4). A voice ID in our system is therefore one of two kinds:

1. **Text voice** — the voice ID *is* a description string, e.g.
   `"An old female lady with a husky voice in her 80s"`. It is embedded verbatim into every
   shot prompt in which that character appears/speaks. This is the primary, always-present
   form — the guides require the prose regardless of anything else.
2. **Audio voice** — a real voice sample file, cited as `<Audio N>` on top of the text
   (never instead of it). Stored either **globally in the asset library** (Audio category,
   `a/{id}`) or **project-local** (`p/{pid}/audio/{file}`) — regular asset refs, no new
   storage system.

**Character schema** (story.json):

```json
{
  "name": "Elder Mama",
  "voice": {
    "type": "text",
    "text": "An old female lady with a husky voice in her 80s",
    "ref": null
  }
}
```

- `type: "audio"` additionally sets `ref` to an asset ref (`a/9f3ab21c` or
  `p/{pid}/audio/mama_voice.wav`); `text` stays mandatory in both types (prose is embedded
  either way; the clip anchors timbre).
- Shots never carry voice data themselves — the shot lists `characters`, and the composer
  resolves each character's voice at prompt-build time (per-shot embedding, as the user
  flow requires).

**Generators are not voices.** ElevenLabs / Edge-TTS / ComfyUI voice workflows are
interchangeable **synthesis backends** used to *produce* an audio voice from a text voice —
the voice itself is the text or the audio asset, never "the ElevenLabs voice". Any backend
supported by `narration_generator` can be used; backend + provider-voice choice is a
per-generation setting (UI dropdown on the generate action, config default otherwise).

**Voice lifecycle (UI + CLI)**:

- Write/bind a text voice on the character (free text, or pick from previously used text
  voices — a lightweight suggestions list sourced from other characters/projects).
- Optional **"Generate voice sample"** action: synthesizes a 5–10 s clip from the text
  voice using the chosen backend, saves it as an asset (project `audio/` dir by default,
  "save to library" checkbox) and sets `voice.ref` — promoting the text voice to an audio
  voice. Preview playback before/after.
- Re-generating replaces the sample (same promotion path); clearing `ref` demotes back to
  text-only.

**Prompt embedding (composer rules, guide-exact)**:

- Text voice → injected verbatim as the speaker's identifying phrase in
  `subject_definitions` and at each dialogue line: `An old lady with a husky voice in her
  80s (S1) says: <d>[English] …</d>`; voiceover uses the exact §4.4 phrase `says in an
  off-screen voiceover` + "lips remain completely closed".
- Audio voice → additionally attach the sample as `ref_audio_N` and write
  `<Audio 1> is the voice-timbre reference for <Subject 1> (S1)` in `subject_definitions`,
  citing "the voice timbre referenced from `<Audio 1>`" at the character's spoken lines
  (ref guide §2.4/§5.4). `(Sx)` numbering is unchanged by the clip; audio refs count
  against the 3-clip / 12-file budgets (§5).
- Deterministic injection (not LLM re-wording) is what makes the voice byte-identical
  across shots — the D9 mitigation.

Standard (i2v) projects can reuse the same character voice fields for narration
TTS selection later — out of scope for v1 (§8).

### D9 — Known limitations & mitigations (to document in the guide)

| Risk | Mitigation |
| --- | --- |
| Character identity drift across shots (no shared first frame) | 8-view sheets + mandatory `<Subject N>` re-description every shot + `retention_analysis` |
| Voice consistency across separately-generated clips | Identical voice-description prose per shot **plus optional per-character voice-timbre reference clips** (D8, `<Audio N>`); the 3-clip budget fills voices first, the BGM anchor drops when 3 speakers fill it |
| Cut-to-cut continuity softer than I2VA | Same background sheet per scene; explicit opening-state sentences; opt-in reference-video continuation within a scene (D12); multi-shot 15 s clips to keep continuity inside a scene |
| Ref limits on ensemble shots | 9 image slots cover typical casts; the real cap is **12 mixed files** — the D2 priority fill applies across images+videos+audio; extra characters fold into prompt text only |
| ~~Background crop by `ref_image_size: "match"`~~ | **Resolved (Q2)**: no resize needed — the workflow/node auto-handles reference sizing for any source AR (square character sheets included) |

### D10 — Props (v2)

Recurring objects that must look identical across shots: vehicles (car, bike), weapons
(gun, knife), electronics (computer, phone), home/locations-as-objects, wearables (watch,
jewelry), standalone outfits/armor. Today **nothing in the schema tracks props** — story
directors emit only `characters` (with `attire` folded into the character) and scenes/shots
carry free-text descriptions.

**Story schema** — extend `base_story_format.md` (and the R2V story-director guidance) with an
optional story-level array mirroring `characters`:

```json
"props": [
  {
    "name": "John's Mustang",
    "category": "vehicle",
    "image_prompt": "1968 dark-green Ford Mustang fastback, chrome bumpers, dirty windshield, on white background, three-quarter front view, cinematic product shot",
    "owner": "John"
  }
]
```

- `owner` (optional) links a prop to a character ("John's car"); the R2V prompt composer uses
  it to phrase `subject_definitions` ("<Subject 4> is John's car from <Picture 3>…").
- Directors that don't emit `props` simply produce none — everything downstream is a no-op
  (same backward-compatibility rule as `characters`).
- **Wearables rule for directors**: a character's *default* clothing stays inside the character
  `image_prompt`/`attire` (it's part of identity); only standalone/outfit-changing items
  (armor, uniforms worn by many, transformation suits) become props.

**Prop reference sheets** — one reference image per prop, generated once per project:

- Stored in the project `references/` dir (keeps `images/` for shot frames); path on
  `story.props[].reference_image_path`, analogous to `character_reference_image_path`.
- Prompt template: neutral-background cinematic product shot, consistent with the story's
  `style`; **single hero image in v1**; optional multi-view grid (front/side/detail) for
  complex categories (`vehicle`, `weapon`) via a `PROP_SHEET_VIEWS` config later.
- Queue: new `GenerationType.PROP_IMAGE` mirroring `CHARACTER_IMAGE`
  (`models/queue.py`, `_process_prop_generation` in `generation_service.py`), API
  `POST /stories/props/{idx}/generate-reference` next to the character endpoint
  (`api/stories.py:498`), upload variant included. Frontend: props manager component
  mirroring `CharacterReferenceUpload`.
- Manual upload path (like characters) writes `reference_image_path` directly.

**Shot wiring** — the R2V shots director lists prop names per shot (`props: [...]`, exact names
from story.json). `sync_shot_video_refs` (D6) attaches prop refs after characters/background
per the D2 priority fill, tracked in the same `synced_video_ref_asset_refs` set so
regenerating a prop sheet swaps refs instead of accumulating.

**Prompt presence** — an attached prop gets a `<Subject N>` + `<Picture N>` citation; a
dropped prop (slot budget) stays as a text-only `<Subject N>` built from its `image_prompt`.
Prop continuity across shots rides on the same sheet + identical wording in every
`subject_definitions`.

### D11 — Character expression sheets (optional, user-triggered)

**Yes, worth adding — but as an explicit opt-in, not part of the default flow.**

- Rationale: the existing 8-view sheet carries 4 neutral face close-ups. An expression grid
  (joy / anger / fear / sadness / surprise / determination) gives the model a facial-identity
  anchor at emotional extremes — useful in *both* modes, since close-ups are where identity
  drift is most visible. Prompt text still drives the emotion; the sheet anchors the face.
- **Generation**: per-character button next to the existing "Generate Reference" — queue item
  `CHARACTER_IMAGE` with `sheet_type: "expressions"` (or a distinct type; implementation
  detail), writing `characters[].expression_reference_image_path`; stored in the project
  `references/` dir (like prop sheets, keeping `images/` for shot frames). Never
  auto-generated.
- **Attachment heuristic** (default on, config `REF2VIDEO_EXPRESSION_ON_CLOSEUPS`): when a
  shot's `camera` is a close-up variant (`close-up`, `extreme close-up`, `macro`) **and** the
  expression sheet exists, the D2 priority fill includes it for that shot — v1 replaces the
  standard sheet in the character's slot (same slot count); later, if slots allow, both.
  Manual attachment via the shot's `reference_asset_ids` always wins.
- **Cost control**: +1 image generation per character, only when the user asks; the D2
  priority fill means it costs no extra slots vs the standard sheet (v1 replacement rule).
- The R2V director prompt format is unchanged — the composer just cites the expression sheet as
  the `<Picture N>` behind the character's `<Subject N>`; `subject_definitions` wording is
  identical either way ("the young woman in <Picture 1>"), so prompts stay stable whether
  the standard or expression sheet is attached.

---

## 4. Gaps in current code (must fix regardless)

1. **Background generation broken**: `generation_service.py:2762-2776` passes 11 positional
   args to `_generate_single_image` (10-param signature) — args shifted, would misbehave.
2. **r2v workflows not pipeline-usable**: no `[prompt]`/`[ref_N]` title tags → discovery
   produced `load_image_first/last_node_id` and no prompt node; and even once tagged, the
   prompt node is a `PrimitiveStringMultiline` (input `value`), which neither discovery's
   `CLIPTextEncode` scan nor `compile_workflow`'s `text`/`prompt` input-name cases handle
   (D5). All resolved by the D5 workflow edits (which we author) plus the discovery/compiler
   changes. (The duration math's `max(5, …)` is a 5-frame floor, not seconds — verified
   correct, untouched.)
3. `compile_workflow` has no multi-reference injection path for video workflows.

---

## 5. Official limits & remaining verification spikes (before Phase 1)

Official MiniMax H3 Ref2VA limits per generation:

- up to **9 reference images**,
- up to **3 reference videos**, each 2–15 s long,
- up to **3 reference audio clips**, each 2–15 s long,
- **≤ 12 mixed files** total across all three categories.

Implications: the 9-image budget covers character + background + prop sheets for virtually
every shot (D2 priority fill only binds on the 12-file mixed cap once audio/video refs are
attached); reference **audio clips** open a per-character voice-timbre mechanism (D8);
reference **videos** open an opt-in shot-to-shot continuity mechanism (D12).

Remaining spikes:

- **Q1** — **fully resolved**: unfilled reference inputs are simply **omitted from the
  submission — ComfyUI/the workflow auto-handles it** (no placeholder images, no slot
  surgery; wire all 9 image slots in the template, attach only what each shot has). And
  since we own the node, **the video/audio input names are ours to define**: the node will
  expose exactly this contract — `ref_videos.ref_video_0..2` and
  `ref_audios.ref_audio_0..2` (3 + 3, official limits) — with node, workflow wiring, and
  the compile step landing together in Phase 0. Any residual submit-time check is a cheap
  presence guard (does the active workflow config carry the `[ref_audio_N]`/`[ref_video_N]`
  node ids), not a compatibility fallback.
- **Q2** — resolved: **no resize needed — the workflow auto-handles reference-image
  sizing**, so sheets of any aspect ratio (square character sheets included) attach
  as-is; no AR constraints on sheet generation.
- **Q3** — resolved: `SaveVideo` with `format: "auto"` selects the container/codec itself
  (audio included), so the native H3 audio track survives the copy step
  (`get_output_file_path` → project videos dir) with no handling on our side.
- **Q4** — resolved: the R2V prompt limit is **7000 characters** — generous headroom for
  the six-section format (a 350–500-word `detailed_description` fits comfortably), so
  prompts stay as detailed as the guide asks. The r2v `validate_video_prompt` variant
  enforces the cap, repairing over-budget prompts through the existing LLM repair loop
  (D7).
- **Q5** — resolved, with a correction: the `Ns` suffix in H3 workflow filenames means
  **N sampling steps**, not seconds (`minimax_h3_i2v` = full model at 20 steps;
  `minimax_h3_i2v_4s` / `_8s` = Lightning LoRA at 4 / 8 steps; clip duration is a
  separate node — baked at 5 s and overridden per shot via `[duration]`). Step variants
  are **speed/quality presets to keep**, surfaced naturally by the existing workflow
  selector — no dedup. One real defect found while verifying: `video_minimax_h3_r2v_8s.json`
  enables the Lightning LoRA but leaves its steps int at **4** — set it to 8 (or rename)
  during the D5 workflow edits.
- **Q6** — resolved: **t2v runs on the MiniMax H3 R2V workflow with zero references
  attached** (no dedicated `MiniMaxH3TextToVideo` node or new workflow needed — H3 t2v
  keeps native audio), **or on any workflow that needs no references** (e.g. Wan t2v,
  combined image+motion prompts per D6). The default for t2v projects is the r2v
  workflow with zero refs; the prompt strategy follows the workflow family.

---

## 6. Implementation phases

**Phase 0 — spikes, bug fix & workflow authoring** (§5 Q1–Q6; background
`_generate_single_image` fix; **modify the H3 workflow JSONs per D5** — 9 `[ref_N]` slots,
`[prompt]` tag, video/audio inputs in lockstep with the node update,
fix the r2v_8s steps mismatch (Q5)).

**Phase 1 — workflow plumbing**: config/workflow discovery of `reference_image_node_ids`,
the `is_ref2video` flag, and `[prompt]`-tagged `PrimitiveStringMultiline` prompt nodes;
`compile_workflow` multi-ref injection **plus the `value` prompt-input case** (D5); unit
tests for injection (no live ComfyUI needed).

**Phase 2 — core pipeline**: extract sheet generation into `core/sheet_generator.py`
(character/background/prop sheets; fixes the `_generate_single_image` arg bug in the one
shared place, D6); shot `characters` **and `props`** fields (planner passthrough +
validator); story schema `props` array + `characters[].voice` (text/audio voice ID, D13)
(base_story_format + directors); `sync_shot_video_refs` in `project_manager` (D2 priority fill
incl. props, D11 close-up expression swap, the `video_ref_asset_ids` split, `audio`/`videos`
in `_project_media_asset_ref`); image-stage skip in the CLI flow incl. the
`video_regenerator.py` gates; new `ProjectType` members + `meta.video_generation_type`
(t2v/i2v/r2v, default `i2v` for existing types, D1); CLI flags
(`--video-generation-type`, `--character-voice`); queue gate bypass in backend
(`_queue_processor_loop`, `regenerate_shot_video`, `run_batch_generation` — keyed on
`is_ref2video`, D5); `GenerationType.PROP_IMAGE` processor (D10).

**Phase 3 — prompts & composer**: `videoprompt_minimax_h3_r2v` director + the
`videoprompt_minimax_h3_t2v` sibling (D7) + r2v background-sheet prompt include + prop
reference-sheet prompt template; the shared composer `core/r2v_composer.py` (D7 —
voice-text injection D13, `<Picture N>`/`<Audio N>` renumbering D3, text-only subject
fallbacks); `validate_video_prompt` r2v/t2v variants.

**Phase 4 — Web UI**: project-creation flow gains the new project type with its
video-generation-type selector (plus later editability in settings); batch builder skips
IMAGE items for r2v/t2v projects and queues CHARACTER_IMAGE / BACKGROUND / PROP_IMAGE
first (r2v only); shot card hides image generate in r2v/t2v projects; scenes background manager (existing) becomes part of the main flow; props
manager component (generate/upload per prop); per-character "Generate Expressions" button;
**voice management** per D13 (text/audio voice editor on characters, "Generate voice
sample" action with backend picker — the `VOICE_SAMPLE` queue item ships here so samples
can be auditioned and bound — preview playback, library/project storage choice);
GenerationDialog r2v presets.

**Phase 5 — audio/video reference attachment, options, docs, tests**: `<Audio N>` /
`<Video N>` attachment to generations — D8 voice clips + BGM anchors behind
`REF2VIDEO_VOICE_REFS`, D12 continuation behind `REF2VIDEO_CONTINUITY_MODE` (inputs and
names are ours per the Q1 contract — the flags gate the feature, not node capability;
incl. the ffmpeg tail-trim helper); `audio_strategy`,
optional soundfx mixing; docs (`docs/features/REF2VIDEO.md`, guide cross-links,
DOCS_INDEX); manual live test against ComfyUI (`tests/` manual script per repo convention)
+ offline unit tests.

### Tests (offline, `tests/unit/`)

- regression test for the background `_generate_single_image` arg fix (phase 0),
- ref injection into `[ref_N]` nodes (count mismatch cases) and the `value` prompt-input
  case (D5),
- `is_ref2video` workflow discovery,
- label renumbering,
- D2 priority fill (characters/background/props ordering incl. the `continuity` token,
  slot cap, `reference_subjects` override, close-up expression swap),
- `sync_shot_video_refs` idempotency/manual-ref preservation + scoping (ref2video projects
  only, supersedes the character sync there),
- `video_ref_asset_ids` resolution and the audio-slot fill order (voices before BGM),
- queue gate bypass for r2v/t2v projects (`video_generation_type` branching),
- voice embedding tests: text voice injection verbatim per shot, audio-voice `<Audio N>`
  citation + attachment, type precedence/edge cases (D13),
- r2v prompt validator (six sections, label convention, cut times, 7000-char cap).

---

## 7. Example of an r2v shot prompt (target shape)

```text
subject_definitions:
<Subject 1> is the middle-aged baker in <Picture 1>, with salt-and-pepper beard, flour-dusted
apron and rolled sleeves.
<Subject 2> is his teenage daughter in <Picture 2>, dark braided hair, green scarf.
<Subject 3> is the small street bakery environment in <Picture 3>: wooden counter, brass
scale, fogged front windows before sunrise.
<Subject 4> is the baker's vintage delivery bicycle in <Picture 4>, dark-green frame, wicker
front basket.

summary:
[reference generation] <Subject 1> opens the bakery shutters while <Subject 2> loads loaves
onto <Subject 4>; three timestamped sub-shots, ending on the two wheeling the bicycle out.

retention_analysis:
<Subject 1> (appears in [Shot 1], [Shot 3]): fully_preserved - beard, apron, sleeves retained.
<Subject 2> (appears in [Shot 2], [Shot 3]): fully_preserved - braids and green scarf retained.
<Subject 3> (appears in all shots): fully_preserved - counter, scale, fogged windows retained.
<Subject 4> (appears in [Shot 2], [Shot 3]): fully_preserved - dark-green frame and wicker basket retained.

detailed_description:
The target video is live-action, cinematic, warm practical lighting before dawn.
[Shot 1] Inside <Subject 3>, a medium shot frames <Subject 1> ... he says in a calm, slightly
raspy voice: <d>[English] First batch of the morning.</d> ...
[Shot 2] At 00:05.000, the camera cuts to ...

overall_soundscape:
Cold morning street tone through the glass, oven door creak, tray clatter.

non_diegetic_music:
A sparse solo piano motif enters after the first line, slow tempo, no swell.
```

(Attached refs in wired-slot order: `ref_image_0` = baker's character sheet → `<Picture 1>`,
`ref_image_1` = daughter's character sheet → `<Picture 2>`, `ref_image_2` = scene background
→ `<Picture 3>`, `ref_image_3` = bicycle prop sheet → `<Picture 4>`. With 9 image slots all
four always fit; the D2 fill only drops refs when the 12-file mixed cap binds (e.g. after
voice/BGM audio refs are attached). If a ref is dropped, the renumbering post-processor
strips its `<Picture N>` citation but keeps the `<Subject N>` as a text-only definition
built from its `image_prompt`.)

Character voices (D13) embed per §4.4: the baker's text voice
(`"A calm, slightly raspy middle-aged male voice"`) is injected as the speaker's
identifying phrase with his stable ID — `The middle-aged baker with a calm, slightly raspy
voice (S1) says: <d>[English] First batch of the morning.</d>` — in every shot where he
speaks, word-for-word identical. With an audio voice bound (D8), the same prompt additionally
gains in `subject_definitions`: `<Audio 1> is the voice-timbre reference for <Subject 1>
(S1)` — attached as `ref_audio_0` = his synthesized sample — and the dialogue line cites
"...says in the voice timbre referenced from `<Audio 1>`: <d>…</d>".

---

## 8. Non-goals (for v1)

- No GeminiWeb/FlowWeb r2v equivalent (ComfyUI only).
- No per-shot image fallback UI (an `i2v` project of the new type — or any legacy project
  type — remains the fallback).
- No automatic voice cloning in v1 — audio voices (D13) are synthesized from the character's
  text voice via a TTS backend, not cloned from real recordings; and `<Audio N>` attachment
  ships in phase 5 behind its feature flag (node/workflow inputs are ours per the Q1
  contract). Reference-video continuation (D12) is likewise opt-in/phase 5.
- No `<Audio N>` file attachments before phase 5; until then audio is prompt-authored only.
  Post-audio layering reuses existing export mixing.
- No multi-view environment sheets (later enhancement, D4) and no multi-view prop sheets in
  v1 (single hero image per prop; grid variant deferred via `PROP_SHEET_VIEWS`, D10).
- No automatic prop *discovery* in v1 — props exist only where a story director (or the user,
  via the props manager) defines them; an LLM prop-extraction pass over existing projects is
  a possible follow-up.
- Character voices (D13) serve ref2video prompt/clip needs in v1; wiring them into standard
  (I2VA) mode's narration voice selection is future work.
