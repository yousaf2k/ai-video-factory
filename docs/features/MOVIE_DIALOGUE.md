# Movie Dialogue Layer

> 📚 [Docs Index](../DOCS_INDEX.md) › Features › Movie Dialogue
>
> Related: [Ref2Video](REF2VIDEO.md) · [H3 base prompt guide](../guides/Minimax_H3_VIDEO_PROMPT_WRITING_GUIDE_base_en.md) · [Configuration](../getting-started/CONFIGURATION.md)

## Overview

Movie projects (`directors/story/movie/*`) are written as **screenplays with a dialogue layer**: the
characters' spoken lines are first-class story data, and the pipeline checks — deterministically —
that they are in the right language, fit the film, and reach the shot prompts, where MiniMax H3
renders them as lip-synced speech.

Before this layer, movie stories were voice-over narration with "dialogue allowed sparingly", the
scene schema had no place for dialogue, and the shot planner received none. Measured on the
existing movie projects: only **20% of shots contained dialogue**, about **23 dialogue words per
minute of screen time**, and several films (one of them 300s / 64 shots) had **no lines at all**.
Dialogue written in the master script was dropped by the scene pass (13 lines → 0, 33 → 0).

Documentaries and the other narrated families are unchanged: their scenes keep the narration-only
shape and plan exactly as before.

## Measured effect

Same method both times: dialogue words inside the shots' `<d>` blocks, divided by the planned
screen time. "Existing projects" is the 14 movie projects on disk before this layer; "verification"
is a fresh 120-second Urdu horror short generated afterwards through the web UI's own code path
(`movie/horror` + `studio_ghibli` on the r2v Singularity base, DeepSeek).

| | Existing projects | Verification |
| --- | --- | --- |
| Shots containing dialogue | 20% | **94%** (15 of 16) |
| Dialogue words per screen minute | 22.9 — the most recent films: 3–7 | **62** |
| Scripted lines actually spoken in a shot | not tracked | **16 of 16** |
| Dialogue script | Latin and Urdu script mixed inside one film | **16 of 16** in Urdu script |
| Scene speech density | — | 34–70% (limit 75%) |
| Clips over 75% speaking time | — | **1 of 16** (79%, pinned at the 15s clip cap) |

The checks are not decoration: every one of them earned its place during the four verification
rounds. The first screenplay came back with 152 seconds of speech for a 120-second film (clips at
150–400% speaking time); a planner response with one broken JSON string cost a whole scene its
shots; and the model answered *"Dialogs in Urdu. Do not use English"* in English even when the
prompt stated the language explicitly — the translation pass is what put all 16 lines in Urdu
script.

## How it works

```
Idea ─► dialogue language detected from the idea ("Dialogs in Urdu")
  │
  ├─► Pass 1: screenplay (master script)       dialogue-first; word + line budgets; language stated
  ├─► Pass 2: scenes                           every scene carries dialogue: [{speaker, line, delivery}]
  │
  ├─ ✗ language check      (story_engine)      not a line in the requested script → one translation pass
  ├─ ✗ fit check           (story_engine)      lines lost / too few words, or a scene that cannot play its
  │                                             speech → one repair pass, merged scene by scene
  ▼
Shot planner                                  gets the lines + each character's voice
  │  DIALOGUE rules: place EVERY line verbatim, fit the clip, stage the speakers
  ├─ ✗ coverage check      (shot_planner)      a scene with unplaced lines → one rewrite, kept only if better
  ├─ ⚖ clip pacing         (shot_planner)      time moves to the clips whose lines need it
  ▼
video_prompt  … (S1) says: <d>[Urdu] …</d>  ─►  MiniMax H3 speaks it with lip-sync
```

### Speaking-time model

One estimate is shared by every budget and check: a line takes **its words ÷ 2.5 seconds plus a
0.6s breath**. A scene or a clip may fill at most **75%** of its time with speech; the screenplay
prompts plan for less (40% dialogue + 15% narration) so scenes keep room to act.

### 1. Dialogue language

