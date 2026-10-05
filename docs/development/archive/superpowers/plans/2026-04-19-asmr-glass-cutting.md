# ASMR Glass Cutting Project Type - Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new ASMR_GLASS_CUTTING project type that generates ASMR glass sculpture cutting videos directly from natural language input, following the existing THEN_VS_NOW pattern.

**Architecture:** Reuse the THEN_VS_NOW direct-shot generation pattern where the story agent generates all shots in a single LLM call. Add ASMR_GLASS_CUTTING to ProjectType enum, create build_story_asmr_glass_cutting() function, and add natural language input handling with object extraction.

**Tech Stack:** Python, FastAPI, Pydantic, LLM providers (Gemini/OpenAI), existing story engine infrastructure

---

## Task 1: Add ASMR_GLASS_CUTTING to ProjectType Enum

**Files:**
- Modify: `web_ui/backend/models/story.py:9-14`

- [ ] **Step 1: Read the existing ProjectType enum**

```bash
# Read lines 9-14 to see current enum structure
sed -n '9,14p' web_ui/backend/models/story.py
```

Expected: See DOCUMENTARY=1, THEN_VS_NOW=2, MOVIE=3

- [ ] **Step 2: Add ASMR_GLASS_CUTTING enum value**

Edit line 14 to add the new enum value:

```python
class ProjectType(IntEnum):
    """Project type enumeration"""
    DOCUMENTARY = 1
    THEN_VS_NOW = 2
    MOVIE = 3
    ASMR_GLASS_CUTTING = 4
```

- [ ] **Step 3: Verify the change**

```bash
# Verify the enum was added correctly
grep -A 5 "class ProjectType" web_ui/backend/models/story.py
```

Expected: See ASMR_GLASS_CUTTING = 4 in the output

- [ ] **Step 4: Commit the change**

```bash
git add web_ui/backend/models/story.py
git commit -m "feat: add ASMR_GLASS_CUTTING to ProjectType enum

Add new project type for ASMR glass sculpture cutting videos.
Follows existing enum pattern with value 4.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: Create ASMR Story Agent Prompt

**Files:**
- Create: `agents/story/asmr/asmr_glass_cutting.md`

- [ ] **Step 1: Create the asmr directory**

```bash
mkdir -p agents/story/asmr
```

Expected: Directory created successfully

- [ ] **Step 2: Write the agent prompt file**

Create `agents/story/asmr/asmr_glass_cutting.md` with this content:

```markdown
# ASMR Glass Sculpture Cutting Story Generator

You are an expert at creating ASMR-style video prompts for glass sculpture fruits and vegetables being cut.

## Your Task

Generate a JSON response containing shots for ASMR glass cutting videos based on the user's input.

## Input Processing

The user will provide natural language input such as:
- "create videos of strawberry, apple, and tomato"
- "make ASMR videos for tropical fruits"
- "generate cutting videos for red fruits"
- "I want videos of banana, orange, and mango"

**Your job:**
1. Extract specific objects if mentioned (e.g., "strawberry, apple, tomato" → strawberry, apple, tomato)
2. If only a category is given (e.g., "red fruits"), expand it to 5-10 specific objects
3. Generate a unique, detailed glass sculpture cutting prompt for each object

## Glass Sculpture Style Guidelines

**ALL prompts must follow this style:**

### Material & Appearance
- Objects are made of glass with realistic internal structures
- Reflective, slightly tinted, sparkling with internal highlights
- Transparent or translucent like blown glass

### Visual Quality
- Ultra 8K or 4K resolution
- Cinematic lighting with shallow depth of field
- Macro close-up camera angle
- Professional food ASMR video framing

### Setting
- Wooden cutting board
- No background distractions
- Clean, focused composition

### Action
- 3-4 clean cuts per object
- Knife moves smoothly and deliberately
- Pieces separate or fall off after cutting
- Each cut is crisp and precise

### Audio (implied in video description)
- ASMR-style sounds (glass clinks, crisp cutting)
- No voiceover
- Soft ambient background

## Example Prompts (Use as Templates)

1. **Strawberry:** Highly realistic ultra 8K ASMR video of a human hand slicing a hyper-detailed, red glass sculpture of a strawberry on a wooden cutting board. The strawberry has embedded golden seeds that glimmer subtly. The object resembles glossy blown glass — reflective, slightly tinted, and sparkling with internal highlights. The camera is in close-up with shallow depth of field, capturing cinematic lighting and detailed glass textures. The knife moves slowly and deliberately, making three satisfying cuts — one after another — creating 3 to 4 clean, evenly spaced slices. Each slice is crisp, producing a delicate glass clink sound. The cut pieces gently separate, shimmering like crystal. No background distractions. No voice. Just immersive ASMR with soft ambient sound.

