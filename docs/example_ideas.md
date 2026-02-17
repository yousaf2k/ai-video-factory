# Video Idea Examples

This directory contains example video ideas for the AI Video Factory.

## Usage

1. **Default method** - Save your idea as `input/video_idea.txt`:
   ```bash
   # Your idea goes here
   A futuristic city with flying cars and neon lights at night
   ```

2. **Custom file method** - Use `--idea-file`:
   ```bash
   python core/main.py --idea-file input/ideas/nature_documentary.txt
   ```

3. **Command line method** - Use `--idea`:
   ```bash
   python core/main.py --idea "A dragon flying over medieval castle"
   ```

## Example Ideas

### Nature Documentary
```
A majestic eagle soars through mountain mist at sunrise, hunting for prey in a golden valley below. Cinematic wildlife documentary with sweeping aerial views.
```

### Sci-Fi Scene
```
A lone astronaut stands on a red planet looking at a distant blue nebula. Epic space cinematics with dramatic lighting and sense of isolation.
```

### Action Sequence
```
A martial artist fights through a crowded marketplace at night, leaping between stalls. Fast-paced action with dynamic camera movements and sparks flying.
```

### Commercial
```
Close-up of a refreshing drink with condensation droplets, ice cubes clinking, and lime slice. Bright studio lighting with product-focused shots.
```

## Tips for Writing Ideas

- **Be specific** about what you want to see
- **Include style** keywords (documentary, cinematic, epic, etc.)
- **Mention camera work** if you want specific shots (aerial, tracking, drone)
- **Add emotion** to guide the AI's creative choices
- **Keep it concise** - 2-3 sentences is usually enough

## Idea File Format

You can use plain text (.txt) or markdown (.md) files:
- UTF-8 encoding required
- Can be single line or multi-line
- Can include notes or descriptions
- Only the text content will be used as the idea

Example with structure:
```
# My Video Project

Video Idea:
A serene Japanese garden in autumn, with red maple leaves falling into a koi pond.

Style:
Peaceful, meditative, slow-motion nature documentary

Camera:
Static shots, gentle pans, close-ups of fish and leaves
```
