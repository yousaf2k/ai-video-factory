# Bugfix: Missing Dynamic Narration Length Scaling

## Symptoms

The user noticed that regardless of a scene's duration (e.g., 45 seconds or 75 seconds), the generated voice narration was always almost exactly the same length. A 60-second scene needs at least 50-60 seconds of conversational TTS to prevent awkward silent gaps, but the LLM repeatedly yielded very short snippets.

## Root Cause

All 16 different story generator agents (`agents/story/*.md` explicitly mandated constraints like:
`"narration": "Your voice-over narration describing the experience (2-3 sentences)"`
Because of this hardcoded instruction across `netflix_documentary.md`, `time_traveler.md`, `selfie_vlogger.md`, and others, the LLM deliberately stunted its generation to only a few sentences regardless of the `scene_duration`.

## Resolution

1. A Python script (`update_story_agents.py`) was executed to strip the matching `(2-3 sentences)` rules from the JSON schema examples and the explicit "Pacing" constraints.
2. Replaced the static rules with dynamic instructions parameterized against the speech rate constraint:
   `Write EXACTLY enough text to fill the scene_duration. Since average speaking rate is ~2.5 words per second, a 60-second scene needs ~150 words of narration.`

## Affected Files

- `agents/story/*.md` (All 16 story agent variants)