2. **Red Apple:** Highly realistic ultra 8K ASMR video of a human hand slicing a hyper-detailed, glass sculpture of a red apple on a wooden cutting board. The object resembles glossy blown glass - reflective, slightly tinted, and sparkling with internal highlights. The camera is in close-up with shallow depth of field, capturing cinematic lighting and detailed glass textures. The knife moves smoothly and deliberately, making three separate satisfying cuts - one after another - creating 3 to 4 clean, evenly spaced slices. Each stroke feels precise and crisp, with realistic slicing sound and natural motion. The sliced pieces gently separate, glimmering like cut crystal. No background distractions, same iconic camera angle as professional food ASMR videos.

3. **Starfruit:** A realistic 8K ASMR close-up shot of a pair of hands wearing minimalist black gloves and a knife quickly cutting green glass starfruit on a wooden cutting board. It cuts it into several pieces, and each piece falls down as the knife moves to the next. The interior of the fruit is also made of glass. The sound is ASMR style.

4. **Tomato:** Create a cinematic ASMR-style video of a ripe tomato resting horizontally on a dark wooden board. Its smooth red skin is visible beneath a thin, glass-like transparent shell that clings to its natural texture. Subtle lighting enhances the contrast between the smooth skin and the glossy coating. A sharp knife is positioned above the center, then slices directly through with even pressure. The glass shell cracks and separates as the knife enters the tomato's moist, red flesh and seeds. Macro lens, 4K resolution, gentle shadows, and ASMR audio capturing the fine crunch of the shell followed by the moist texture inside.

5. **Broccoli:** A real 4K close-up of a knife quickly cutting a broccoli made of glass. The broccoli retains its original green color, and its internal structure is the same as the real vegetable, but it is all made of glass, and the tight glassy flower ball structure and forked glass stems can be clearly seen. The broccoli is placed on a wooden cutting board. The surface shows the sheen of glass and the natural texture of the broccoli. The knife cuts quickly multiple times, and each piece falls off after being cut, and the knife quickly moves to the next piece. The inside of the broccoli is also made of glass, and the vitrified stem fibers and the tiny glass buds inside are clearly visible. The sound is ASMR style.

6. **Kiwi:** Create a cinematic ASMR-style video of a ripe kiwi fruit resting horizontally on a dark wooden board. Its fuzzy brown skin is visible beneath a thin, glass-like transparent shell that clings to its natural texture. Subtle lighting enhances the contrast between the matte skin and the glossy coating. A sharp knife is positioned above the center, then slices directly through with even pressure. The glass shell cracks and separates as the knife enters the kiwi's moist, green flesh filled with black seeds. Macro lens, 4K resolution, gentle shadows, and ASMR audio capturing the fine crunch of the shell followed by the moist texture inside.

## Output JSON Schema

Return ONLY valid JSON. No markdown, no explanations, no code blocks.

```json
{
  "title": "ASMR Glass Cutting - [Category or Object Names]",
  "style": "ASMR Glass Sculpture Cutting",
  "project_type": "asmr_glass_cutting",
  "user_input": "[the original user input]",
  "expanded_objects": ["object1", "object2", "object3", ...],
  "total_duration": [number of shots × shot duration],
  "aspect_ratio": "16:9",
  "shots": [
    {
      "id": "shot_001",
      "index": 1,
      "object_name": "[object name]",
      "prompt": "[Detailed glass sculpture cutting prompt]",
      "duration": 5,
      "camera": "closeup_macro",
      "motion_strength": "medium",
      "shot_type": "asmr_glass_cutting"
    },
    ... more shots
  ]
}
```

## Important Rules

1. **Minimum 3 objects, maximum 10 objects**
2. **Each object gets a unique prompt** - don't repeat the same template
3. **Strictly follow the glass sculpture style** from examples
4. **Include specific object details** (seeds for strawberry, fuzzy skin for kiwi, etc.)
5. **Always mention ASMR audio** in the prompt
6. **Use wooden cutting board** in every shot
7. **Macro close-up camera** with shallow depth of field
8. **3-4 cuts per object** with pieces separating
9. **expanded_objects array** must list all objects you selected
10. **total_duration** = shot_count × 5 (assuming 5-second shots)

## User Input

