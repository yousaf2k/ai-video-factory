# Music Workflows

Drop ComfyUI music-generation workflows (API JSON or Workflow JSON) in this folder.
They are auto-discovered at startup into `config.MUSIC_WORKFLOWS` and appear as
selectable "Music Workflows" in the generation dialog (next to image/video/soundfx).

## Sample

- `acestep_t2m.json` — native ComfyUI ACE-Step text-to-music (instrumental).
  Requires the ACE-Step checkpoint (e.g. `ace_step_v1_3.5b.safetensors`) in
  `ComfyUI/models/checkpoints/`. Custom-node variants (e.g. `ACEStepSampler`
  from ACE-Step-ComfyUI) also work.

## Node discovery (title tags)

Tag node titles in the ComfyUI editor (or `_meta.title` in API JSON):

| Tag | Meaning | Fallback heuristic |
|-----|---------|--------------------|
| `[prompt]` | Music style/mood prompt input | `ACEStepSampler` / `TextEncodeAceStepAudio` / node with a `prompt`-ish input |
| `[lyrics]` | Lyrics input (optional; defaults to `[inst]` instrumental) | — |
| `[duration]` | Duration in seconds (optional; auto-set to shot/scene length, capped) | — |
| `[audio_out]` / `[out_audio]` / `[save_audio]` | Audio output/save node | `SaveAudio*` / `PreviewAudio*` / `VHS_VideoCombine` |

A workflow is only registered when both a prompt node and an output node resolve.

## Input keys

The generator sets the prompt by auto-detecting the node's input name:
`description` (native ACE-Step) → `prompt` → `text`. Lyrics are written to a
`lyrics` input when present. The output filename goes to `filename_prefix`.

Outputs of type `audio` are used directly; `video` outputs (audio muxed) are
extracted to `.mp3` with ffmpeg.

## Generation modes

- `comfyui` (default) — runs the selected workflow on ComfyUI.
- `geminiweb` — sends `"Create a music: <prompt>"` to the Gemini web UI via
  browser automation and downloads the returned audio attachment.

Configure via Settings (`music_generation_mode`, `music_workflow`) or per-request
in the generation dialog.
