# Video Prompt Rules (MiniMax H3 I2VA)

The `video_prompt` field is a detailed, timestamped video generation prompt that follows this exact structure. It describes ONE rendered clip (the shot duration is provided in the input); the clip may contain multiple timestamped camera sub-shots.

## Required Structure

The prompt MUST follow this exact format:

```text
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.

integrated_multimodal_description: [Shot 1] ...

overall_soundscape: ...

non_diegetic_music: ...
```

- The first line is ALWAYS the I2VA first-frame instruction (the shot's generated image is `<Picture 1>` at 0.00 seconds and belongs to `[Shot 1]`), followed by one blank line.
- Keep the image anchor consistent: preserve subject identity, clothing, colors, key objects and spatial relationships from the shot's `image_prompt`.
- Structure of Shot 1: **first-frame anchor → action onset → continuous development → result or reaction**.

## Shots and Cuts

- `[Shot 1]` begins the description and has NO timestamp. Start it by stating the overall style (`Live-action, cinematic`, `3D CG`, `2D-animated`, etc.) and initial composition.
- Later shots use sequential numbers with a strictly increasing cut time inside the clip duration, e.g. `[Shot 2] At 00:03.500, the camera cuts to...`
- Cut times MUST stay within the clip duration (e.g. a 5-second clip cannot have a cut after 00:05.000).
- Use plain cuts (`the camera cuts to`, `the shot transitions to`). A cut must introduce new information (subject, space, viewpoint or time); for small framing changes prefer camera motion.
- Most single clips work best with 1-3 sub-shots. Use more only if the action truly requires it.

## Camera Motion

Write camera motion as a natural English action inside the shot, combining motion type + amplitude + speed when meaningful (omit medium amplitude / normal speed):

- Motion types: Zoom In/Out, Push In/Pull Out, Pan Left/Right, Truck Left/Right, Tilt Up/Down, Pedestal Up/Down, Arc Shot, Tracking Shot, Static Shot, Shake Slightly/Strongly, POV, Roll Clockwise/Counterclockwise.
- Amplitude: `with small amplitude`, `with large amplitude`. Speed: `at slow speed`, `at fast speed`.
- Example: `The camera pushes in with small amplitude at slow speed toward the folded letter in her hands.`

## Dialogue, Speakers and On-Screen Text

- Speaking subjects use stable IDs `(S1)`, `(S2)`; together `(S1,S2)`. A speaker keeps the same ID across sub-shots. Establish identity on first appearance (age, gender, voice quality).
- Spoken content goes inside `<d>` with a language tag, preserved verbatim: `The young woman with a quiet, breathy voice (S1) says: <d>[English] I get off at the next station.</d>`
- For voiceover: `says in an off-screen voiceover` followed by `<d>...</d> while his lips remain completely closed.`
- Visible on-screen text goes in double quotes, preserved verbatim: `A red neon sign reading "OPEN" glows above the doorway.`

## overall_soundscape

1-4 sentences in one continuous paragraph summarizing ambient sound, physical action sounds and non-verbal human sounds across the WHOLE clip. Do NOT repeat dialogue or music already in the description. Only use `N/A` if complete silence is required.

## non_diegetic_music

1-3 sentences describing background music only the audience hears (instrumentation, tempo, dynamics - no mood words). Use `N/A` when there is none.

## Output

The `video_prompt` value must be the complete prompt text described above (all fields, blank lines between them) as a single JSON string. It must NOT contain JSON syntax itself and must be self-contained - it is sent to the video model exactly as written.