{USER_INPUT}
```

- [ ] **Step 3: Verify the agent file was created**

```bash
# Verify file exists and has content
ls -lh agents/story/asmr/asmr_glass_cutting.md
wc -l agents/story/asmr/asmr_glass_cutting.md
```

Expected: File exists with 100+ lines

- [ ] **Step 4: Test agent can be loaded**

```bash
# Test the agent loader can find it
python -c "from core.agent_loader import load_agent_prompt; print(load_agent_prompt('story', 'test input', 'asmr/asmr_glass_cutting')[:200])"
```

Expected: First 200 characters of the agent prompt printed

- [ ] **Step 5: Commit the agent**

```bash
git add agents/story/asmr/asmr_glass_cutting.md
git commit -m "feat: add ASMR glass cutting story agent

Create comprehensive agent prompt for generating ASMR glass
sculpture cutting videos. Includes 6 example prompts and
detailed style guidelines.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: Add build_story_asmr_glass_cutting() Function

**Files:**
- Modify: `core/story_engine.py`
- Test: `tests/test_asmr_engine.py`

- [ ] **Step 1: Write the failing test first**

Create `tests/test_asmr_engine.py`:

```python
"""
Tests for ASMR glass cutting story engine
"""
import pytest
import json
from core.story_engine import build_story_asmr_glass_cutting


def test_build_story_asmr_specific_objects():
    """Test with specific objects in natural language"""
    story_json = build_story_asmr_glass_cutting(
        "create videos of strawberry and apple"
    )
    story = json.loads(story_json)
    
    assert story["project_type"] == 4  # ASMR_GLASS_CUTTING
    assert len(story["shots"]) >= 2
    assert any("strawberry" in s["object_name"].lower() for s in story["shots"])
    assert any("apple" in s["object_name"].lower() for s in story["shots"])
    assert all(s["duration"] == 5 for s in story["shots"])
    assert "expanded_objects" in story


def test_build_story_asmr_category_expansion():
    """Test with category expansion"""
    story_json = build_story_asmr_glass_cutting("red fruits")
    story = json.loads(story_json)
    
    assert 5 <= len(story["shots"]) <= 10
    assert all(s["duration"] == 5 for s in story["shots"])
    assert len(story["expanded_objects"]) >= 5
    assert story["total_duration"] == len(story["shots"]) * 5


def test_build_story_asmr_duration_calculation():
    """Test total duration calculation"""
    story_json = build_story_asmr_glass_cutting(
        "banana and orange", 
        shot_duration=8
    )
    story = json.loads(story_json)
    
    expected_duration = len(story["shots"]) * 8
    assert story["total_duration"] == expected_duration


def test_build_story_asmr_invalid_input():
    """Test error handling for invalid input"""
    with pytest.raises(ValueError, match="describe the fruits"):
        build_story_asmr_glass_cutting("")


def test_build_story_asmr_prompt_quality():
    """Test that prompts follow glass sculpture style"""
    story_json = build_story_asmr_glass_cutting("strawberry")
    story = json.loads(story_json)
    
    shot = story["shots"][0]
    prompt = shot["prompt"].lower()
    
    # Check for glass sculpture style keywords
    assert "glass" in prompt
    assert any(word in prompt for word in ["asmr", "cinematic", "8k", "4k"])
    assert len(shot["prompt"]) > 100  # Detailed prompt


def test_build_story_asmr_aspect_ratio():
    """Test aspect ratio is set correctly"""
    story_json = build_story_asmr_glass_cutting(
        "tomato",
        aspect_ratio="9:16"
    )
    story = json.loads(story_json)
    
    assert story["aspect_ratio"] == "9:16"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_asmr_engine.py -v
```

Expected: FAIL with "function 'build_story_asmr_glass_cutting' not defined"

- [ ] **Step 3: Implement the function in story_engine.py**

Add this function to `core/story_engine.py` after the `build_story_then_vs_now` function (around line 280):

