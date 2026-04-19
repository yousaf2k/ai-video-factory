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

### Action Description
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
"Highly realistic ultra 8K ASMR video, close-up macro shot of precision cutting through a strawberry glass sculpture. The glass sculpture has a strawberry shape with embedded golden seeds visible through the crystal clear glass. The sculpture features realistic strawberry texture with slight red tint and reflective surface. A sharp knife makes 3-4 clean precise cuts through the glass strawberry. As the knife cuts, you see satisfying crack propagation through the glass. The pieces separate or fall off the main sculpture with realistic physics. Light catches on the glass surfaces creating rainbow prisms and sparkling highlights. The strawberry has detailed internal glass structure visible through the cuts. Shallow depth of field with blurred wooden cutting board in background. No people or hands visible, just the knife and glass sculpture. Professional food ASMR style, cinematic lighting."

### Example 2: Red Apple
"Ultra 8K ASMR video, macro close-up of a red apple glass sculpture being cut with precision. The glass apple has realistic apple shape with embedded lighter-colored glass core and seed details visible through transparent material. Slight red tint with sparkling internal highlights. Sharp knife makes 3-4 clean cuts through the glass apple. Satisfying crack propagation visible as the knife cuts through. Glass pieces separate and fall with realistic physics. Light refracts through glass creating rainbow prisms. Detailed internal glass structure of the apple visible. Shallow DOF, blurred wooden cutting board background. Cinematic lighting, no hands visible. Professional ASMR quality."

### Example 3: Green Starfruit
"Highly realistic 8K ASMR video, extreme close-up of precision cutting through a starfruit glass sculpture. The glass starfruit has distinctive star shape with green-tinted translucent glass. Embedded internal structure visible through crystal clear material. Person wearing black gloves (gloves visible) holds a sharp knife making 3-4 precise cuts through the glass starfruit. Satisfying crack propagation as glass separates. Starfruit pieces fall apart with realistic physics. Rainbow prisms and light refraction through glass pieces. Detailed star pattern visible in cross-section. Shallow depth of field, blurred background. Professional ASMR style, cinematic lighting."

### Example 4: Tomato
"Ultra 8K ASMR macro video, precision cutting of a tomato glass sculpture. Realistic tomato-shaped glass sculpture with deep red tint and visible internal lighter-colored glass seed chambers. The glass has a slight shell-like texture. Sharp knife makes 3-4 clean cuts through the glass tomato. Satisfying cracking sounds as glass separates with visible crack propagation. Tomato pieces fall or separate with realistic physics. Light catches on glass surfaces creating sparkling highlights and rainbow refraction. Detailed internal glass structure visible through cuts. Shallow DOF, blurred wooden background. No hands visible. Professional food ASMR quality."

### Example 5: Broccoli
"Highly realistic 8K ASMR video, close-up macro shot of precision cutting through a broccoli glass sculpture. The glass broccoli has detailed floret structure with green-tinted translucent glass. Visible internal glass structure showing realistic broccoli texture. Sharp knife makes 3-4 precise cuts through the glass broccoli. Satisfying crack propagation visible through the glass. Pieces separate with realistic physics. Light refraction creates rainbow prisms through glass pieces. Detailed internal structure of broccoli florets visible. Shallow depth of field, blurred background. Professional ASMR style, cinematic lighting."

### Example 6: Kiwi
"Ultra 8K ASMR video, macro close-up of precision cutting through a kiwi glass sculpture. The glass kiwi has fuzzy brown outer glass shell with visible internal green glass flesh and black seed details. The fuzzy texture shows through light refraction. Sharp knife makes 3-4 clean cuts through the glass kiwi. Satisfying cracking as glass separates with visible crack propagation. Kiwi pieces fall with realistic physics. Light catches on glass creating rainbow prisms and sparkling highlights. Detailed internal structure with seeds visible. Shallow DOF, blurred wooden cutting board background. Professional food ASMR quality."

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
      "prompt": "Highly realistic ultra 8K ASMR video...",
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
- `prompt`: Detailed prompt following the example style (100+ words)
- `duration`: Fixed duration per shot (default 5 seconds)
- `camera`: "closeup_macro" for all shots
- `motion_strength`: "medium" for all shots
- `shot_type`: "asmr_glass_cutting" for all shots

## Important Rules

1. **expanded_objects Format**: MUST be simple string array, NOT array of objects
2. **One Shot Per Object**: Each object in expanded_objects gets exactly one shot
3. **Prompt Detail**: Each prompt must be 100+ words following the example style
4. **Fixed Duration**: All shots use same duration (default 5 seconds)
5. **Camera**: Always "closeup_macro"
6. **Natural Language Parsing**: Correctly extract objects from sentences like "create for the fruits strawberry, banana, orange"
7. **Category Expansion**: For categories, generate 5-10 specific objects
8. **Project Type**: Must be "asmr_glass_cutting"

## Shot Prompt Template

For each object, generate prompts following this structure:

1. **Opening**: "Highly realistic ultra 8K ASMR video, close-up macro shot of..."
2. **Object Description**: Glass sculpture details (shape, color, texture, internal structure)
3. **Action**: Sharp knife making 3-4 clean cuts through the glass [object]
4. **Visual Effects**: Crack propagation, pieces separating/falling, light refraction, rainbow prisms
5. **Internal Details**: Visible internal glass structure through cuts
6. **Camera/Background**: Shallow DOF, blurred wooden cutting board, no hands (unless specified)
7. **Style**: Professional food ASMR, cinematic lighting

## Processing Instructions

1. **Parse Input**: Extract objects from {USER_INPUT}
2. **Expand Categories**: If category detected, expand to 5-10 specific objects
3. **Generate Shots**: Create one shot per object using detailed prompts
4. **Calculate Duration**: total_duration = number_of_shots × shot_duration (default 5)
5. **Return JSON**: Valid JSON with correct schema

{USER_INPUT}
