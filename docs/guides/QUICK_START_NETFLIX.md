# Quick Start: Netflix Documentary Agent

## 🎬 Generate Your First Netflix-Style Documentary

### Step 1: Choose Your Idea

Pick from examples or create your own:

**Option A: Use Example Ideas**
```bash
cd input/examples
cat netflix_style_ideas.md
```

**Option B: Create Your Own**
```bash
echo "An amateur astronomer receives a mysterious signal from deep space. When it decodes, it's coordinates to a location that shouldn't exist." > my_mystery.txt
```

### Step 2: Generate Story

```bash
# With example ideas
python core/main.py --story-agent netflix_documentary --idea-file "input/examples/netflix_style_ideas.md"

# With your own idea
python core/main.py --story-agent netflix_documentary --idea-file my_mystery.txt

# Or inline
python core/main.py --story-agent netflix_documentary --idea "A small town where five people vanished overnight without trace"
```

### Step 3: Review Generated Story

The output will be saved to:
```
output/sessions/session_XXXXXX_XXXXXX/story.json
```

Look for:
- Suspenseful scene descriptions
- Mystery-driven narrative arc
- High-stakes emotional moments
- Cliffhanger scene endings
- Gripping narration

### Step 4: Continue Pipeline

```bash
# Story generates automatically, continue to shots
python core/main.py --step 4
```

## 🎯 Netflix Style Characteristics

Your generated story will have:

### Suspense
- Questions raised in every scene
- Tension building gradually
- Answers delayed for impact
- Emotional hooks at scene ends

### Excitement
- Shocking discoveries
- High-stakes reveals
- Dramatic confrontations
- Consequences that matter

### Curiosity
- Puzzles to solve
- Mysteries to unravel
- Unexplained phenomena
- Investigative journey

## 📝 Example Ideas to Try

### Mystery & Vanishing
```
A small town where five people disappeared without a trace over twenty years. Now, fresh evidence has emerged, and investigators must uncover what really happened.
```

### Scientific Anomaly
```
Construction workers unearth a perfectly preserved metal box - dated 10,000 BC - with electronics inside. The technology is impossible for its time.
```

### True Crime
```
A woman in witness protection sees her alleged murderer on national television - as a celebrated hero. She knows he's not a hero. He's hunting her.
```

### Historical Reinvestigation
```
New evidence suggests Blackbeard was actually a woman disguised as a man. The treasure was never gold - it was something far more valuable.
```

## 🔑 Key Elements

For best Netflix-style results, ensure your ideas have:

1. **Central Mystery** - What question needs answering?
2. **High Stakes** - Life, death, truth, justice
3. **Real People** - Authentic characters with emotions
4. **Clear Payoff** - Discovery that rewards investigation
5. **Lasting Impact** - Truth that changes understanding

## 🎬 Visual Results

Expect cinematic scenes with:

- **Lighting**: Moody shadows, revealing lights, high contrast
- **Camera**: Slow pushes, dramatic pulls, handheld intensity
- **Composition**: Framing that emphasizes mystery/isolation
- **Color**: Cool blues for mystery, warm tones for revelations

## 📚 Full Documentation

- `NETFLIX_DOCUMENTARY_AGENT.md` - Comprehensive guide
- `NETFLIX_AGENT_SUMMARY.md` - Implementation details
- `input/examples/netflix_style_ideas.md` - 15+ example ideas

## 🚀 Quick Commands

```bash
# List all story agents
python -c "from core.agent_loader import AgentLoader; print(AgentLoader().list_agents('story'))"

# Verify Netflix agent works
python -c "from core.agent_loader import load_agent_prompt; print(load_agent_prompt('story', 'test', 'netflix_documentary')[:200])"

# Generate with example idea
python core/main.py --story-agent netflix_documentary --idea "A mysterious signal from deep space"
```

## ✨ Tips

- **Start with mystery** - Let viewers know "something's wrong"
- **Build gradually** - Don't reveal everything at once
- **Use real stakes** - Life, death, truth, justice
- **End hard** - Make last scene land emotionally
- **Create hooks** - Each scene should need next episode

## 🔍 Troubleshooting

**Story not suspenseful?**
- Add more questions, fewer answers
- Include consequences and risks
- Use cliffhanger scene endings

**Too much information?**
- Slow down reveals
- Build tension between scenes
- Add red herrings
- Deepen mystery layers

**Low emotional impact?**
- Focus on people, not just facts
- Add personal stakes
- Show character emotions
- Create urgency

Ready to create binge-worthy content! 🎬