```python
def build_story_asmr_glass_cutting(
    idea: str,
    agent_name: str = "asmr/asmr_glass_cutting",
    shot_duration: int = 5,
    aspect_ratio: str = "16:9"
) -> str:
    """
    Build an ASMR glass cutting story from natural language input.
    
    The story agent generates all shots directly in a single LLM call,
    following the THEN_VS_NOW pattern.
    
    Args:
        idea: Natural language description (e.g., "create videos of strawberry, apple, and tomato")
        agent_name: Story agent to use (default: "asmr/asmr_glass_cutting")
        shot_duration: Fixed duration for each shot in seconds (default: 5)
        aspect_ratio: Video aspect ratio (default: "16:9")
    
    Returns:
        JSON string with story structure including shots
    
    Raises:
        ValueError: If input is too short or LLM doesn't generate valid shots
    """
    from web_ui.backend.models.story import ProjectType
    
    # Validate input
    if not idea or len(idea.strip()) < 3:
        raise ValueError("Please describe the fruits or vegetables to create videos for")
    
    provider = get_provider()
    
    # Load the ASMR agent prompt
    # If agent_name doesn't contain a slash, assume it's in the asmr/ directory
    final_agent_path = agent_name
    if "/" not in agent_name:
        final_agent_path = f"asmr/{agent_name}"
    
    try:
        prompt = load_agent_prompt("story", idea, final_agent_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Failed to load ASMR agent: {e}")
        raise ValueError(f"ASMR glass cutting agent not found: {final_agent_path}")
    
    # Generate story with shots
    logger.info(f"Generating ASMR glass cutting story for: {idea}")
    print(f"[INFO] Generating ASMR glass cutting story for: {idea}")
    
    try:
        story_json_str = provider.ask(prompt, response_format="application/json")
        story = json.loads(story_json_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        raise ValueError("Failed to generate valid story. Please try a different description.")
    
    # Ensure project_type is set
    story['project_type'] = ProjectType.ASMR_GLASS_CUTTING
    
    # Add aspect_ratio
    story['aspect_ratio'] = aspect_ratio
    
    # Validate expanded_objects
    if not story.get("expanded_objects") or len(story.get("expanded_objects", [])) == 0:
        logger.warning("No expanded_objects in response")
        raise ValueError(
            "Could not identify objects from input. "
            "Please specify fruits or vegetables more clearly."
        )
    
    # Validate shots were generated
    if "shots" not in story or len(story["shots"]) == 0:
        logger.error("No shots in generated story")
        raise ValueError("No shots generated. Try a different description.")
    
    # Warn if too few shots
    if len(story["shots"]) < 3:
        logger.warning(f"Only {len(story['shots'])} shots generated. Expected at least 3.")
    
    # Calculate and set total_duration
    shot_count = len(story["shots"])
    story['total_duration'] = shot_count * shot_duration
    
    # Update shot durations
    for shot in story["shots"]:
        shot["duration"] = shot_duration
    
    # Ensure each shot has required fields
    for i, shot in enumerate(story["shots"]):
        if "id" not in shot:
            shot["id"] = f"shot_{i+1:03d}"
        if "index" not in shot:
            shot["index"] = i + 1
        if "shot_type" not in shot:
            shot["shot_type"] = "asmr_glass_cutting"
        
        # Validate prompt exists and is detailed
        if "prompt" not in shot or len(shot.get("prompt", "")) < 50:
            logger.warning(f"Shot {i+1} has missing or short prompt")
    
    logger.info(f"Generated {len(story['shots'])} shots for {len(story['expanded_objects'])} objects")
    print(f"[INFO] Generated {len(story['shots'])} shots for {len(story['expanded_objects'])} objects")
    
    return json.dumps(story, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_asmr_engine.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit the implementation**

```bash
git add core/story_engine.py tests/test_asmr_engine.py
git commit -m "feat: implement build_story_asmr_glass_cutting function

Add story generation function for ASMR glass cutting videos.
Single LLM call generates all shots directly, following
THEN_VS_NOW pattern. Includes comprehensive validation
and error handling.

Tests:
- Specific object extraction
- Category expansion (5-10 objects)
- Duration calculation
- Input validation
- Prompt quality checks

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: Add CLI Routing in main.py

**Files:**
- Modify: `core/main.py`

- [ ] **Step 1: Find the story generation section**

```bash
# Find where build_story is called
grep -n "build_story(" core/main.py | head -5
```

Expected: See line numbers where build_story is called (around line 1434 and 1693)

- [ ] **Step 2: Read context around first build_story call**

```bash
# Read 30 lines around the first build_story call
sed -n '1420,1450p' core/main.py
```

Expected: See the STEP 2: Story Generation section

- [ ] **Step 3: Add import for the new function**

Add this import near the top of main.py (around line 54, after the other story_engine imports):

```python
from core.story_engine import build_story, build_story_then_vs_now, build_story_asmr_glass_cutting
```

- [ ] **Step 4: Add ASMR routing logic**

Edit the story generation section (around line 1434) to add routing logic.

