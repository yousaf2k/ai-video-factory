"""
Shot Planner - Plan cinematic shots using LLM agents.
"""
from core.llm_engine import get_provider
from core.agent_loader import load_agent_prompt
from core.logger_config import setup_agent_logger
from core.log_decorators import log_agent_call
import json
import re
from config import (DEFAULT_SHOTS_PER_SCENE, MIN_SHOTS_PER_SCENE, MAX_SHOTS_PER_SCENE,
                    SHOT_GENERATION_BATCH_SIZE, LLM_PROVIDER, MAX_PARALLEL_BATCH_THREADS,
                    DEFAULT_SHOT_LENGTH)
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


# Get logger for agent operations
logger = setup_agent_logger(__name__)


def is_local_provider():
    """Check if current LLM provider is local (Ollama or LMStudio)"""
    local_providers = ['ollama', 'lmstudio']
    return LLM_PROVIDER.lower() in local_providers


def plan_shots_batch(scenes_batch, batch_num, total_batches, max_shots_instruction, image_agent, video_agent):
    """Plan shots for a batch of scenes"""
    # Create scene graph for this batch
    batch_graph = json.dumps(scenes_batch, ensure_ascii=False)

    # Build batch-specific instruction
    batch_instruction = f"""
BATCH PROCESSING: This is batch {batch_num} of {total_batches}
{max_shots_instruction}

IMPORTANT: Generate ONLY shots for these {len(scenes_batch)} scenes in this batch.
"""

    # Try to use agent prompts
    try:
        user_input = f"{batch_graph}{batch_instruction}"
        image_prompt = load_agent_prompt("image", user_input, image_agent)

        provider = get_provider()
        response = provider.ask(image_prompt, response_format="application/json")
        shots = extract_and_repair_json(response)

        logger.info(f"Batch {batch_num}/{total_batches}: Generated {len(shots)} shots")
        return shots

    except (FileNotFoundError, ValueError):
        # Fall back to legacy prompt
        print(f"[WARN] Image agent '{image_agent}' not found, using legacy prompt for batch {batch_num}")
        prompt = f"""
Create cinematic shots for WAN 2.2.{batch_instruction}

Return JSON list (each shot MUST include narration from scene):
[
  {{
   "image_prompt":"",
   "motion_prompt":"",
   "camera":"slow pan | dolly | static | orbit | zoom | tracking | drone | arc | walk | fpv | dronedive | bullettime ",
   "narration":""
  }}
]

SCENES:
{batch_graph}
"""
        provider = get_provider()
        response = provider.ask(prompt, response_format="application/json")
        shots = extract_and_repair_json(response)
        logger.info(f"Batch {batch_num}/{total_batches}: Generated {len(shots)} shots (legacy mode)")
        return shots


def extract_and_repair_json(response):
    """
    Extract JSON from LLM response and repair common issues.

    Args:
        response: Raw LLM response string

    Returns:
        Parsed JSON object

    Raises:
        ValueError: If JSON cannot be parsed after repair attempts
    """
    if not response or not isinstance(response, str):
        raise ValueError("Response must be a non-empty string")

    original_response = response
    response = response.strip()

    # Remove markdown code blocks
    if response.startswith("```json"):
        response = response[7:]
    elif response.startswith("```"):
        response = response[3:]
    if response.endswith("```"):
        response = response[:-3]
    response = response.strip()

    # Find JSON array start
    start_idx = response.find('[')
    if start_idx == -1:
        raise ValueError("No JSON array found in response")

    # Find matching end bracket
    bracket_count = 0
    in_string = False
    escape_next = False
    end_idx = -1

    for i in range(start_idx, len(response)):
        char = response[i]

        if escape_next:
            escape_next = False
            continue

        if char == '\\':
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if not in_string:
            if char == '[':
                bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    end_idx = i + 1
                    break

    if end_idx == -1:
        # Try to find the last ] and hope for the best
        last_bracket = response.rfind(']')
        if last_bracket > start_idx:
            end_idx = last_bracket + 1
        else:
            raise ValueError("Could not find complete JSON array")

    json_str = response[start_idx:end_idx]

    # Strategy 1: Try strict JSON parsing first
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parsing failed: {e}, attempting repair...")

    # Strategy 2: Try json5 (more lenient parser)
    try:
        import json5
        return json5.loads(json_str)
    except ImportError:
        logger.debug("json5 not available, skipping...")
    except Exception as e2:
        logger.debug(f"json5 parsing failed: {e2}")

    # Strategy 3: Apply regex-based repairs
    json_repaired = apply_json_repairs(json_str)
    try:
        return json.loads(json_repaired)
    except json.JSONDecodeError as e:
        logger.debug(f"Regex repair failed: {e}")

    # Strategy 4: Extract individual objects as last resort
    try:
        valid_objects = extract_complete_objects(json_str)
        if valid_objects:
            logger.info(f"Extracted {len(valid_objects)} valid shot objects from malformed JSON")
            return valid_objects
    except Exception as e3:
        logger.debug(f"Object extraction failed: {e3}")

    # All strategies failed
    raise ValueError(f"Failed to parse JSON after multiple repair attempts. Last error: {e}\nResponse snippet: {json_str[:500]}...")


