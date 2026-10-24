# Story Output Format (shared by documentary and movie bases)

## Video Duration Planning

You are creating a story for a **{VIDEO_LENGTH}-second video**.

### Scene Duration Allocation

You MUST assign a `scene_duration` (in seconds) to each scene.

**Rules**:

1. Each scene must have a `scene_duration` field (integer, in seconds)
2. Sum of all scene_duration must equal {VIDEO_LENGTH}
3. Minimum scene duration: 15 seconds

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
      "voice_type": "Voice requirements",
      "personality": "Key personality traits",
      "attire": "Description of clothing"
    }
  ],
  "scenes": [
    {
      "scene_id": 0,
      "location": "Short name of the setting",
      "characters": "Who is in the scene",
      "action": "What happens in this scene",
      "emotion": "Primary emotion of the scene",
      "narration": "Voice-over text. Write EXACTLY enough text to fill the scene_duration. Since average speaking rate is ~2.5 words per second, a 60-second scene needs ~150 words of narration.",
      "set_prompt": "Detailed background image prompt for this scene's environment (location stays a short name): geography, architecture and key objects with their materials, weather and time of day, lighting, and atmosphere. 2-3 sentences, no people.",
      "scene_duration": 45
    }
  ]
}
```

## Narration Guidelines

- **Speaking Rate**: Maintain approximately 2.5 words per second.
- **Tone**: Match the style requested but always prioritize engagement.
- **Structure**: Ensure each scene transitions logically to the next.
- **Direct Address**: When appropriate, use "you" to involve the viewer.