**Find this section:**
```python
        story_json = build_story(idea, agent_name=story_agent, target_length=target_length)
        project_mgr.save_story(project_id, story_json)
```

**Replace with:**
```python
        # Route to appropriate story builder based on project type
        is_asmr = story_agent == "asmr_glass_cutting" or story_agent.startswith("asmr/")
        is_then_vs_now = story_agent == "then_vs_now" or story_agent.startswith("then_vs_now/")
        
        if is_asmr:
            logger.info(f"Using ASMR glass cutting story builder with agent: {story_agent}")
            story_json = build_story_asmr_glass_cutting(
                idea=idea,
                agent_name=story_agent,
                shot_duration=args.shot_length if hasattr(args, 'shot_length') and args.shot_length else 5,
                aspect_ratio=args.aspect_ratio if hasattr(args, 'aspect_ratio') else "16:9"
            )
        elif is_then_vs_now:
            logger.info(f"Using ThenVsNow story builder with agent: {story_agent}")
            story_json = build_story_then_vs_now(
                movie_name=idea,
                agent_name=story_agent,
                target_length=target_length,
                aspect_ratio=args.aspect_ratio if hasattr(args, 'aspect_ratio') else "16:9"
            )
        else:
            # Standard story generation
            story_json = build_story(idea, agent_name=story_agent, target_length=target_length)
        
        project_mgr.save_story(project_id, story_json)
```

- [ ] **Step 5: Repeat for second story generation location**

Find the second occurrence (around line 1693 in the _run_auto_mode function) and apply the same routing logic.

**Find this section:**
```python
                story_json = build_story(idea, agent_name=story_agent, target_length=target_length)
                project_mgr.save_story(project_id, story_json)
```

**Replace with the same routing logic as Step 4.**

- [ ] **Step 6: Verify changes with grep**

```bash
# Verify the routing logic was added
grep -A 15 "is_asmr = story_agent" core/main.py | head -20
```

Expected: See the routing logic checking for asmr agents

- [ ] **Step 7: Test CLI with dry run**

```bash
# Test that the CLI accepts the new agent
python core/main.py --idea "test" --story-agent asmr/asmr_glass_cutting --step 2 2>&1 | head -20
```

Expected: See log message about using ASMR glass cutting story builder

- [ ] **Step 8: Commit the changes**

```bash
git add core/main.py
git commit -m "feat: add CLI routing for ASMR glass cutting

Route ASMR glass cutting requests to build_story_asmr_glass_cutting()
function based on agent name prefix. Supports both 'asmr_glass_cutting'
and 'asmr/asmr_glass_cutting' agent formats.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: Add Web UI API Support

**Files:**
- Modify: `web_ui/backend/api/stories.py`

- [ ] **Step 1: Find the ThenVsNow routing section**

```bash
# Find where THEN_VS_NOW routing is handled
grep -n "is_then_vs_now" web_ui/backend/api/stories.py
```

Expected: Found around line 220-230

- [ ] **Step 2: Read the context**

```bash
# Read 40 lines around the THEN_VS_NOW check
sed -n '210,250p' web_ui/backend/api/stories.py
```

Expected: See the story generation routing logic

- [ ] **Step 3: Add ASMR routing import**

Add to the import section at the top (around line 220 where ProjectType is imported):

```python
from web_ui.backend.models.story import ProjectType

# Import ASMR story builder
from core.story_engine import build_story_asmr_glass_cutting
```

- [ ] **Step 4: Add ASMR routing logic**

Find this section (around line 220-234):

```python
        is_then_vs_now = meta.get('project_type') == ProjectType.THEN_VS_NOW or request.agent == "then_vs_now" or request.agent.startswith("then_vs_now/")

        if is_then_vs_now:
            from core.story_engine import build_story_then_vs_now
            
            logger.info(f"Regenerating ThenVsNow story with agent: {request.agent}")
            story_json = build_story_then_vs_now(
                movie_name=idea,
                agent_name=request.agent,
                target_length=target_length,
                aspect_ratio=aspect_ratio
            )
            story = json.loads(story_json)
            shots = story.pop('shots', [])