Models drift out of a requested dialogue language when it is only implied in the idea: the first
live test of the new screenplay answered *"Dialogs in Urdu. Do not use English"* entirely in
English. So the language is handled in code:

- `detect_dialogue_language(idea)` reads the language the idea names for its dialogue
  ("Dialogs in Urdu Lanaguge", "dialogue should be in Spanish", "Urdu-language dialogue",
  "Dialogs in Roman Urdu"). Only listed language names count, so surrounding prose — including
  "do not use English in dialogue" — cannot produce a wrong language.
- It is injected into both screenplay prompts as `{DIALOGUE_LANGUAGE}`:
  *"This film's dialogue language is Urdu."*
- After Pass 2, `ensure_dialogue_language()` verifies the **script** for languages written in a
  non-Latin script: if not a single dialogue line is in that script, one pass translates every
  line. A scene keeps the translation only if its lines still map one to one onto the same
  speakers; only the words are replaced. ("Roman Urdu" asks for transliteration and skips this.)

One script is used for the whole film — a language's own script unless the idea itself writes that
language in transliteration. Mixing scripts was a source of inconsistency in older projects.

### 2. Screenplay (`movie/_base/master_script.md`)

Pass 1 writes a dialogue-first screenplay: action lines, every spoken line as
`CHARACTER NAME (delivery): "…"`, and sparse narrator lines as `NARRATOR (voice-over): "…"`. It gets
explicit budgets through placeholders:

| Placeholder | Value for a film of `L` seconds |
| --- | --- |
| `{MASTER_WORD_COUNT}` | `L × 2.5` — all spoken words |
| `{DIALOGUE_WORD_COUNT}` | `L × 2.5 × MOVIE_DIALOGUE_SHARE` (default 0.40) |
| `{NARRATION_WORD_COUNT}` | `L × 2.5 × MOVIE_NARRATION_SHARE` (default 0.15) |
| `{DIALOGUE_LANGUAGE}` | the idea's dialogue language |

Models cannot count words reliably, so the budget is also given in lines, which they can count:
**about one short line (≤ 12 words) per 8 seconds of film** — a 120-second film asks for about 15
lines / 120 dialogue words. That is dialogue for roughly 40% of the running time, close to a real
feature (60–80 spoken dialogue words per screen minute), and it leaves each clip room to act.

### 3. Scenes with dialogue (`movie/_base/_output_format.md`)

The movie family has its own scene schema. It sits in `movie/_base/`, so the movie base layers'
include of `_output_format` resolves to it first, while documentaries keep the shared
`story/_output_format.md`.

```json
"dialogue": [
  {"speaker": "Dawa Farosh", "line": "Bhai sahib, Faisalabad ja rahe hain?", "delivery": "hopeful, half-whispered"},
  {"speaker": "Tonga Driver", "line": "Chal. Baith ja.", "delivery": "flat, not turning"}
],
"narration": "Voice-over only — \"\" when the narrator is silent"
```

Rules given to the model: carry every screenplay line over **verbatim** (add within the line
budget, never remove), list lines in playing order with the exact character `name` as `speaker`,
and **a scene holds at most `scene_duration ÷ 7` lines** (a 15s scene: 2, a 24s scene: 3). When the
screenplay has more lines than the film has time for, the scene pass may trim to the strongest.

Each character's `voice_type` is a concrete speaking voice (age, gender, pitch, timbre, pace,
accent). It is copied word for word into every shot the character speaks in, which is what keeps a
voice consistent across separately generated clips.

### 4. Fit check (`core/story_engine.py`)

`fit_story_dialogue()` runs on the final scene durations and checks two directions, because models
overshoot as easily as undershoot (an early test wrote 152 seconds of speech for a 120-second film):

- **too little** — far fewer dialogue lines than the screenplay (judged by *count*: a translated or
  reworded line is not a lost line), or less than half the dialogue word budget;
- **too much** — a scene whose speech cannot play in its duration.

Speech time is measured the same way everywhere (`core/dialogue.speaking_seconds`): **words ÷ 2.5
plus a breath after every line**. A scene may fill at most 75% of its duration with speech, beyond
about a line's worth of slack. The breath matters: seven lines of seven words take much longer to
play than their word count suggests, and a scene that "fits" on words alone still arrives packed in
its clips.

