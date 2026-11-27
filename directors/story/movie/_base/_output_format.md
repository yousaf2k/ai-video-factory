# Story Output Format (Screenplay → Scenes with Dialogue)
#
# Movie-family override of the shared story/_output_format.md. The movie base
# layers sit in this folder, so their include of `_output_format` resolves here
# first; documentaries and the other narrated families keep the shared format.

## Video Duration Planning

You are breaking a screenplay into scenes for a **{VIDEO_LENGTH}-second film**.

### Scene Duration Allocation

You MUST assign a `scene_duration` (in seconds) to each scene.

**Rules**:

1. Each scene must have a `scene_duration` field (integer, in seconds)
2. Sum of all scene_duration must equal {VIDEO_LENGTH}
3. Minimum scene duration: 15 seconds

### Spoken-word Budget (speech has to fit the screen time)

Speech runs at ~2.5 words per second and needs room to act. Across the whole film the scenes must carry about **{DIALOGUE_WORD_COUNT} words of dialogue** and about **{NARRATION_WORD_COUNT} words of narration**.

Words are hard to count; lines are easy, so budget in lines:

- **A scene holds at most `scene_duration ÷ 7` dialogue lines** (round down): a 15-second scene has room for 2, a 24-second scene for 3, a 40-second scene for 5. Never exceed it.
- **Every line is short: at most 12 words**, one breath. A longer thought becomes an exchange.
- Narration is speech too and takes room from the same budget: keep it brief in scenes that carry a conversation, and never add narration to a scene that already uses its full line budget.
- Plan the scene durations around the conversations: a scene that carries a conversation needs its lines' worth of time, so prefer fewer, longer scenes over many short ones, and give dialogue scenes the time.
- In a scene with two or more speaking characters, dialogue takes at least two thirds of the spoken words.
- If the screenplay has more lines than the film has time for, keep the strongest ones — always the opening and the closing line of each conversation — rather than overfilling scenes.

## Output Format

Respond with a single valid JSON object only — no commentary before or after it. Markdown code fences are tolerated but not needed:

```json
{
  "title": "Video title here",
  "description": "A short, engaging description of the video",
  "tags": ["tag1", "tag2", "tag3"],
  "seo_keywords": ["keyword1", "keyword2", "keyword3"],
  "title_options": [
    "Intriguing title 1",
    "Intriguing title 2",
    "Intriguing title 3"
  ],
  "thumbnail_moments": [
    "Description of visual hook for thumbnail 1",
    "Description of visual hook for thumbnail 2"
  ],
  "thumbnail_prompt_16_9": "A highly detailed, cinematic prompt for a 16:9 Youtube thumbnail image",
  "thumbnail_prompt_9_16": "A highly detailed, cinematic prompt for a 9:16 Shorts/TikTok thumbnail image",
  "chapters": [
    {"time": "0:00", "title": "Introduction"},
    {"time": "2:30", "title": "The Main Core"}
  ],
  "description_preview": "First 150 characters of video description for SEO",
  "style": "Description of the visual and narrative style",
  "characters": [
    {
      "name": "Character Name",
      "image_prompt": "Detailed cinematic prompt defining both face and full body appearance on white background",
      "voice_type": "Speaking voice, described so a stranger could imitate it: apparent age, gender, pitch, timbre, pace and accent (e.g. \"Tired man in his late thirties, low husky voice, slow breathless delivery, rural Punjabi accent speaking Urdu\"). Every character who has a line needs one — it is copied word for word into the video prompt of every shot they speak in.",
      "personality": "Key personality traits, what they desire, and how they speak (vocabulary, rhythm, verbal habits)",
      "attire": "Description of clothing"
    }
  ],
  "scenes": [
    {
      "scene_id": 0,
      "location": "Short name of the setting",
      "characters": "Who is in the scene",
      "action": "The physical action the camera sees in this scene (spoken lines go in \"dialogue\", not here)",
      "emotion": "Primary emotion of the scene",
      "narration": "Voice-over text: ONLY what the narrator says over this scene. An empty string \"\" when the narrator is silent.",
      "dialogue": [
        {"speaker": "Character Name", "line": "The exact words the character says.", "delivery": "hopeful, half-whispered"},
        {"speaker": "Second Character", "line": "Their reply, exactly as spoken.", "delivery": "flat, not turning around"},
        {"speaker": "Character Name", "line": "The next line in playing order.", "delivery": "a nervous laugh underneath"}
      ],
      "music_prompt": "Instrumental background music direction for this scene: genre/mood, tempo, key instruments, dynamics (e.g., 'slow melancholic piano with ambient pads, 70 BPM, builds to warm strings'). No lyrics, no vocals, 1-2 sentences.",
      "set_prompt": "Detailed background image prompt for this scene's environment (location stays a short name): a WIDE ESTABLISHING VIEW of the empty space — geography, architecture and key objects with their materials, weather and time of day, lighting, atmosphere. Not a close-up, not a single-object shot, no camera/cinematography language; 2-3 sentences, no people.",
      "scene_duration": 45
    }
  ]
}
```

## Dialogue Rules (the screenplay's lines MUST survive this pass)

1. **Carry every line over.** Every dialogue line of the master script is spoken in exactly one scene and must appear in that scene's `dialogue` array **verbatim** — same words, same language, same script. Do not paraphrase, shorten, translate, merge away or drop a line. You may ADD lines to build fuller conversations, within the line budget; never remove.
   - One exception, **dialogue language**: this film's dialogue language is {DIALOGUE_LANGUAGE}. If a master-script line was written in another language, write that line in the film's dialogue language instead — a faithful translation that keeps its meaning and tone, in the language's own script. Lines already in that language stay verbatim. Every line of the film ends up in that one language and script.
2. **Order is playing order.** List the lines in the order they are spoken; a conversation alternates speakers.
3. `speaker` is the exact `name` of a character from `characters`. The narrator never appears here.
4. `line` holds only the spoken words — no quotes, no speaker name, no stage directions — and at most 12 words. `delivery` is a short acting note.
5. **Write the conversation, not a summary.** Where the master script summarizes an exchange ("they argue about the debt"), write the actual exchange — within the scene's line budget — instead.
6. **Never replace dialogue with narration.** A scene the master script plays as dialogue stays a dialogue scene, even if that leaves its `narration` empty.
7. Keep the dialogue in the language and script the master script uses for it. Write every other field in English.

## Narration Rules

- `narration` is the narrator's voice-over only — the film's inner voice: the opening hook, transitions, the closing line, a thought no character would say aloud.
- It must NOT describe the action (the `action` field and the shots carry that) and must NOT repeat what the characters say.
- Across the film, narration totals about {NARRATION_WORD_COUNT} words. Many dialogue scenes need none at all.