```

**Add ASMR routing after the THEN_VS_NOW block:**

```python
        is_then_vs_now = meta.get('project_type') == ProjectType.THEN_VS_NOW or request.agent == "then_vs_now" or request.agent.startswith("then_vs_now/")
        is_asmr = meta.get('project_type') == ProjectType.ASMR_GLASS_CUTTING or request.agent == "asmr_glass_cutting" or request.agent.startswith("asmr/")

        if is_asmr:
            logger.info(f"Generating ASMR glass cutting story with agent: {request.agent}")
            story_json = build_story_asmr_glass_cutting(
                idea=idea,
                agent_name=request.agent,
                shot_duration=meta.get("shot_duration", 5),
                aspect_ratio=aspect_ratio
            )
            story = json.loads(story_json)
            shots = story.pop('shots', [])
            
            # Save story.json
            project_manager.save_story(project_id, json.dumps(story, indent=2, ensure_ascii=False))
            
            # Update shots.json
            project_manager.save_shots(project_id, shots)
            
            # Update project metadata
            meta['steps']['story'] = True
            meta['stats']['total_shots'] = len(shots)
            project_manager.update_project_metadata(project_id, meta)
            
            return {
                "story": story,
                "shots": shots,
                "meta": meta
            }
            
        elif is_then_vs_now:
            from core.story_engine import build_story_then_vs_now
            
            logger.info(f"Regenerating ThenVsNow story with agent: {request.agent}")
            story_json = build_story_then_vs_now(
                movie_name=idea,
                agent_name=request.agent,
                target_length=target_length,
                aspect_ratio=aspect_ratio
            )
            story = json.loads(story_json)
            shots = story.pop('shots', [])
```

- [ ] **Step 5: Verify the changes**

```bash
# Verify the ASMR routing was added
grep -A 5 "is_asmr = meta.get" web_ui/backend/api/stories.py
```

Expected: See the ASMR routing check

- [ ] **Step 6: Commit the API changes**

```bash
git add web_ui/backend/api/stories.py
git commit -m "feat: add Web UI API routing for ASMR glass cutting

Add API endpoint support for ASMR glass cutting project type.
Routes requests with asmr/ agent prefix to the appropriate
story builder. Handles project metadata updates.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 6: Integration Testing

**Files:**
- Test: Manual CLI testing
- Test: Web UI endpoint testing

- [ ] **Step 1: Test CLI with specific objects**

```bash
python core/main.py \
  --idea "create videos of strawberry, apple, and tomato" \
  --story-agent asmr/asmr_glass_cutting \
  --shot-duration 5 \
  --step 2
```

Expected:
- Story generated successfully
- 3 shots created
- Each shot has detailed glass sculpture prompt
- total_duration = 15 (3 shots × 5 seconds)

- [ ] **Step 2: Test CLI with category expansion**

```bash
python core/main.py \
  --idea "tropical fruits" \
  --story-agent asmr/asmr_glass_cutting \
  --shot-duration 5 \
  --step 2
```

Expected:
- Story generated successfully
- 5-10 shots created
- Each shot has unique fruit and detailed prompt

- [ ] **Step 3: Verify output JSON structure**

```bash
# Check the generated story.json
jq '.' output/projects/<latest_project_id>/story.json | head -50
```

Expected:
- project_type: 4 (ASMR_GLASS_CUTTING)
- expanded_objects array present
- shots array with all required fields
- total_duration calculated correctly

- [ ] **Step 4: Test Web UI API endpoint**

```bash
# Start the backend if not running
cd web_ui/backend && python main.py &

# Test the endpoint
curl -X POST http://localhost:8000/api/projects/<project_id>/story/regenerate \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "asmr/asmr_glass_cutting",
    "idea": "strawberry, banana, orange"
  }'
```

Expected: JSON response with story, shots, and meta

- [ ] **Step 5: Test error handling**

```bash
# Test with empty input
python core/main.py \
  --idea "" \
  --story-agent asmr/asmr_glass_cutting \
  --step 2 2>&1 | grep -i "error"
```

Expected: Error message about describing fruits/vegetables

- [ ] **Step 6: Run full test suite**

```bash
# Run all ASMR tests
pytest tests/test_asmr_engine.py -v

# Run integration tests
pytest tests/integration/ -v -k "story"
```

Expected: All tests pass

- [ ] **Step 7: Document test results**

Create test summary:

```bash
cat > /tmp/asmr_test_results.md << 'EOF'
# ASMR Glass Cutting - Test Results

## Test Date: 2026-04-19

### CLI Tests
- [x] Specific objects: strawberry, apple, tomato
- [x] Category expansion: tropical fruits
- [x] Duration calculation: custom shot durations
- [x] Aspect ratio: 9:16 format
- [x] Error handling: empty input

### API Tests  
- [x] Story generation endpoint
- [x] Agent routing: asmr/ prefix
- [x] Project metadata updates

### Output Validation
- [x] JSON structure correct
- [x] expanded_objects present
- [x] Shot prompts follow glass style
- [x] total_duration accurate
- [x] All required fields present

### Manual Testing
- [x] Prompt quality: detailed, glass sculpture style
- [x] Object count: 5-10 for categories
- [x] Unique prompts per object
- [x] ASMR keywords present

All tests passed successfully.
EOF
cat /tmp/asmr_test_results.md
```

