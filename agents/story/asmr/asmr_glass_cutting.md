# ASMR Glass Sculpture Cutting Story Generator

## Task
Generate ASMR glass cutting video shots in JSON format. Each video will feature precision glass sculpting with satisfying audio feedback and visual crack propagation effects.

Extract objects from natural language input. For specific objects (e.g., "create videos of strawberry, apple, and tomato"), use exactly those objects. For categories (e.g., "red fruits", "tropical fruits"), expand to 5-10 specific objects.

## Input
{USER_INPUT}

## Object Extraction Rules

1. **Specific Objects**: If user lists specific objects (e.g., "strawberry, apple, tomato"), use those exact objects
2. **Categories**: If user provides a category (e.g., "red fruits", "tropical fruits"), expand to 5-10 specific examples
3. **Natural Language**: Parse sentences like "create videos for the fruits strawberry, banana, orange" correctly
4. **Multiple Objects**: Support any number of objects from 1 to 10

## Glass Sculpture Style Guidelines

### Material Quality
- **Crystal Clear Glass**: Ultra-transparent, refractive light beams showing rainbow prisms
- **Realistic Texture**: Glass sculptures with realistic internal structures
- **Reflective Surfaces**: Slightly tinted, sparkling internal highlights
- **Photorealistic**: Ultra 8K quality, professional food ASMR style

### Visual Quality
- **Macro Close-up**: Shallow depth of field, blurred background
- **Cinematic Lighting**: Soft backlighting, rim lighting, internal refraction
- **Wooden Cutting Board**: Professional ASMR setting
- **No Background Distractions**: Focus on the glass sculpture

### Image Prompt (Static Shot)
- **Complete Object**: Show the full glass sculpture intact on cutting board
- **Horizontal Knife**: Sharp knife positioned HORIZONTALLY above the object, blade parallel to the cutting board
- **NOT Vertical**: Knife should NOT be vertical or straight down - must be horizontal/angled like real cutting
- **Before Cutting**: No cuts, no cracks, object is whole
- **Tension**: Anticipation of the cut, knife poised in mid-air
- **Static**: Frozen moment before action begins

### Video/Motion Prompt (Action)
- **3-4 Clean Cuts**: Precision cutting through the glass sculpture
- **Pieces Separate/Fall Off**: Glass pieces separating naturally with realistic physics
- **Satisfying Cracks**: Visible crack propagation through glass
- **Light Refraction**: Rainbow prisms through glass pieces

### Audio Focus
- **Glass Clinks**: Crystal clear glass cutting sounds
- **Crisp Cutting**: Satisfying cracking as glass separates
- **ASMR-style**: High-quality audio feedback

## Example Prompts

### Example 1: Strawberry

**Image Prompt** (static - complete object, horizontal knife):
"Ultra 8K photorealistic image, close-up macro shot of a complete intact strawberry glass sculpture resting on a wooden cutting board. The glass sculpture has realistic strawberry shape with embedded golden seeds visible through the crystal clear glass. Features realistic strawberry texture with slight red tint and sparkling reflective surface. A sharp stainless steel knife is positioned HORIZONTALLY above the strawberry, blade parallel to the cutting board, poised to slice through. The knife blade is held horizontally at a slight angle, creating realistic cutting preparation. No cuts or cracks yet - the strawberry is completely whole and intact. Light catches on the glass surfaces creating rainbow prisms and internal highlights. Shallow depth of field with blurred wooden cutting board background. No hands visible. Professional food photography style, cinematic lighting with soft backlight and rim lighting."

**Motion Prompt** (video - cutting action):
"Highly realistic ultra 8K ASMR video, close-up macro shot of precision cutting through a strawberry glass sculpture. The glass sculpture has a strawberry shape with embedded golden seeds visible through the crystal clear glass. Sharp knife makes 3-4 clean precise cuts through the glass strawberry. As the knife cuts, you see satisfying crack propagation through the glass. The pieces separate or fall off the main sculpture with realistic physics. Light catches on the glass surfaces creating rainbow prisms and sparkling highlights. The strawberry has detailed internal glass structure visible through the cuts. Shallow depth of field with blurred wooden cutting board in background. No people or hands visible, just the knife and glass sculpture. Professional food ASMR style, cinematic lighting."

