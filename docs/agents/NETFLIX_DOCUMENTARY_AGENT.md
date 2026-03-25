# Netflix Documentary Agent Documentation

## Overview

The `netflix_documentary` agent creates gripping, binge-worthy dramatic documentaries with mystery, suspense, and high-stakes storytelling typical of Netflix original documentaries.

## Tone Characteristics

### Suspense
- Every scene raises questions
- Builds tension gradually
- Creates emotional investment
- Delivers payoff after buildup

### Excitement
- High-stakes reveals
- Shocking discoveries
- Intense moments
- Dramatic consequences

### Curiosity
- Puzzles waiting to be solved
- Mysteries that need answers
- Unexplained phenomena
- Investigative journey

## Key Features

1. **Mystery-Driven Structure**: Stories framed as investigations or discoveries
2. **Cliffhanger Pacing**: Each scene ends with hooks
3. **Character Focus**: Real people, authentic emotions
4. **Cinematic Language**: Vivid, evocative descriptions
5. **Documentary Authenticity**: Factual accuracy within dramatic framework
6. **High Emotional Stakes**: Life, death, truth, justice

## Usage

### Basic Usage
```bash
# Use the Netflix-style agent
python core/main.py --story-agent netflix_documentary --idea "A small town where five people disappeared without trace"
```

### With Custom Idea File
```bash
# Create idea file
cat > my_netflix_idea.txt <<EOF
An amateur astronomer receives a mysterious pattern from deep space. When it finally returns, the message is terrifying.
EOF

# Generate story
python core/main.py --story-agent netflix_documentary --idea-file my_netflix_idea.txt
```

### In Config
```python
# config.py
STORY_AGENT = "netflix_documentary"
```

## Story Structure

### Scene Progression

**Scenes 1-2: The Hook**
- Establish mystery or question
- Introduce key characters
- Create immediate intrigue
- Raise compelling questions

**Scenes 3-5: The Investigation**
- Follow discovery process
- Build layers of mystery
- Reveal clues gradually
- Increase tension

**Scenes 6-7: The Reveal**
- Deliver major discoveries
- Shock moments
- Character confrontations
- Emotional payoffs

**Scene 8: Resolution**
- Reflect on meaning
- Larger implications
- Philosophical impact
- Lasting impression

### Narrative Arc

1. **Opening Question**: What's happening here?
2. **Deepening Mystery**: Each answer spawns more questions
3. **Raising Stakes**: What's at risk if truth isn't found?
4. **Red Herrings**: False paths that increase tension
5. **The Breakthrough**: Critical discovery that changes everything
6. **The Confrontation**: Facing the truth
7. **The Aftermath**: How discoveries change lives/world

## Output Format

The agent generates JSON with this structure:

```json
{
  "title": "Documentary title",
  "style": "Netflix dramatic documentary",
  "scenes": [
    {
      "location": "Setting with cinematic detail",
      "characters": "People and their emotions",
      "action": "What happens - focus on tension/discovery",
      "emotion": "suspense, shock, awe, curiosity, triumph",
      "narration": "2-3 sentences of gripping narration"
    }
  ]
}
```

## Visual Style Guidance

The agent instructs video generation with:

### Lighting
- Chiaroscuro (light/dark contrast)
- Silhouettes for mystery
- Revealing lights for discoveries
- Moody shadows

### Camera
- Slow pushes into scenes
- Handheld for intensity
- Dramatic pulls for reveals
- Close-ups for evidence/reactions

### Composition
- Framing that emphasizes mystery
- Isolation shots for vulnerability
- Wide shots for scale/awe

### Color
- Cool blues for mystery
- Warm tones for revelations
- High contrast for drama

## Comparison with Other Agents

| Feature | default | dramatic | documentary | **netflix_documentary** |
|----------|---------|-----------|--------------|----------------------|
| Tone | Balanced | Emotional | Factual | **Suspenseful** |
| Pacing | Moderate | Slow | Measured | **Binge-worthy** |
| Style | General | Character | Educational | **Investigative** |
| Focus | Story | Emotion | Information | **Mystery** |
| Hooks | Narrative | Emotional | Curiosity | **Cliffhangers** |