Either failure triggers **one** repair pass that names the problems scene by scene ("scene 2 holds
8 dialogue lines — about 27 seconds of speech — but at most 21 seconds fit"). Scenes are then merged
one by one — an over-full scene is taken only with less speech (and still a line), a scene with
room only with more dialogue that still fits — so the result never regresses. On any failure the
original story is kept.

### 5. Shot planning (`core/shot_planner.py`)

- `build_characters_block()` passes each character's **voice** with the cast.
- `build_dialogue_instruction()` adds the dialogue rules, only for batches whose scenes carry lines:
  place **every** line verbatim in exactly one shot as `<d>[Language] …</d>`, keep speaking time
  under ~75% of a clip, keep the speaker on screen while delivering, copy the voice verbatim, and
  never turn narration into a character's speech. If lines cannot fit, they are kept anyway — a
  line is never dropped to make it fit.
- `enforce_dialogue_coverage()` checks each scene with `unplaced_dialogue()` (verbatim after
  normalisation, tolerant of punctuation/typos and of a line split across sub-shots). A scene with
  unplaced lines gets one rewrite of its shots; the rewrite is kept only if it places more lines,
  and its clips are scaled back to the scene's planned length.
- `rebalance_speech_durations()` fixes clip pacing without an LLM: planners put long silent clips
  next to short crammed ones, and pack lines unevenly even when the scene fits. Inside a scene,
  time moves from silent clips and from speaking clips with room to spare to the clips whose lines
  need it — never below a clip's last sub-shot cut, and a silent clip never below 3s — so the
  scene's total, shot count and order stay as planned.

### 6. Voice embedding (`core/r2v_composer.py`)

The composer's voice-text embedding used to read only a bound `voice.text`, which no story director
ever wrote — and planners paraphrase voices rather than copying them. It now falls back to
`voice_type`, in shots where someone speaks, so a voice the planner lost is still inserted into
`subject_definitions`. Silent shots keep their prompt unchanged, and a voice note is skipped when
it would push a prompt past the 7,000-character cap.

## Web UI

- **Scene card** — a *Dialogue* block lists the lines (speaker, delivery, words). In edit mode the
  dialogue is a structured editor (speaker from the story cast, line, delivery, add/remove) with a
  live line/word/speech-seconds readout. **Replan** the scene afterwards to place edited lines.
- **Characters** — a *Voice* field per character.
- **Project page** — the scene list shows each scene's dialogue under the narration.

## Tuning

| Setting | Default | Meaning |
| --- | --- | --- |
| `MOVIE_DIALOGUE_SHARE` | `0.40` | share of a film's running time filled with dialogue |
| `MOVIE_NARRATION_SHARE` | `0.15` | share filled with narrator voice-over |

Raise `MOVIE_DIALOGUE_SHARE` for talk-driven films (0.5 ≈ 75 dialogue words per screen minute). Keep
the two shares under ~0.65 so lines still fit their scenes. For a deliberately quiet film, ask for
it in the idea ("a silent chase, only three spoken lines") — the screenplay prompt treats silence as
a choice and the fit check only reacts to clear under-delivery.

## Older projects

Existing movie stories have no `dialogue` on their scenes, so re-planning their shots alone will not
add dialogue. To give an old film a dialogue layer, regenerate its story (or paste `dialogue` lines
into the scenes in the editor) and then re-plan the shots.

## Related code

| File | Role |
| --- | --- |
| `core/dialogue.py` | shared helpers: speech matching, dialogue normalisation, screenplay line extraction, `unplaced_dialogue` |
| `core/story_engine.py` | dialogue language, word budgets, placeholders, fit check |
| `core/shot_planner.py` | voices in the cast block, dialogue rules, coverage enforcement, clip pacing |
| `core/r2v_composer.py` | voice embedding (`voice.text` → `voice_type`) |
| `core/scene_graph.py` | passes `dialogue` through on the CLI path |
| `tests/unit/test_movie_dialogue.py` | unit tests for the whole chain |
