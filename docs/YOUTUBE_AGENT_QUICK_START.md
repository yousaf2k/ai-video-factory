# YouTube Documentary Agent - Quick Start Guide

## What Is It?

The YouTube Documentary Agent (`youtube_documentary`) creates viral, high-retention documentary scripts optimized specifically for YouTube. Unlike cinematic agents (Netflix), this agent focuses on:

- Fast pacing and energy
- Multiple hooks throughout (not just opening)
- Pattern interrupts to recapture attention
- Call-to-actions for engagement
- YouTube optimization (titles, thumbnails, SEO)

## Quick Start

### 1. Verify Installation
```bash
python core/main.py --list-agents
```

Look for `youtube_documentary` under STORY agents.

### 2. Generate Your First YouTube Documentary
```bash
python core/main.py --story-agent youtube_documentary --idea "The mystery of the Bermuda Triangle"
```

### 3. With Custom Options
```bash
# Generate 10 scenes (approximately 10-15 minute video)
python core/main.py --story-agent youtube_documentary --max-shots 10 --idea "Hidden world of deep sea creatures"

# Story only (no media generation)
python core/main.py --story-agent youtube_documentary --max-shots 8 --idea "Your topic" --no-narration --step story
```

## What You Get

### Extended JSON Output
```json
{
  "title": "Documentary title",
  "style": "YouTube viral documentary",

  // YouTube Metadata
  "seo_keywords": ["keyword1", "keyword2", "keyword3"],
  "title_options": ["Clickable title 1", "Clickable title 2"],
  "thumbnail_moments": ["Visual hook description 1", "Visual hook description 2"],
  "chapters": [{"time": "0:00", "title": "Opening Hook"}],
  "description_preview": "First 150 characters...",

  // Scenes with hook types
  "scenes": [
    {
      "location": "...",
      "characters": "...",
      "action": "...",
      "emotion": "...",
      "hook_type": "shock | question | tease | pattern_interrupt | breadcrumb | cta",
      "narration": "..."
    }
  ]
}
```

## Hook Types Explained

Each scene uses one of these retention techniques:

| Hook Type | Purpose | Example |
|-----------|---------|---------|
| **shock** | Surprising fact | "What they found had been hidden for 2,000 years" |
| **question** | Rhetorical question | "Why would someone risk everything?" |
| **tease** | Promise of something amazing | "What you're about to see has never been captured" |
| **pattern_interrupt** | Unexpected twist | "But then, something happened that no one predicted" |
| **breadcrumb** | Future tease | "Wait until you see what happens at the end..." |
| **cta** | Call-to-action | "If you enjoyed this, drop a comment below" |

## YouTube-Specific Features

### 1. Opening Hook (First 30 seconds)
- Immediate shock or curiosity
- "You won't believe what happens next..."
- Visual intrigue from frame one

### 2. Pattern Interrupts (Every 45-60 seconds)
- Visual changes, narrative surprises
- Energy shifts to recapture attention
- Quick cuts, transitions, audio changes

### 3. Breadcrumbs & Teasers
- "Stick around to the end to see X"
- "Coming up next: Y"
- Creates anticipation, delivers on promises

### 4. Engagement Elements
- Rhetorical questions for comments
- "What would YOU do?" moments
- Subscribe/like prompts (1-2 per video max)

### 5. YouTube Optimization
- **Titles**: Clickable, 40-60 chars, power words
- **Thumbnails**: High-contrast visual moments designed into scenes
- **SEO**: Keywords, description preview
- **Chapters**: Timestamp suggestions for longer videos

## Usage Tips

### Best Topics
- Mysteries and unexplained phenomena
- True crime and shocking stories
- Science and technology discoveries
- History's secrets and hidden truths
- Amazing facts and mind-blowing information

### Optimal Length
- **8-12 scenes** = 8-15 minute video (sweet spot for YouTube)
- **3-5 scenes** = 3-5 minute video (shorter format)
- **12-15 scenes** = 15-20 minute video (long-form)

### Retention Checklist
Each scene should:
- [ ] Have visual energy or movement
- [ ] Include a hook_type (shock/question/tease/etc)
- [ ] Advance the story or reveal information
- [ ] Create curiosity or emotional response
- [ ] Earn its place (no filler)

## Output Location

Generated stories are saved to:
```
output/sessions/{session_id}/story.json
```

## Comparison: When to Use Which Agent?

| Use Case | Agent |
|----------|-------|
| YouTube videos, viral content | **youtube_documentary** |
| Netflix-style cinematic documentaries | netflix_documentary |
| General documentary content | documentary |
| Dramatic narratives | dramatic |
| Simple storytelling | default |

## Troubleshooting

### Agent Not Found
```bash
# Check if file exists
ls agents/story/youtube_documentary.md

# Re-run agent discovery
python core/main.py --list-agents
```

### LLM Connection Error
Make sure your LLM backend is running (LM Studio, OpenAI, etc.)

### JSON Parse Errors
The agent outputs strict JSON. If you get errors:
1. Check LLM is following the prompt instructions
2. Try adjusting the temperature setting
3. Review the story generation in the session logs

## Examples

### Example 1: Mystery Topic
```bash
python core/main.py --story-agent youtube_documentary \
  --max-shots 10 \
  --idea "The missing crew of the Mary Celeste"
```

### Example 2: Science Discovery
```bash
python core/main.py --story-agent youtube_documentary \
  --max-shots 8 \
  --idea "Scientists discover new species in deep ocean trench"
```

### Example 3: Historical Secret
```bash
python core/main.py --story-agent youtube_documentary \
  --max-shots 12 \
  --idea "The secret library hidden beneath the Vatican"
```

## Advanced Usage

### Custom Session ID
```bash
python core/main.py --story-agent youtube_documentary \
  --idea "Your topic" \
  --session-id my_custom_session
```

### Combine with Other Agents
```bash
# Use YouTube story agent with artistic image prompts
python core/main.py \
  --story-agent youtube_documentary \
  --image-agent artistic \
  --idea "Your topic"
```

### Resume Previous Session
```bash
# The system will prompt to resume if a session exists
python core/main.py --story-agent youtube_documentary
```

## What Makes It Different?

### vs. Netflix Documentary
- **Faster pacing** (45-60 sec scenes vs 2-3 min)
- **Multiple hooks** throughout vs single opening hook
- **Conversational** narration vs cinematic drama
- **Direct engagement** (CTAs) vs passive viewing
- **YouTube metadata** (titles, thumbnails, SEO) vs none

### vs. Default Documentary
- **Platform-optimized** for YouTube algorithm
- **Retention-focused** with pattern interrupts
- **Engagement-driven** with CTAs and questions
- **SEO-enhanced** with keywords and descriptions
- **Viral-oriented** structure and hooks

## Next Steps

1. **Try it out**: Generate your first YouTube documentary story
2. **Review the output**: Check the JSON for YouTube-specific fields
3. **Customize**: Edit the story if needed before media generation
4. **Produce**: Run the full pipeline to create images and videos
5. **Upload**: Use the metadata (titles, descriptions, tags) for YouTube upload

## Support

For detailed implementation information, see:
- `YOUTUBE_AGENT_IMPLEMENTATION_SUMMARY.md` - Full technical documentation
- `agents/story/youtube_documentary.md` - Agent prompt and guidelines
- `validate_youtube_agent.py` - Validation script

## Summary

The YouTube Documentary Agent is ready to use for creating engaging, viral documentary content optimized for YouTube's platform, algorithm, and viewer behavior patterns.
