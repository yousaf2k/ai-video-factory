# ASMR Glass Cutting - User Guide

## Overview

The ASMR Glass Cutting project type generates cinematic ASMR videos of glass sculpture fruits and vegetables being cut. Each video features ultra-realistic glass textures, satisfying cutting sounds, and professional food ASMR styling.

## Features

- **Natural Language Input**: Describe what you want in plain English
- **Smart Object Extraction**: Agent extracts specific objects from your description
- **Category Expansion**: Say "red fruits" and get 5-10 specific fruits
- **Glass Sculpture Style**: All prompts follow consistent glass sculpture aesthetics
- **Single LLM Call**: Fast generation with one API call
- **ASMR Audio**: Prompts include satisfying sound descriptions

## Usage Examples

### Specific Objects

```bash
python core/main.py \
  --idea "create videos of strawberry, apple, and tomato" \
  --story-agent asmr/asmr_glass_cutting
```

**Output**: 3 shots (one per object)

### Category Expansion

```bash
python core/main.py \
  --idea "tropical fruits" \
  --story-agent asmr/asmr_glass_cutting
```

**Output**: 5-10 shots (agent expands the category)

### Mixed Input

```bash
python core/main.py \
  --idea "make ASMR videos for summer fruits like watermelon and mango" \
  --story-agent asmr/asmr_glass_cutting
```

**Output**: 5-10 shots including mentioned fruits

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--shot-length` | 5 | Duration per shot in seconds |
| `--aspect-ratio` | 16:9 | Video aspect ratio (16:9, 9:16, 1:1, etc.) |
| `--story-agent` | asmr/asmr_glass_cutting | Agent to use for generation |

## Input Tips

✅ **Good Inputs:**
- "create videos of strawberry, banana, and orange"
- "make ASMR cutting videos for tropical fruits"
- "generate videos for red fruits"
- "I want cutting videos of summer fruits"

❌ **Avoid:**
- Comma-separated lists without context: "strawberry, apple, tomato"
- Too vague: "make some videos"
- Non-food objects: "cut a car" (agent expects fruits/vegetables)

## Output Structure

### Story JSON

```json
{
  "title": "ASMR Glass Cutting - Strawberry, Apple, Tomato",
  "project_type": 4,
  "expanded_objects": ["strawberry", "apple", "tomato"],
  "total_duration": 15,
  "shots": [...]
}
```

### Shot Structure

Each shot includes:
- `object_name`: The fruit/vegetable being cut
- `prompt`: Detailed glass sculpture cutting prompt
- `duration`: Shot length in seconds
- `camera`: "closeup_macro"
- `motion_strength`: "medium"

## Prompt Style

All generated prompts follow the glass sculpture style:

- **Material**: Glass with realistic internal structures
- **Visuals**: Reflective, sparkling, internal highlights
- **Lighting**: Cinematic, shallow depth of field
- **Camera**: Macro close-up
- **Audio**: ASMR-style sounds
- **Setting**: Wooden cutting board
- **Action**: 3-4 clean cuts, pieces separate

## Web UI Usage

1. Create a new project
2. Select agent: `asmr/asmr_glass_cutting`
3. Enter your idea: "create videos of tropical fruits"
4. Click "Generate Story"
5. Review shots and proceed to image/video generation

## Troubleshooting

**Problem**: "Could not identify objects from input"
- **Solution**: Be more specific about fruits or vegetables

**Problem**: Only 1-2 shots generated
- **Solution**: This is normal for specific objects. Use category expansion for more shots

**Problem**: Prompts don't mention glass
- **Solution**: The agent should automatically use glass style. If not, check the agent prompt file

**Problem**: Total duration seems wrong
- **Solution**: total_duration = shot_count × shot_duration. Check both values

## Examples Gallery

### Red Fruits
```bash
python core/main.py \
  --idea "red fruits" \
  --story-agent asmr/asmr_glass_cutting
```
Generates: Strawberry, Apple, Tomato, Cherry, Raspberry, Watermelon, etc.

### Tropical Fruits
```bash
python core/main.py \
  --idea "tropical fruits" \
  --story-agent asmr/asmr_glass_cutting
```
Generates: Mango, Pineapple, Papaya, Coconut, Guava, etc.

### Common Vegetables
```bash
python core/main.py \
  --idea "common salad vegetables" \
  --story-agent asmr/asmr_glass_cutting
```
Generates: Tomato, Cucumber, Bell Pepper, Carrot, Lettuce, etc.