def apply_json_repairs(json_str):
    """Apply common JSON repairs using regex patterns"""
    repaired = json_str

    # Fix 1: Remove control characters that break JSON
    repaired = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', repaired)

    # Fix 2: Fix trailing commas before closing brackets/braces
    repaired = re.sub(r',(\s*[}\]])', r'\1', repaired)

    # Fix 3: Fix unquoted property names (common in LLM output)
    # This is tricky, so we'll be conservative
    # repaired = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)', r'\1"\2"\3', repaired)

    # Fix 4: Add missing commas between objects
    repaired = re.sub(r'}\s*{', '},{', repaired)
    repaired = re.sub(r']\s*\[', '],[', repaired)
    repaired = re.sub(r'"\s*\}', '"}', repaired)  # Before closing brace
    repaired = re.sub(r'"\s*\]', '"]', repaired)  # Before closing bracket

    # Fix 5: Fix escaped quotes issues
    repaired = repaired.replace('\\"', '"')  # Remove double escapes
    repaired = repaired.replace('\\', '\\\\')  # Ensure proper escapes

    # Fix 6: Ensure proper string termination in value fields
    # Look for patterns like "image_prompt": <incomplete string>
    def fix_unterminated_strings(match):
        """Fix unterminated strings in JSON objects"""
        return match.group(0).rstrip() + '",'

    # Pattern: property followed by " but missing closing quote and comma
    repaired = re.sub(r'("[\w_]+"):\s*"[^"}\]]*$', fix_unterminated_strings, repaired, flags=re.MULTILINE)

    return repaired


def extract_complete_objects(json_str):
    """
    Extract complete JSON objects from malformed JSON string.
    Uses a state machine to track brace nesting.
    """
    objects = []
    i = 0
    length = len(json_str)

    while i < length:
        # Find next object start
        while i < length and json_str[i] != '{':
            i += 1
        if i >= length:
            break

        # Track nesting
        start = i
        depth = 0
        in_string = False
        escape_next = False

        while i < length:
            char = json_str[i]

            if escape_next:
                escape_next = False
                i += 1
                continue

            if char == '\\':
                escape_next = True
                i += 1
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                i += 1
                continue

            if not in_string:
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        # Found complete object
                        obj_str = json_str[start:i+1]
                        try:
                            obj = json.loads(obj_str)
                            # Validate it's a shot object
                            if isinstance(obj, dict) and any(k in obj for k in ['image_prompt', 'motion_prompt', 'camera']):
                                objects.append(obj)
                        except:
                            pass
                        break
            i += 1

        i += 1

    return objects