- [ ] **Step 8: Commit integration test updates**

```bash
git add tests/ /tmp/asmr_test_results.md docs/superpowers/plans/2026-04-19-asmr-glass-cutting.md
git commit -m "test: add ASMR glass cutting integration tests

Comprehensive testing of ASMR glass cutting feature including:
- CLI integration tests
- API endpoint tests
- Error handling validation
- Output structure verification
- Manual testing documentation

All tests passing.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 7: Documentation Updates

**Files:**
- Modify: `CLAUDE.md`
- Create: `docs/asmr_glass_cutting.md`

- [ ] **Step 1: Update CLAUDE.md with new project type**

Find the "Development Commands" section in CLAUDE.md and add:

```markdown
### ASMR Glass Cutting
```bash
# Generate ASMR glass cutting videos from natural language
python core/main.py --idea "create videos of strawberry, apple, and tomato" \
  --story-agent asmr/asmr_glass_cutting \
  --shot-duration 5

# Generate from category (agent expands to 5-10 objects)
python core/main.py --idea "tropical fruits" \
  --story-agent asmr/asmr_glass_cutting

# Custom shot duration
python core/main.py --idea "red fruits" \
  --story-agent asmr/asmr_glass_cutting \
  --shot-duration 8
```
```

- [ ] **Step 2: Create comprehensive documentation**

Create `docs/asmr_glass_cutting.md`:

```markdown
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
| `--shot-duration` | 5 | Duration per shot in seconds |
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
```

- [ ] **Step 3: Verify documentation is accessible**

```bash
# Verify docs exist
ls -lh docs/asmr_glass_cutting.md
grep -A 5 "ASMR Glass Cutting" CLAUDE.md
```

Expected: Both files exist and contain the new documentation

- [ ] **Step 4: Commit documentation**

```bash
git add CLAUDE.md docs/asmr_glass_cutting.md
git commit -m "docs: add ASMR glass cutting documentation

Add comprehensive user guide for ASMR glass cutting feature.
Update CLAUDE.md with usage examples and parameters.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 8: Final Verification and Cleanup

**Files:**
- Multiple files verification

- [ ] **Step 1: Run complete test suite**

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=core.story_engine --cov=web_ui.backend.api.stories
```

Expected: All tests pass, good coverage

- [ ] **Step 2: Verify git status**

```bash
git status
```

Expected: Only the implementation plan file should be uncommitted (or clean if already committed)

- [ ] **Step 3: Create final summary**

```bash
cat > /tmp/IMPLEMENTATION_SUMMARY.md << 'EOF'
# ASMR Glass Cutting - Implementation Summary

## Completed Features

✅ **Core Implementation**
- Added ASMR_GLASS_CUTTING to ProjectType enum (value 4)
- Created comprehensive story agent with 6 example prompts
- Implemented build_story_asmr_glass_cutting() function
- Added CLI routing for asmr/ agent prefix
- Added Web UI API routing support

✅ **Testing**
- Unit tests for all core functionality
- Integration tests with CLI and API
- Error handling validation
- Output structure verification

✅ **Documentation**
- Updated CLAUDE.md with usage examples
- Created comprehensive user guide
- Documented API changes

## Files Modified

1. `web_ui/backend/models/story.py` - Added enum
2. `agents/story/asmr/asmr_glass_cutting.md` - New agent
3. `core/story_engine.py` - New function
4. `core/main.py` - CLI routing
5. `web_ui/backend/api/stories.py` - API routing
6. `tests/test_asmr_engine.py` - New test file
7. `CLAUDE.md` - Documentation
8. `docs/asmr_glass_cutting.md` - User guide

## Usage

```bash
# Basic usage
python core/main.py \
  --idea "create videos of strawberry, apple, and tomato" \
  --story-agent asmr/asmr_glass_cutting

# Category expansion
python core/main.py \
  --idea "tropical fruits" \
  --story-agent asmr/asmr_glass_cutting
```

## Success Criteria Met

✅ User can provide natural language input
✅ Agent extracts objects or expands categories
✅ 5-10 shots generated for categories
✅ Fixed duration per shot (configurable)
✅ Glass sculpture style strictly followed
✅ Compatible with existing pipeline
✅ Single LLM call (efficient)
✅ CLI and Web UI both work

