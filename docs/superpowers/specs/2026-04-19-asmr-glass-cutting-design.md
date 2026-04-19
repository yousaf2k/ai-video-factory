# ASMR Glass Cutting Project Type - Design Spec

**Date:** 2026-04-19
**Status:** Design Approved - Awaiting Implementation
**Priority:** High
**Review Status:** Spec approved by reviewer with minor recommendations

## Overview

Add a new `ASMR_GLASS_CUTTING` project type that generates ASMR-style videos of glass sculpture fruits/vegetables being cut. Unlike standard projects that use separate story and shots agents, this follows the `THEN_VS_NOW` pattern where the story agent generates all shots directly in a single LLM call.

## Requirements

### Functional Requirements
- Support natural language input (e.g., "create videos of strawberry, apple, and tomato")
- Handle both specific objects and category expansion (e.g., "red fruits" → 5-10 specific fruits)
- Generate 5-10 shots from general categories
- Strictly follow glass sculpture prompt style from provided examples
- Fixed duration per shot (default 5 seconds)
- No scene structure, no narration (pure ASMR focus)

### Non-Functional Requirements
- Single LLM call for efficiency (no per-object LLM calls)
- Follow existing `THEN_VS_NOW` pattern for minimal code changes
- Compatible with existing image/video generation pipeline
- Maintain existing CLI and Web UI interfaces

## Architecture

### Components

#### 1. Project Type Enum
**File:** `web_ui/backend/models/story.py`

```python
class ProjectType(str, Enum):
    # ... existing types
    ASMR_GLASS_CUTTING = "asmr_glass_cutting"
```

#### 2. Story Engine Function
**File:** `core/story_engine.py`

```python
def build_story_asmr_glass_cutting(
    idea: str,
    agent_name: str = "asmr/asmr_glass_cutting",
    shot_duration: int = 5,
    aspect_ratio: str = "16:9"
) -> str:
    """
    Build ASMR glass cutting story from natural language input.

    Args:
        idea: Natural language description (e.g., "create videos of strawberry, apple, and tomato")
        agent_name: Story agent to use
        shot_duration: Fixed duration for each shot in seconds
        aspect_ratio: Video aspect ratio

    Returns:
        JSON string with story structure including shots
    """
```

**Key behaviors:**
- No comma splitting - let LLM parse natural language completely
- Validate LLM returned objects
- Calculate total_duration = shot_count × shot_duration
- Return standard story JSON format

#### 3. Story Agent
**File:** `agents/story/asmr/asmr_glass_cutting.md`

**Structure:**
- System prompt with 6 glass sculpture example prompts
- Instructions for extracting objects from natural language
- Category expansion logic (5-10 objects for general categories)
- JSON schema definition

**Output JSON Schema:**
```json
{
  "title": "ASMR Glass Cutting - [Category/Objects]",
  "project_type": "asmr_glass_cutting",
  "user_input": "original user input",
  "expanded_objects": ["object1", "object2", ...],
  "total_duration": 45,
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

### Data Flow

```
User Input (Natural Language)
    ↓
build_story_asmr_glass_cutting(idea)
    ↓
load_agent_prompt("asmr/asmr_glass_cutting", idea)
    ↓
LLM Single Call (extracts objects + generates prompts)
    ↓
JSON Response with expanded_objects + shots array
    ↓
Validate (objects exist, shots generated)
    ↓
Return JSON story structure
    ↓
Standard Pipeline (image/video generation)
```

**Input Examples:**
- "create videos of strawberry, apple, and tomato" → 3 specific objects
- "make ASMR videos for tropical fruits" → 5-10 expanded objects
- "generate for red fruits" → 5-10 expanded objects

### Pipeline Integration

**CLI Usage:**
```bash
python core/main.py \
  --idea "create videos of strawberry, apple, and tomato" \
  --story-agent asmr/asmr_glass_cutting \
  --project-type asmr_glass_cutting \
  --shot-duration 5
```

**Main Pipeline Changes:**
In `core/main.py`, add routing:
```python
if project_type == ProjectType.ASMR_GLASS_CUTTING:
    story_json = build_story_asmr_glass_cutting(
        idea=args.idea,
        shot_duration=args.shot_duration,
        aspect_ratio=args.aspect_ratio
    )
    # Skip build_scene_graph() and plan_shots()
    # Shots already in story_json
