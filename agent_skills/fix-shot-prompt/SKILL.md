---
name: fix-shot-prompt
description: Use when the user says a generated shot/video is wrong (character not doing the action, wrong motion, wrong scene) and wants it fixed. Diagnoses the prompt, edits it surgically, and queues regeneration.
---

# Fix a wrong shot

Users usually say things like "shot 4 video prompt the character is not doing it"
or "in shot 12 she should be running, not walking". Follow this procedure:

## 1. Identify the shot
- Ask `get_project_overview` (or `list_shots`) for the active project if you
  haven't this conversation.
- Resolve the user's numbering to a shot id with `list_shots` — users say
  "shot 4" meaning **1-based index 4**. Confirm the shot's scene/camera looks
  like what they describe before editing.

## 2. Read the full prompts
Call `get_shot` and inspect:
- `video_prompt` (timestamped MiniMax H3 prompt — used when prompt_type=video)
- `motion_prompt` (short motion description — used when prompt_type=motion)
- `image_prompt` (the still the video is generated from — for i2v the WRONG
  ACTION often lives here, not in the motion prompt!)

Rule of thumb for i2v/r2v projects: if the **subject pose/action** in the start
frame is wrong → fix `image_prompt` (and regenerate the image first). If the
start frame is fine but the **motion** is wrong → fix `motion_prompt`/`video_prompt`.

## 3. Edit minimally
- Change ONLY the part the user complained about. Keep character descriptions,
  style tokens and camera terms intact — they are tuned for consistency.
- Keep timestamps/structure in `video_prompt` (it is a timestamped format).
- Apply via `update_shot` with only the changed fields.

## 4. Regenerate
- Image wrong → `generate_shot_image` with `force: true`, then tell the user the
  video must be regenerated after the image completes (or queue both — the video
  job waits in the queue behind the image).
- Only motion wrong → `generate_shot_video` with `force: true`.
- Ask before regenerating when the user only asked to "fix the prompt".

## 5. Report
Tell the user exactly: what was wrong in the old prompt, the new wording, and
which queue items were created (they can watch progress on the Queue page).