### Example 2: Red Apple

**Image Prompt** (static - complete object, horizontal knife):
"Ultra 8K photorealistic image, macro close-up of a complete intact red apple glass sculpture resting on a wooden cutting board. The glass apple has realistic apple shape with embedded lighter-colored glass core and seed details visible through transparent material. Slight red tint with sparkling internal highlights and crystal clear transparency. A sharp knife blade is positioned HORIZONTALLY above the apple, blade parallel to cutting board surface, ready to slice through horizontally. The knife is held at a realistic cutting angle, frozen mid-air above the intact apple, creating dramatic tension. No cuts have been made yet - the apple is completely whole. Light refracts through the glass creating subtle rainbow prisms. Shallow depth of field, blurred wooden cutting board background. Cinematic lighting with soft backlight. No hands visible. Professional ASMR food photography."

**Motion Prompt** (video - cutting action):
"Ultra 8K ASMR video, macro close-up of a red apple glass sculpture being cut with precision. The glass apple has realistic apple shape with embedded lighter-colored glass core and seed details visible through transparent material. Slight red tint with sparkling internal highlights. Sharp knife makes 3-4 clean cuts through the glass apple. Satisfying crack propagation visible as the knife cuts through. Glass pieces separate and fall with realistic physics. Light refracts through glass creating rainbow prisms. Detailed internal glass structure of the apple visible. Shallow DOF, blurred wooden cutting board background. Cinematic lighting, no hands visible. Professional ASMR quality."

### Example 3: Tomato

**Image Prompt** (static - complete object, horizontal knife):
"Ultra 8K photorealistic image, macro close-up of a complete intact tomato glass sculpture on a wooden cutting board. Realistic tomato-shaped glass sculpture with deep red tint and visible internal lighter-colored glass seed chambers. The glass has a slight shell-like texture with sparkling internal highlights. A sharp knife blade is positioned HORIZONTALLY above the tomato, blade parallel to the cutting board surface, poised to slice horizontally through. The knife is held at a realistic cutting angle, frozen in position before the first cut. The tomato is completely intact with no cuts or cracks. Light catches on the curved glass surfaces creating rainbow refraction and sparkling highlights. Detailed internal glass structure is visible through the transparent material. Shallow depth of field with blurred wooden background. Cinematic lighting, no hands visible. Professional food photography style."

**Motion Prompt** (video - cutting action):
"Ultra 8K ASMR macro video, precision cutting of a tomato glass sculpture. Realistic tomato-shaped glass sculpture with deep red tint and visible internal lighter-colored glass seed chambers. The glass has a slight shell-like texture. Sharp knife makes 3-4 clean cuts through the glass tomato. Satisfying cracking sounds as glass separates with visible crack propagation. Tomato pieces fall or separate with realistic physics. Light catches on glass surfaces creating sparkling highlights and rainbow refraction. Detailed internal glass structure visible through cuts. Shallow DOF, blurred wooden background. No hands visible. Professional food ASMR quality."

## Output JSON Schema

```json
{
  "project_type": "asmr_glass_cutting",
  "title": "ASMR Glass Cutting - [Category or Objects]",
  "user_input": "[original user input]",
  "expanded_objects": ["object1", "object2", "object3"],
  "total_duration": 15,
  "aspect_ratio": "16:9",
  "shots": [
    {
      "id": "shot_001",
      "index": 1,
      "object_name": "strawberry",
      "image_prompt": "Ultra 8K photorealistic image, close-up macro shot of a complete intact strawberry glass sculpture...",
      "motion_prompt": "Highly realistic ultra 8K ASMR video, close-up macro shot of precision cutting through a strawberry glass sculpture...",
      "duration": 5,
      "camera": "closeup_macro",
      "motion_strength": "medium",
      "shot_type": "asmr_glass_cutting"
    }
  ]
}
```

## Critical Format Requirements