```

## Prompt Style Guidelines

### Glass Sculpture Characteristics
- **Material:** Glass sculptures with realistic internal structures
- **Visuals:** Reflective, slightly tinted, sparkling internal highlights
- **Lighting:** Cinematic, shallow depth of field, macro close-up
- **Audio:** ASMR-style (glass clinks, crisp cutting sounds)
- **Action:** 3-4 clean cuts per object, pieces separate or fall off
- **Setting:** Wooden cutting board, no background distractions

### Camera Specifications
- **Angle:** Close-up macro, consistent with examples
- **Depth of Field:** Shallow (blurred background)
- **Resolution:** Ultra 8K or 4K
- **Frame:** Professional food ASMR style

### Example Prompts (Include in Agent)
1. Strawberry with embedded golden seeds
2. Red apple with glass texture
3. Green starfruit with black gloves
4. Tomato with glass shell cracking
5. Broccoli showing internal glass structure
6. Kiwi with glass shell over fuzzy skin

## Error Handling

### Input Validation
```python
if not idea or len(idea.strip()) < 3:
    raise ValueError("Please describe the fruits or vegetables to create videos for")
```

### LLM Response Validation
```python
story = json.loads(story_json)

if not story.get("expanded_objects") or len(story["expanded_objects"]) == 0:
    raise ValueError(
        "Could not identify objects from input. "
        "Please specify fruits or vegetables more clearly."
    )

if len(story["shots"]) == 0:
    raise ValueError("No shots generated. Try a different description.")

if len(story["shots"]) < 3:
    logger.warning(f"Only {len(story['shots'])} shots generated. Expected at least 3.")
```

### Agent Prompt Safeguards
- Include clear instructions for object extraction
- Provide fallback to common objects if ambiguous
- Require minimum 3 objects, maximum 10 objects

## Testing Strategy

### Unit Tests
**File:** `tests/test_asmr_engine.py`

```python
def test_build_story_asmr_specific_objects():
    """Test with specific objects in natural language"""
    story = build_story_asmr_glass_cutting(
        "create videos of strawberry and apple"
    )
    data = json.loads(story)
    assert len(data["shots"]) >= 2
    assert any("strawberry" in s["object_name"] for s in data["shots"])
    assert any("apple" in s["object_name"] for s in data["shots"])

def test_build_story_asmr_category_expansion():
    """Test with category expansion"""
    story = build_story_asmr_glass_cutting("red fruits")
    data = json.loads(story)
    assert 5 <= len(data["shots"]) <= 10
    assert all(s["duration"] == 5 for s in data["shots"])

def test_build_story_asmr_duration_calculation():
    """Test total duration calculation"""
    story = build_story_asmr_glass_cutting("banana and orange", shot_duration=5)
    data = json.loads(story)
    expected_duration = len(data["shots"]) * 5
    assert data["total_duration"] == expected_duration

def test_build_story_asmr_invalid_input():
    """Test error handling for invalid input"""
    with pytest.raises(ValueError):
        build_story_asmr_glass_cutting("")
```

### Integration Tests
```python
def test_full_pipeline_asmr():
    """Test complete ASMR pipeline"""
    # Generate story
    story_json = build_story_asmr_glass_cutting("create strawberry video")
    story = json.loads(story_json)

    # Verify structure
    assert "shots" in story
    assert len(story["shots"]) > 0

    # Test compatibility with image generator
    for shot in story["shots"]:
        assert "prompt" in shot
        assert len(shot["prompt"]) > 50  # Detailed prompt
```

### Manual Testing
```bash
# Test specific objects
python core/main.py --idea "create videos of strawberry, apple, and tomato" \
  --story-agent asmr/asmr_glass_cutting --test-mode

# Test category expansion
python core/main.py --idea "tropical fruits" \
  --story-agent asmr/asmr_glass_cutting --test-mode

# Test duration calculation
python core/main.py --idea "banana and orange" \
  --story-agent asmr/asmr_glass_cutting --shot-duration 8 --test-mode
```

## Implementation Checklist

### Core Files
- [ ] Add `ASMR_GLASS_CUTTING` to `ProjectType` enum
- [ ] Create `build_story_asmr_glass_cutting()` in `story_engine.py`
- [ ] Create agent file `agents/story/asmr/asmr_glass_cutting.md`
- [ ] Add CLI routing in `core/main.py`
- [ ] Add API support in `web_ui/backend/api/projects.py`

### Agent Development
- [ ] Write system prompt with 6 example prompts
- [ ] Define JSON output schema
- [ ] Add object extraction instructions
- [ ] Add category expansion logic
- [ ] Test prompt with various inputs

### Testing
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Manual testing with various inputs
- [ ] Verify Web UI integration

### Documentation
- [ ] Update CLAUDE.md with new project type
- [ ] Add usage examples to docs
- [ ] Update API documentation

## Success Criteria

✅ User can provide natural language input
✅ Agent extracts objects or expands categories
✅ 5-10 shots generated for categories
✅ Fixed duration per shot (configurable)
✅ Glass sculpture style strictly followed
✅ Compatible with existing pipeline
✅ Single LLM call (efficient)
✅ CLI and Web UI both work

## Future Enhancements

- Custom duration per object type
- Camera style variations (user-selectable)
- Background music options
- Multi-object sequences (one shot with multiple objects)
- Custom material styles (crystal, ice, metal)
- Batch processing for large object lists
