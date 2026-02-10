# AI Agents Folder

This folder contains system prompts for LLM agents used in different stages of video generation.

## Folder Structure

```
agents/
├── story/         - Story generation agents
├── narration/     - Narration script agents
├── image/         - Image prompt engineering agents
└── video/         - Video motion/camera agents
```

## How to Create a Custom Agent

1. **Navigate to the appropriate folder** (e.g., `agents/story/`)

2. **Create a new `.txt` file** with your agent name (e.g., `my_custom_agent.txt`)

3. **Write the system prompt** following this template:

   ```
   You are a [role description]. Your task is to [task description].

   ## Guidelines

   1. [Guideline 1]
   2. [Guideline 2]
   ...

   ## Output Format

   [Specify the expected output format]

   {USER_INPUT}
   ```

4. **Use the agent** by specifying its name:
   ```bash
   python core/main.py --story-agent my_custom_agent
   ```

## Available Agents

### Story Agents (`agents/story/`)
- `default.txt` - Cinematic documentary style
- `dramatic.txt` - Emotional, character-driven narratives
- `documentary.txt` - Factual, educational content

### Narration Agents (`agents/narration/`)
- `default.txt` - Standard voice-over narration
- `documentary.txt` - Educational documentary narration
- `professional.txt` - Professional VO artist style
- `storytelling.txt` - Narrative-driven storytelling

### Image Agents (`agents/image/`)
- `default.txt` - Standard image prompt engineering
- `artistic.txt` - Artistic, aesthetic-focused prompts

### Video Agents (`agents/video/`)
- `default.txt` - Standard motion/camera prompts
- `cinematic.txt` - Hollywood cinematography style

## Agent Prompt Guidelines

1. **Be Specific**: Clearly define the agent's role and task
2. **Include Examples**: Show examples of good inputs/outputs
3. **Define Format**: Specify the exact output format expected
4. **Use Placeholders**: Include `{USER_INPUT}` where user input should be inserted
5. **Keep it Focused**: Each agent should have a clear, single purpose

## Testing Your Agent

To test a new agent:

```bash
# List all agents
python core/main.py --list-agents

# Test with a simple idea
python core/main.py --idea "Test idea" --story-agent my_custom_agent --step 2
```