### expanded_objects Array
**MUST be a simple array of object name strings**

✅ CORRECT:
```json
"expanded_objects": ["strawberry", "apple", "tomato"]
```

❌ WRONG:
```json
"expanded_objects": [
  {"object": "strawberry", "material": "glass"},
  {"object": "apple", "material": "glass"}
]
```

### shots Array
Each shot MUST include:
- `id`: Unique shot identifier (e.g., "shot_001", "shot_002")
- `index`: Sequential number starting from 1
- `object_name`: Simple object name string
- `image_prompt`: Static shot description - complete object with HORIZONTAL knife above, blade parallel to cutting board (100+ words)
- `motion_prompt`: Video action description - cutting through the object (100+ words)
- `duration`: Fixed duration per shot (default 5 seconds)
- `camera`: "closeup_macro" for all shots
- `motion_strength`: "medium" for all shots
- `shot_type`: "asmr_glass_cutting" for all shots

## Important Rules

1. **expanded_objects Format**: MUST be simple string array, NOT array of objects
2. **One Shot Per Object**: Each object in expanded_objects gets exactly one shot
3. **Two Prompts Per Shot**: Must generate BOTH `image_prompt` (static) AND `motion_prompt` (action)
4. **image_prompt**: Shows complete intact object with knife in air - NO cutting, NO cracks
5. **motion_prompt**: Shows the cutting action with cracks, pieces falling, physics
6. **Prompt Detail**: Each prompt (image and motion) must be 100+ words following the example style
7. **Fixed Duration**: All shots use same duration (default 5 seconds)
8. **Camera**: Always "closeup_macro"
9. **Natural Language Parsing**: Correctly extract objects from sentences like "create for the fruits strawberry, banana, orange"
10. **Category Expansion**: For categories, generate 5-10 specific objects
11. **Project Type**: Must be "asmr_glass_cutting"

## Shot Prompt Template

For each object, generate TWO separate prompts:

### image_prompt (Static Shot - Before Cutting)
Generate a frozen moment BEFORE cutting begins:
1. **Opening**: "Ultra 8K photorealistic image, close-up macro shot of a complete intact [object] glass sculpture..."
2. **Object Description**: Glass sculpture details (shape, color, texture, internal structure) - COMPLETE and INTACT
3. **Knife Position**: Sharp knife positioned HORIZONTALLY above the object, blade parallel to cutting board, held at realistic cutting angle (NOT vertical/straight down)
4. **No Action Yet**: Object is whole, no cuts, no cracks, no pieces fallen
5. **Anticipation**: Knife poised creating dramatic tension before the cut
6. **Camera/Background**: Shallow DOF, blurred wooden cutting board, no hands visible
7. **Style**: Professional food photography, cinematic lighting with backlight and rim lighting

### motion_prompt (Video - Cutting Action)
Generate the cutting action sequence:
1. **Opening**: "Highly realistic ultra 8K ASMR video, close-up macro shot of precision cutting through a [object] glass sculpture..."
2. **Object Description**: Glass sculpture details (shape, color, texture, internal structure)
3. **Action**: Sharp knife making 3-4 clean cuts through the glass [object]
4. **Visual Effects**: Crack propagation, pieces separating/falling, light refraction, rainbow prisms
5. **Internal Details**: Visible internal glass structure through cuts
6. **Camera/Background**: Shallow DOF, blurred wooden cutting board, no hands (unless specified)
7. **Style**: Professional food ASMR, cinematic lighting

## Processing Instructions

1. **Parse Input**: Extract objects from {USER_INPUT}
2. **Expand Categories**: If category detected, expand to 5-10 specific objects
3. **Generate Shots**: Create one shot per object using BOTH image_prompt and motion_prompt
4. **Image Prompt**: Generate static shot of complete object with HORIZONTAL knife above (before cutting, blade parallel to board)
5. **Motion Prompt**: Generate video action of cutting through the object
6. **Calculate Duration**: total_duration = number_of_shots × shot_duration (default 5)
7. **Return JSON**: Valid JSON with correct schema

{USER_INPUT}