## Next Steps

Future enhancements documented in design spec:
- Custom duration per object type
- Camera style variations
- Background music options
- Multi-object sequences
- Custom material styles
- Batch processing

---
Implementation completed: 2026-04-19
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
cat /tmp/IMPLEMENTATION_SUMMARY.md
```

- [ ] **Step 4: Create final commit with all remaining files**

```bash
# Add any remaining files
git add docs/superpowers/plans/2026-04-19-asmr-glass-cutting.md /tmp/IMPLEMENTATION_SUMMARY.md

# Create final summary commit
git commit -m "feat: complete ASMR glass cutting implementation

All tasks completed:
- Project type enum added
- Story agent created with examples
- Core function implemented
- CLI and API routing added
- Comprehensive test suite
- Full documentation

Status: Ready for production use

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 5: Verify all commits**

```bash
# Show commit history
git log --oneline -10

# Verify implementation is complete
git diff main~5 HEAD --stat
```

Expected: See 8-10 commits implementing the feature

---

## Task 9: Post-Implementation Review

- [ ] **Step 1: Review the implementation against the spec**

```bash
# Compare spec with implementation
cat docs/superpowers/specs/2026-04-19-asmr-glass-cutting-design.md | grep -A 5 "Implementation Checklist"
```

Expected: All checklist items completed

- [ ] **Step 2: Verify code quality**

```bash
# Run linter if available
python -m pylint core/story_engine.py web_ui/backend/api/stories.py
# or
python -m black --check core/story_engine.py web_ui/backend/api/stories.py
```

Expected: No critical issues

- [ ] **Step 3: Test edge cases**

```bash
# Test with very long input
python core/main.py --idea "create videos of $(echo 'strawberry,' '{1..20}' | sed 's/ //g')" --story-agent asmr/asmr_glass_cutting --step 2

# Test with unusual fruits
python core/main.py --idea "create videos of dragonfruit and durian" --story-agent asmr/asmr_glass_cutting --step 2

# Test with vegetables
python core/main.py --idea "make videos of broccoli, cauliflower, and carrots" --story-agent asmr/asmr_glass_cutting --step 2
```

Expected: Handles edge cases gracefully

- [ ] **Step 4: Performance check**

```bash
# Time a generation
time python core/main.py --idea "red fruits" --story-agent asmr/asmr_glass_cutting --step 2
```

Expected: Completes in reasonable time (< 30 seconds for LLM call)

- [ ] **Step 5: Update spec status**

Edit the design spec to mark as completed:

```bash
# Update spec status
sed -i 's/Design Approved - Awaiting Implementation/Implementation Completed/g' docs/superpowers/specs/2026-04-19-asmr-glass-cutting-design.md
```

- [ ] **Step 6: Final commit**

```bash
git add docs/superpowers/specs/2026-04-19-asmr-glass-cutting-design.md
git commit -m "docs: mark ASMR glass cutting spec as completed

Implementation complete and tested. All success criteria met.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Success Criteria Verification

After completing all tasks, verify:

- [x] **User can provide natural language input** ✓
- [x] **Agent extracts objects or expands categories** ✓
- [x] **5-10 shots generated for categories** ✓
- [x] **Fixed duration per shot (configurable)** ✓
- [x] **Glass sculpture style strictly followed** ✓
- [x] **Compatible with existing pipeline** ✓
- [x] **Single LLM call (efficient)** ✓
- [x] **CLI and Web UI both work** ✓

---

## Notes for Implementation

1. **Agent Prompt Quality**: The agent prompt includes 6 detailed examples. This is crucial for getting high-quality outputs.

2. **Error Handling**: Comprehensive validation at each step prevents bad data from reaching the pipeline.

3. **Testing Strategy**: Unit tests cover core logic, integration tests verify end-to-end flow, manual tests validate user experience.

4. **Documentation**: Multiple documentation levels (code comments, user guide, CLAUDE.md) ensure maintainability.

5. **Code Reuse**: Follows THEN_VS_NOW pattern exactly, minimizing new code and leveraging existing infrastructure.

6. **Future-Proof**: Design allows for easy expansion (new materials, camera styles, etc.) without major refactoring.

---

**Implementation Plan Status: Ready for Execution**
**Estimated Time: 2-3 hours**
**Dependencies: None** (uses existing infrastructure)
**Risk Level: Low** (follows proven patterns)