## Best Practices

### 1. Start Strong
- Open with immediate mystery or question
- Don't bury the lead
- Make first 10 seconds count

### 2. Build Tension
- Each scene should increase curiosity
- Use pacing to control information flow
- Save best reveals for right moments

### 3. Emotional Truth
- Ground mysteries in real human stakes
- People's lives, fears, histories
- Authenticity over exaggeration

### 4. Pay Off Setup
- Every question raised should be answered
- Red herrings should make sense in hindsight
- Reveals should feel earned

### 5. End Hard
- Last scene should land emotionally
- Leave viewers thinking
- Create desire for next episode

## Example Prompts

### True Crime
```
A woman in witness protection sees her alleged murderer on national TV - as a celebrated hero. She knows he's not a hero. He's hunting her.
```

### Scientific Mystery
```
Construction workers unearth a perfectly preserved metal box from 10,000 BC - with electronics inside. The technology shouldn't exist.
```

### Historical Investigation
```
In 1845, an entire Arctic settlement of 128 people vanished. Their journals describe something approaching in the ice. What was it?
```

### Supernatural Mystery
```
A family moves into a home where the previous owner vanished. They discover recordings of something that shouldn't exist. But now it knows they're here.
```

## Tips for Best Results

### Idea Development
- Focus on unsolved mysteries or extraordinary events
- Include clear stakes (life, death, truth, justice)
- Have a specific question at the center
- Consider what makes it binge-worthy

### Character Focus
- Real people with genuine emotions
- Experts or witnesses with credibility
- Relatable motivations and fears
- Clear emotional journeys

### Pacing Control
- Don't reveal everything at once
- Let suspense build between scenes
- Use cliffhangers strategically
- Save biggest reveals for impact moments

### Narrative Voice
- Use cinematic, evocative language
- Balance mystery with facts
- Create visual descriptions that demand cinematography
- Write narration that complements, not duplicates, visuals

## Troubleshooting

### Story Not Suspenseful Enough
- **Increase mystery**: Add more questions, fewer answers
- **Add consequences**: What's at risk? What happens if truth isn't found?
- **Slow reveals**: Don't rush discoveries
- **Build dread**: Let tension accumulate

### Scenes Feel Like Regular Documentary
- **Add cliffhangers**: Each scene should end with hook
- **Emphasize unknown**: What don't we know? What's possible?
- **Raise stakes**: Make discoveries matter more
- **Create urgency**: Time pressure, danger, consequences

### Too Much Information, Not Enough Mystery
- **Deepen mystery**: Add layers, complications, red herrings
- **Character reactions**: Show emotions, not just facts
- **Visual tension**: Describe lighting, camera angles
- **Pacing clues**: Distribute reveals across scenes

## File Locations

- **Agent**: `agents/story/netflix_documentary.md`
- **Examples**: `input/examples/netflix_style_ideas.md`
- **Documentation**: `NETFLIX_DOCUMENTARY_AGENT.md`

## Netflix Reference Style

Study these Netflix documentary patterns:

### Opening Sequences
- Dramatic reenactment tease
- Narrator setup with intrigue
- Title card with mood-setting music
- "What happens next will shock you"

### Episode Structure
- Cold open (mystery hook)
- Investigation (building case)
- Midpoint twist (changes direction)
- Climax reveal (major discovery)
- Final reflection (meaning/implications)

### Cinematic Language
- "What they found would change everything"
- "But the truth was far more shocking"
- "In that moment, everything they knew was wrong"
- "The answer had been hiding in plain sight"

### Signature Elements
- Experts with credibility
- Evidence that challenges assumptions
- Personal stakes for investigators
- Local color and atmosphere
- Reenactments with dramatic lighting
- Archival footage integration
- Final twist that recontextualizes

## See Also

- `input/examples/netflix_style_ideas.md` - Example ideas crafted for this agent
- `IDEA_FILE_README.md` - How to use idea files
- `LOGGING_README.md` - Understanding generated logs