@log_agent_call
def plan_shots(scene_graph, max_shots=None, image_agent="default", video_agent="default", shots_per_scene=None):
    """
    Plan cinematic shots for WAN 2.2 video generation.

    Args:
        scene_graph: The scene graph JSON
        max_shots: Maximum number of shots to create (optional)
        image_agent: Name of image prompt agent to use (default: "default")
                    Available: default, artistic
        video_agent: Name of video motion agent to use (default: "default")
                    Available: default, cinematic
        shots_per_scene: Target number of shots per scene (optional)

    Returns:
        List of shot dictionaries with image_prompt, motion_prompt, and camera

    Raises:
        ValueError: If scene_graph is None or empty
        ValueError: If scene_graph is not a valid JSON string or dict
    """
    # Validate inputs
    if scene_graph is None:
        raise ValueError("scene_graph cannot be None")
    if isinstance(scene_graph, str):
        if not scene_graph.strip():
            raise ValueError("scene_graph cannot be empty string")
        try:
            json.loads(scene_graph)
        except json.JSONDecodeError as e:
            raise ValueError(f"scene_graph is not valid JSON: {e}")
    elif not isinstance(scene_graph, list):
        if not scene_graph:
            raise ValueError("scene_graph must be a non-empty list or valid JSON string")

    # Calculate scene count
    scenes = json.loads(scene_graph) if isinstance(scene_graph, str) else scene_graph
    scene_count = len(scenes)

    # Determine shots per scene target
    if shots_per_scene is None:
        shots_per_scene = DEFAULT_SHOTS_PER_SCENE

    # Check if scenes have scene_length field for intelligent distribution
    has_scene_lengths = any("scene_length" in s or "scene_duration" in s for s in scenes)

    # Build enhanced shot instruction based on parameters
    max_shots_instruction = ""
    if has_scene_lengths:
        # Use scene-based shot distribution
        logger.info("Using scene-based shot distribution (scene_length detected)")
        print(f"[INFO] Using scene-based shot distribution")

        scene_shot_plan = []
        total_shots_from_durations = 0

        for i, scene in enumerate(scenes):
            # Support both scene_length and scene_duration field names
            scene_len = scene.get("scene_length") or scene.get("scene_duration", 0)
            if scene_len > 0:
                shots_for_scene = max(MIN_SHOTS_PER_SCENE, int(scene_len / DEFAULT_SHOT_LENGTH))
                scene_shot_plan.append({
                    'scene_idx': i,
                    'shots': shots_for_scene,
                    'duration': scene_len
                })
                total_shots_from_durations += shots_for_scene
                logger.info(f"Scene {i}: {shots_for_scene} shots ({scene_len}s ÷ {DEFAULT_SHOT_LENGTH}s/shot)")
                print(f"[INFO] Scene {i}: {shots_for_scene} shots ({scene_len}s ÷ {DEFAULT_SHOT_LENGTH}s/shot)")

        # Update max_shots if calculated from durations
        if max_shots is None:
            max_shots = total_shots_from_durations

        # Format scene shot plan for LLM instruction
        scene_plan_text = "\n".join([
            f"  Scene {s['scene_idx']}: {s['shots']} shots ({s['duration']}s)"
            for s in scene_shot_plan
        ])

        max_shots_instruction = f"""
SCENE-BASED SHOT DISTRIBUTION:
Generate the following shots for each scene based on scene duration:
{scene_plan_text}

Total shots: {total_shots_from_durations} (~{total_shots_from_durations * DEFAULT_SHOT_LENGTH}s video)

IMPORTANT:
- Follow the exact shot count specified for each scene above
- Each scene MUST have different camera angles (wide, close-up, detail, etc.)
"""
        logger.info(f"Total shots planned from scene durations: {total_shots_from_durations} (~{total_shots_from_durations * DEFAULT_SHOT_LENGTH}s video)")
        print(f"[INFO] Total shots planned: {total_shots_from_durations} (~{total_shots_from_durations * DEFAULT_SHOT_LENGTH}s video)")

    elif max_shots:
        # Calculate shots per scene from max_shots (even distribution)
        shots_per_scene_target = max(MIN_SHOTS_PER_SCENE, max_shots // scene_count)

        # Log shot distribution planning
        print(f"[INFO] Shot distribution: {max_shots} shots across {scene_count} scenes (~{shots_per_scene_target} shots/scene)")
        logger.info(f"Shot distribution: {max_shots} shots across {scene_count} scenes (~{shots_per_scene_target} shots/scene)")

        max_shots_instruction = f"""
IMPORTANT SHOT DISTRIBUTION:
- Generate exactly {max_shots} shots total ({shots_per_scene_target}-{max_shots // scene_count + 2} shots per scene)
- DISTRIBUTE shots evenly across all {scene_count} scenes
- Each scene MUST have at least {MIN_SHOTS_PER_SCENE} shots (different camera angles)
"""
    else:
        # Use shots_per_scene target
        estimated_total = scene_count * shots_per_scene
        max_shots_instruction = f"""
IMPORTANT SHOT DISTRIBUTION:
- Generate approximately {shots_per_scene}-{min(shots_per_scene + 2, MAX_SHOTS_PER_SCENE)} shots for EACH of the {scene_count} scenes
- Estimated total: {estimated_total} shots
- Each scene MUST have at least {MIN_SHOTS_PER_SCENE} shots with different camera angles
- Maximum: {MAX_SHOTS_PER_SCENE} shots per scene (to prevent over-generation)
"""

    # Use batch processing if there are many scenes to avoid truncation
    batch_size = SHOT_GENERATION_BATCH_SIZE
    if scene_count > batch_size:
        # Split scenes into batches
        total_batches = (scene_count + batch_size - 1) // batch_size
        batches = []

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, scene_count)
            scenes_batch = scenes[start_idx:end_idx]

            # Adjust max_shots for this batch
            batch_max_shots = None
            if max_shots:
                batch_max_shots = max_shots // total_batches

            # Build batch-specific instruction
            batch_max_total = batch_max_shots or len(scenes_batch) * shots_per_scene
            scenes_in_batch = len(scenes_batch)
            shots_per_batch_scene = max(MIN_SHOTS_PER_SCENE, batch_max_total // scenes_in_batch) if batch_max_total else shots_per_scene

            # Create a clear batch-specific instruction (don't reuse the global one)
            batch_instruction = f"""
CRITICAL SHOT REQUIREMENTS:
- You MUST generate exactly {batch_max_total} shots for this batch
- This batch contains {scenes_in_batch} scene(s)
- For EACH scene in this batch, generate {shots_per_batch_scene}-{shots_per_batch_scene + 2} unique shots with different camera angles
- Each scene MUST have at least {MIN_SHOTS_PER_SCENE} shots (different angles: wide shot, close-up, detail, etc.)
"""

            batches.append({
                'scenes_batch': scenes_batch,
                'batch_num': batch_num + 1,
                'total_batches': total_batches,
                'max_shots_instruction': batch_instruction,
                'image_agent': image_agent,
                'video_agent': video_agent,
                'start_idx': start_idx,
                'end_idx': end_idx
            })

        # Check if provider is local
        use_parallel = not is_local_provider()

        if use_parallel:
            # Parallel processing for cloud providers
            logger.info(f"Using PARALLEL batch processing: {total_batches} batches concurrently")
            print(f"[INFO] Processing {total_batches} batches in parallel (cloud provider)")

            all_shots = []
            completed = 0
            lock = threading.Lock()

            def process_batch(batch_data):
                """Process a single batch and track progress"""
                result = plan_shots_batch(
                    scenes_batch=batch_data['scenes_batch'],
                    batch_num=batch_data['batch_num'],
                    total_batches=batch_data['total_batches'],
                    max_shots_instruction=batch_data['max_shots_instruction'],
                    image_agent=batch_data['image_agent'],
                    video_agent=batch_data['video_agent']
                )

                # Add batch number
                for shot in result:
                    shot['batch_number'] = batch_data['batch_num']

                # Update progress
                nonlocal completed
                with lock:
                    completed += 1
                    logger.info(f"Completed batch {batch_data['batch_num']}/{batch_data['total_batches']} ({completed}/{total_batches} total)")
                    print(f"[INFO] Batch {batch_data['batch_num']}/{batch_data['total_batches']} complete ({completed}/{total_batches})")

                return result, batch_data['batch_num']

            # Process batches in parallel
            max_workers = min(total_batches, MAX_PARALLEL_BATCH_THREADS)
            logger.info(f"Using {max_workers} parallel threads (max configured: {MAX_PARALLEL_BATCH_THREADS})")

            # Store results with batch numbers for later sorting
            batch_results = []

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(process_batch, batch): batch['batch_num']
                          for batch in batches}

                for future in as_completed(futures):
                    try:
                        batch_shots, batch_num = future.result()
                        batch_results.append((batch_num, batch_shots))
                    except Exception as e:
                        batch_num = futures[future]
                        logger.error(f"Batch {batch_num} failed: {e}")
                        print(f"[ERROR] Batch {batch_num} failed: {e}")

            # Sort results by batch_num to ensure correct order
            batch_results.sort(key=lambda x: x[0])
            for batch_num, batch_shots in batch_results:
                all_shots.extend(batch_shots)

        else:
            # Sequential processing for local providers
            logger.info(f"Using SEQUENTIAL batch processing: {total_batches} batches (local provider)")
            print(f"[INFO] Processing {scene_count} scenes in {total_batches} batches sequentially (local provider)")

            all_shots = []

            for batch_data in batches:
                print(f"[INFO] Processing batch {batch_data['batch_num']}/{total_batches} (scenes {batch_data['start_idx'] + 1}-{batch_data['end_idx']})")

                # Generate shots for this batch
                batch_shots = plan_shots_batch(
                    scenes_batch=batch_data['scenes_batch'],
                    batch_num=batch_data['batch_num'],
                    total_batches=batch_data['total_batches'],
                    max_shots_instruction=batch_data['max_shots_instruction'],
                    image_agent=batch_data['image_agent'],
                    video_agent=batch_data['video_agent']
                )

                # Add batch number
                for shot in batch_shots:
                    shot['batch_number'] = batch_data['batch_num']

                all_shots.extend(batch_shots)

        logger.info(f"Batch processing complete: {len(all_shots)} total shots generated")

        # Enforce max_shots limit if specified
        if max_shots and len(all_shots) > max_shots:
            print(f"[INFO] Generated {len(all_shots)} shots, limiting to {max_shots}")
            logger.info(f"Generated {len(all_shots)} shots, limiting to {max_shots}")
            all_shots = all_shots[:max_shots]

        # Log results
        if max_shots:
            if len(all_shots) == max_shots:
                print(f"[INFO] Target achieved: {len(all_shots)} shots = ~{len(all_shots) * DEFAULT_SHOT_LENGTH}s video")
            else:
                print(f"[INFO] Final shot count: {len(all_shots)} shots = ~{len(all_shots) * DEFAULT_SHOT_LENGTH}s video")
            logger.info(f"Final shot count: {len(all_shots)} shots, ~{len(all_shots) * DEFAULT_SHOT_LENGTH}s video")

        return all_shots

    # Single batch processing (original logic)
    user_input = f"{scene_graph}{max_shots_instruction}"

    # Try to use agent prompts
    try:
        # Load image agent prompt
        image_prompt = load_agent_prompt("image", user_input, image_agent)

        # Get the response
        provider = get_provider()
        response = provider.ask(image_prompt, response_format="application/json")
        shots = extract_and_repair_json(response)

        # Enforce max_shots limit if specified
        if max_shots and len(shots) > max_shots:
            print(f"[INFO] Generated {len(shots)} shots, limiting to {max_shots}")
            logger.info(f"Generated {len(shots)} shots, limiting to {max_shots}")
            shots = shots[:max_shots]

        # Log results
        if max_shots:
            if len(shots) == max_shots:
                print(f"[INFO] Target achieved: {len(shots)} shots = ~{len(shots) * DEFAULT_SHOT_LENGTH}s video")
            else:
                print(f"[INFO] Final shot count: {len(shots)} shots = ~{len(shots) * DEFAULT_SHOT_LENGTH}s video")
            logger.info(f"Final shot count: {len(shots)} shots, ~{len(shots) * DEFAULT_SHOT_LENGTH}s video")

        return shots

    except (FileNotFoundError, ValueError):
        # Fall back to legacy prompt if agent not found
        print(f"[WARN] Image agent '{image_agent}' not found, using legacy prompt")
        prompt = f"""
Create cinematic shots for WAN 2.2.{max_shots_instruction}

Return JSON list (each shot MUST include narration from scene):
[
  {{
   "image_prompt":"",
   "motion_prompt":"",
   "camera":"slow pan | dolly | static | orbit | zoom | tracking | drone | arc | walk | fpv | dronedive | bullettime ",
   "narration":""
  }}
]

SCENES:
{scene_graph}
"""
        provider = get_provider()
        response = provider.ask(prompt, response_format="application/json")
        shots = extract_and_repair_json(response)

        # Enforce max_shots limit if specified
        if max_shots and len(shots) > max_shots:
            print(f"[INFO] Generated {len(shots)} shots, limiting to {max_shots}")
            shots = shots[:max_shots]

        return shots