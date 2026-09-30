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
                    DEFAULT_SHOT_LENGTH, MIN_SHOT_DURATION, MAX_SHOT_DURATION,
                    VIDEO_PROMPT_CUT_MARGIN_SECONDS)
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import uuid


# Get logger for agent operations
logger = setup_agent_logger(__name__)

# Timing instruction appended to shot planning prompts so that timestamped
# cuts in video_prompt stay within each shot's rendered clip duration
VIDEO_PROMPT_TIMING_INSTRUCTION = (
    "VIDEO PROMPT TIMING: Each shot is rendered as a single video clip whose length is the "
    "shot's \"duration\" field in seconds. All timestamped cuts in video_prompt must be "
    "strictly increasing and fit inside that duration, leaving at least "
    f"{VIDEO_PROMPT_CUT_MARGIN_SECONDS} seconds before the end (format MM:SS.mmm)."
)

# Per-shot clip duration instruction: the LLM chooses each clip length so
# pacing matches the action instead of a fixed default
SHOT_DURATION_INSTRUCTION = (
    f"PER-SHOT CLIP DURATION: Give every shot a \"duration\" field - the rendered clip length "
    f"in seconds, between {MIN_SHOT_DURATION} and {MAX_SHOT_DURATION}. Choose it from the "
    f"action's natural length: quick reactions or inserts 1-3s, standard beats 4-6s, complex "
    f"multi-beat sequences 8-{MAX_SHOT_DURATION}s. The durations of the shots in each scene "
    f"should sum to approximately that scene's duration."
)

# Multi-shot clips: longer clips should be split into timestamped sub-shots
SUB_SHOT_INSTRUCTION = (
    "MULTI-SHOT CLIPS: A video_prompt may split its clip into timestamped sub-shots "
    "([Shot 2] At 00:04.500, the camera cuts to...). Clips of 6 seconds or more SHOULD contain "
    "2-3 sub-shots whenever the action has multiple distinct beats, viewpoints or moments; "
    "clips under 6 seconds stay a single sub-shot ([Shot 1] only). Every cut must introduce "
    "new information (subject, space, viewpoint or time); use camera motion for small "
    "framing changes."
)


def is_local_provider():
    """Check if current LLM provider is local (Ollama or LMStudio)"""
    local_providers = ['ollama', 'lmstudio']
    return LLM_PROVIDER.lower() in local_providers


def plan_shots_batch(scenes_batch, batch_num, total_batches, max_shots_instruction, shots_agent):
    """Plan shots for a batch of scenes"""
    # Create scene graph for this batch
    batch_graph = json.dumps(scenes_batch, ensure_ascii=False)

    # Build batch-specific instruction
    batch_instruction = f"""
BATCH PROCESSING: This is batch {batch_num} of {total_batches}
{max_shots_instruction}

IMPORTANT: Generate ONLY shots for these {len(scenes_batch)} scenes in this batch.
{SHOT_DURATION_INSTRUCTION}
{SUB_SHOT_INSTRUCTION}
{VIDEO_PROMPT_TIMING_INSTRUCTION}
"""

    # Try to use agent prompts
    try:
        user_input = f"{batch_graph}{batch_instruction}"
        image_prompt = load_agent_prompt("shots", user_input, shots_agent)

        provider = get_provider()
        response = provider.ask(image_prompt, response_format="application/json")
        shots = extract_and_repair_json(response)
        repair_batch_scene_ids(shots, scenes_batch, batch_num, total_batches)

        logger.info(f"Batch {batch_num}/{total_batches}: Generated {len(shots)} shots")
        validate_and_repair_shots(shots, shots_agent)
        return shots

    except (FileNotFoundError, ValueError):
        # Fall back to legacy prompt
        print(f"[WARN] Shots agent '{shots_agent}' not found, using legacy prompt for batch {batch_num}")
        prompt = f"""
Create cinematic shots for WAN 2.2.{batch_instruction}

Return JSON list (each shot):
[
  {{
   "scene_id": 0,
   "duration": 5,
   "image_prompt":"",
   "motion_prompt":"",
   "video_prompt":"",
   "soundfx_prompt":"",
   "camera":"slow pan | dolly | static | orbit | zoom | tracking | drone | arc | walk | fpv | dronedive | bullettime "
  }}
]

The "duration" of each shot is its rendered clip length in seconds ({MIN_SHOT_DURATION}-{MAX_SHOT_DURATION}).
The "video_prompt" of each shot is a detailed timestamped MiniMax H3 I2VA prompt: first-frame instruction line ("For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced."), then "integrated_multimodal_description:" with [Shot 1] (no timestamp; clips of 6 seconds or more should continue with [Shot 2], [Shot 3] sub-shots at strictly increasing cut times inside the clip duration), then "overall_soundscape:" (1-4 sentences) and "non_diegetic_music:" (1-3 sentences or N/A).

SCENES:
{batch_graph}
"""
        provider = get_provider()
        response = provider.ask(prompt, response_format="application/json")
        shots = extract_and_repair_json(response)
        repair_batch_scene_ids(shots, scenes_batch, batch_num, total_batches)
        validate_and_repair_shots(shots, shots_agent)
        logger.info(f"Batch {batch_num}/{total_batches}: Generated {len(shots)} shots (legacy mode)")
        return shots


# Matches a sub-shot header followed by a cut time, e.g.
# "[Shot 2] At 00:03.500, the camera cuts to..."  (also accepts 3.500 / 0:03.500)
_CUT_TIME_RE = re.compile(
    r"\[Shot\s*(\d+)\][^\[]{0,400}?[Aa]t\s*(?:\d{1,2}:)?(\d{1,2}):(\d{2})\.(\d{1,3})"
)

# Fields every MiniMax H3 video_prompt must contain
_REQUIRED_VIDEO_PROMPT_FIELDS = (
    ("For the target video", "first-frame instruction line"),
    ("<Picture 1>", "<Picture 1> anchor"),
    ("integrated_multimodal_description:", "integrated_multimodal_description"),
    ("overall_soundscape:", "overall_soundscape"),
    ("non_diegetic_music:", "non_diegetic_music"),
)


def parse_video_prompt_cut_times(video_prompt):
    """Extract (shot_number, cut_time_seconds) pairs from a video_prompt.

    Only later sub-shots carry a timestamp; [Shot 1] starts at 0.00 by
    definition and is not returned unless it repeats one.
    """
    cuts = []
    for match in _CUT_TIME_RE.finditer(video_prompt or ""):
        shot_num = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        millis = int(match.group(4).ljust(3, "0"))
        cuts.append((shot_num, minutes * 60 + seconds + millis / 1000.0))
    return cuts


def validate_video_prompt(video_prompt, clip_duration=None):
    """Validate a MiniMax H3 video_prompt against the required structure.

    Args:
        video_prompt: The prompt text to check.
        clip_duration: The shot's rendered clip length in seconds. When given,
            cut times must fit inside the clip with a safety margin (the H3
            frame snap can extend a clip slightly, and the final sub-shot
            needs room to play out).

    Returns:
        List of human-readable problems; empty list means the prompt is valid.
    """
    problems = []
    if not video_prompt or not str(video_prompt).strip():
        return ["video_prompt is empty"]

    text = str(video_prompt)

    for needle, label in _REQUIRED_VIDEO_PROMPT_FIELDS:
        if needle not in text:
            problems.append(f"missing {label}")

    # Sub-shot numbering must start at 1 and be sequential
    shot_numbers = [int(n) for n in re.findall(r"\[Shot\s*(\d+)\]", text)]
    if shot_numbers:
        expected = list(range(1, max(shot_numbers) + 1))
        if sorted(set(shot_numbers)) != expected:
            problems.append(
                f"sub-shot numbers must be sequential starting at [Shot 1], got {sorted(set(shot_numbers))}"
            )

    # Cut times: strictly increasing and inside the clip duration
    cuts = parse_video_prompt_cut_times(text)
    previous_time = None
    for shot_num, cut_time in cuts:
        if previous_time is not None and cut_time <= previous_time:
            problems.append(
                f"[Shot {shot_num}] cut time {cut_time:.3f}s is not after the previous cut ({previous_time:.3f}s)"
            )
        previous_time = cut_time

    if clip_duration:
        margin = VIDEO_PROMPT_CUT_MARGIN_SECONDS
        for shot_num, cut_time in cuts:
            if cut_time > clip_duration:
                problems.append(
                    f"[Shot {shot_num}] cut time {cut_time:.3f}s is outside the {clip_duration:g}s clip"
                )
            elif cut_time > clip_duration - margin:
                problems.append(
                    f"[Shot {shot_num}] cut time {cut_time:.3f}s must be at or before "
                    f"{clip_duration - margin:.3f}s to leave the final sub-shot room (clip is {clip_duration:g}s)"
                )

    return problems


def ensure_shot_durations(shots):
    """Normalize each shot's duration: default missing values and clamp to the
    configured range. Returns the number of shots whose duration was adjusted."""
    adjusted = 0
    for shot in shots or []:
        if not isinstance(shot, dict):
            continue
        raw = shot.get('duration')
        try:
            duration = float(raw)
        except (TypeError, ValueError):
            duration = None
        if duration is None:
            duration = float(DEFAULT_SHOT_LENGTH)
            adjusted += 1
        clamped = max(float(MIN_SHOT_DURATION), min(float(MAX_SHOT_DURATION), duration))
        if clamped != duration:
            adjusted += 1
        shot['duration'] = clamped
    return adjusted


def validate_and_repair_shots(shots, shots_agent):
    """Validate video_prompts and re-ask the LLM once to fix broken ones.

    Structural problems (missing fields, non-sequential sub-shot numbers, cut
    times outside the clip) are repaired with one follow-up LLM call per
    batch. Clips that stay single-sub-shot are only logged as warnings - the
    planner instructions already push long clips toward 2-3 sub-shots.
    """
    if not isinstance(shots, list):
        return shots

    ensure_shot_durations(shots)

    invalid = []
    for pos, shot in enumerate(shots):
        if not isinstance(shot, dict):
            continue
        problems = validate_video_prompt(shot.get('video_prompt'), shot.get('duration'))
        if problems:
            invalid.append((pos, shot, problems))

    if not invalid:
        return shots

    for pos, shot, problems in invalid:
        logger.warning(
            f"Shot {shot.get('index', pos + 1)}: video_prompt validation failed: {'; '.join(problems)}"
        )
        print(f"[WARN] Shot {shot.get('index', pos + 1)}: invalid video_prompt ({'; '.join(problems)})")

    # One repair attempt for the invalid shots. Shots are matched back by their
    # list position because 'index' may not be assigned yet during planning.
    try:
        repair_payload = [
            {
                "position": pos,
                "duration": shot.get('duration'),
                "current_video_prompt": shot.get('video_prompt'),
                "problems": problems,
            }
            for pos, shot, problems in invalid
        ]
        repair_instruction = f"""
{SHOT_DURATION_INSTRUCTION}
{SUB_SHOT_INSTRUCTION}
{VIDEO_PROMPT_TIMING_INSTRUCTION}

The following video_prompts failed validation. Fix each one and return a JSON array where
each item is {{"position": <original position>, "video_prompt": "<corrected prompt>"}}.
Fix ONLY the listed problems; keep everything else about each prompt unchanged.

INVALID VIDEO PROMPTS:
{json.dumps(repair_payload, ensure_ascii=False, indent=2)}
"""
        provider = get_provider()
        response = provider.ask(repair_instruction, response_format="application/json")
        repairs = extract_and_repair_json(response)
        if isinstance(repairs, dict):
            repairs = [repairs]

        repaired_count = 0
        for repair in repairs or []:
            if not isinstance(repair, dict):
                continue
            pos = repair.get('position')
            if not isinstance(pos, int) or not (0 <= pos < len(shots)) or not isinstance(shots[pos], dict):
                logger.warning("Repair response referenced an unknown position; skipping that entry")
                continue
            target = shots[pos]
            fixed_prompt = (repair.get('video_prompt') or '').strip()
            if not fixed_prompt:
                continue
            remaining = validate_video_prompt(fixed_prompt, target.get('duration'))
            if remaining:
                logger.warning(f"Shot {target.get('index', '?')}: repair attempt still invalid: {'; '.join(remaining)}")
                continue
            target['video_prompt'] = fixed_prompt
            repaired_count += 1

        logger.info(f"Repaired {repaired_count}/{len(invalid)} invalid video_prompts")
    except Exception as e:
        logger.warning(f"video_prompt repair pass failed (keeping original prompts): {e}")

    return shots


def repair_batch_scene_ids(shots, scenes_batch, batch_num=1, total_batches=1):
    """Pin each shot's scene_id to the scenes this batch actually received.

    The LLM sometimes echoes scene_id 0 (or drops the field) even when the
    input scene carries another index, which silently merges a scene's shots
    into another scene and breaks per-scene grouping downstream (image
    generation is driven per scene). A batch only ever contains its own
    scenes, so scene_id can be repaired deterministically from scenes_batch.

    Single-scene batches (the default: SHOT_GENERATION_BATCH_SIZE=1) are
    pinned exactly. Multi-scene batches keep valid scene_ids and reassign
    only shots whose scene_id is missing or belongs to another batch.
    """
    if not isinstance(shots, list) or not scenes_batch:
        return shots

    scene_ids = [s.get('scene_id') for s in scenes_batch if isinstance(s, dict)]
    if not scene_ids:
        return shots

    if len(scene_ids) == 1:
        expected = scene_ids[0]
        for pos, shot in enumerate(shots):
            if not isinstance(shot, dict) or shot.get('scene_id') == expected:
                continue
            logger.warning(
                f"Batch {batch_num}/{total_batches}: shot {shot.get('index', pos + 1)} had scene_id "
                f"{shot.get('scene_id')!r} but this batch only contains scene {expected!r}; repairing"
            )
            shot['scene_id'] = expected
        return shots

    valid_ids = list(dict.fromkeys(scene_ids))
    invalid_shots = [
        shot for shot in shots
        if isinstance(shot, dict) and shot.get('scene_id') not in valid_ids
    ]
    if not invalid_shots:
        return shots

    logger.warning(
        f"Batch {batch_num}/{total_batches}: {len(invalid_shots)} shots had scene_id outside this "
        f"batch's scenes {valid_ids}; reassigning to the scenes with the fewest shots"
    )
    counts = {sid: 0 for sid in valid_ids}
    for shot in shots:
        if isinstance(shot, dict) and shot.get('scene_id') in counts:
            counts[shot['scene_id']] += 1
    for shot in invalid_shots:
        target = min(valid_ids, key=lambda sid: (counts[sid], valid_ids.index(sid)))
        shot['scene_id'] = target
        counts[target] += 1

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
def plan_shots(scene_graph, max_shots=None, shots_agent="default", shots_per_scene=None):
    """
    Plan cinematic shots for WAN 2.2 video generation.

    Args:
        scene_graph: The scene graph JSON
        max_shots: Maximum number of shots to create (optional)
        shots_agent: Name of shots prompt agent to use (default: "default")
                    Available: default, artistic
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
    parsed_graph = json.loads(scene_graph) if isinstance(scene_graph, str) else scene_graph
    
    # Extract scenes list from story wrapper if necessary
    if isinstance(parsed_graph, dict) and "scenes" in parsed_graph:
        scenes = parsed_graph["scenes"]
    else:
        scenes = parsed_graph
        
    # Inject 0-based index into each scene so LLM knows which index to return
    for i, scene in enumerate(scenes):
        scene['scene_id'] = i
        
    scene_graph_with_indices = json.dumps(scenes, ensure_ascii=False, indent=2)
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
                shots_for_scene = max(MIN_SHOTS_PER_SCENE or 1, int(scene_len / DEFAULT_SHOT_LENGTH))
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
        shots_per_scene_target = max(MIN_SHOTS_PER_SCENE or 1, max_shots // scene_count)

        # Log shot distribution planning
        print(f"[INFO] Shot distribution: {max_shots} shots across {scene_count} scenes (~{shots_per_scene_target} shots/scene)")
        logger.info(f"Shot distribution: {max_shots} shots across {scene_count} scenes (~{shots_per_scene_target} shots/scene)")

        max_shots_instruction = f"""
IMPORTANT SHOT DISTRIBUTION:
- Generate exactly {max_shots} shots total ({shots_per_scene_target}-{max_shots // scene_count + 2} shots per scene)
- DISTRIBUTE shots evenly across all {scene_count} scenes
- Each scene MUST have at least {MIN_SHOTS_PER_SCENE or 1} shots (different camera angles)
"""
    else:
        # Use shots_per_scene target
        if shots_per_scene > 0:
            estimated_total = scene_count * shots_per_scene
            max_shots_instruction = f"""
IMPORTANT SHOT DISTRIBUTION:
- Generate approximately {shots_per_scene}-{min(shots_per_scene + 2, MAX_SHOTS_PER_SCENE) if MAX_SHOTS_PER_SCENE > 0 else shots_per_scene + 2} shots for EACH of the {scene_count} scenes
- Estimated total: {estimated_total} shots
- Each scene MUST have at least {MIN_SHOTS_PER_SCENE or 1} shots with different camera angles
"""
            if MAX_SHOTS_PER_SCENE > 0:
                max_shots_instruction += f"- Maximum: {MAX_SHOTS_PER_SCENE} shots per scene (to prevent over-generation)\n"
        else:
            max_shots_instruction = f"""
IMPORTANT SHOT DISTRIBUTION:
- Generate as many shots as necessary for EACH of the {scene_count} scenes to properly and visually tell the story.
- DO NOT artificially limit the number of shots. If a scene is complex or long, generate many shots for it.
- Each scene MUST have at least 1 shot with different camera angles.
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

            if has_scene_lengths:
                # Extract the subset of the scene_shot_plan for this batch
                batch_plan = [p for p in scene_shot_plan if start_idx <= p['scene_idx'] < end_idx]
                batch_max_total = sum(p['shots'] for p in batch_plan)
                
                # Format scene shot plan for LLM instruction
                batch_scene_plan_text = "\n".join([
                    f"  Scene {p['scene_idx']}: {p['shots']} shots ({p['duration']}s)"
                    for p in batch_plan
                ])

                batch_instruction = f"""
CRITICAL SHOT REQUIREMENTS FOR THIS BATCH:
- You MUST generate exactly {batch_max_total} shots for this batch
- This batch contains {len(scenes_batch)} scene(s)
Generate the following exact number of shots for each scene based on its duration:
{batch_scene_plan_text}

IMPORTANT: Follow the exact shot count specified for each scene above.
"""
            else:
                # Adjust max_shots for this batch
                batch_max_shots = None
                if max_shots:
                    batch_max_shots = max_shots // total_batches

                # Build batch-specific instruction
                batch_max_total = batch_max_shots or len(scenes_batch) * shots_per_scene
                scenes_in_batch = len(scenes_batch)

                if shots_per_scene > 0:
                    shots_per_batch_scene = max(MIN_SHOTS_PER_SCENE or 1, batch_max_total // scenes_in_batch) if batch_max_total else shots_per_scene
                    batch_instruction = f"""
CRITICAL SHOT REQUIREMENTS:
- You MUST generate exactly {batch_max_total} shots for this batch
- This batch contains {scenes_in_batch} scene(s)
- For EACH scene in this batch, generate {shots_per_batch_scene}-{shots_per_batch_scene + 2} unique shots with different camera angles
- Each scene MUST have at least {MIN_SHOTS_PER_SCENE or 1} shots (different angles: wide shot, close-up, detail, etc.)
"""
                else:
                    batch_instruction = f"""
CRITICAL SHOT REQUIREMENTS:
- This batch contains {scenes_in_batch} scene(s)
- Generate as many shots as necessary for each scene to properly tell the story visually.
- Each scene MUST have at least 1 shot.
"""

            batches.append({
                'scenes_batch': scenes_batch,
                'batch_num': batch_num + 1,
                'total_batches': total_batches,
                'max_shots_instruction': batch_instruction,
                'shots_agent': shots_agent,
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
                    shots_agent=batch_data['shots_agent']
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
                    shots_agent=batch_data['shots_agent']
                )

                # Add batch number and ensure scene_index is present
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

        # Inject stable UUIDs and correct indices
        for i, shot in enumerate(all_shots):
            shot['id'] = uuid.uuid4().hex[:8]
            shot['index'] = i + 1

        return all_shots

    # Single batch processing (original logic)
    user_input = f"{scene_graph_with_indices}{max_shots_instruction}{SHOT_DURATION_INSTRUCTION}{SUB_SHOT_INSTRUCTION}{VIDEO_PROMPT_TIMING_INSTRUCTION}"

    # Try to use agent prompts
    try:
        # Load shots agent prompt
        image_prompt = load_agent_prompt("shots", user_input, shots_agent)

        # Get the response
        provider = get_provider()
        response = provider.ask(image_prompt, response_format="application/json")
        shots = extract_and_repair_json(response)

        validate_and_repair_shots(shots, shots_agent)

        # Ensure shots is a list
        if isinstance(shots, dict):
            # Check for common wrappers like {"shots": [...]}
            for val in shots.values():
                if isinstance(val, list):
                    shots = val
                    break
            else:
                shots = [shots]  # Wrap single object in list
        elif not isinstance(shots, list):
            shots = []

        # The LLM may echo a wrong scene_id (often 0); repair against the
        # scenes this plan actually received
        repair_batch_scene_ids(shots, scenes, 1, 1)

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

        # Inject stable UUIDs and correct indices
        for i, shot in enumerate(shots):
            shot['id'] = uuid.uuid4().hex[:8]
            shot['index'] = i + 1
            # scene_id is repaired against the input scenes by repair_batch_scene_ids

        return shots

    except (FileNotFoundError, ValueError):
        # Fall back to legacy prompt if agent not found
        print(f"[WARN] Shots agent '{shots_agent}' not found, using legacy prompt")
        prompt = f"""
Create cinematic shots for WAN 2.2.{max_shots_instruction}

Return JSON list (each shot):
[
  {{
   "scene_index": 0,
   "duration": 5,
   "image_prompt":"",
   "motion_prompt":"",
   "video_prompt":"",
   "soundfx_prompt":"",
   "camera":"slow pan | dolly | static | orbit | zoom | tracking | drone | arc | walk | fpv | dronedive | bullettime "
  }}
]

{SHOT_DURATION_INSTRUCTION}
The "video_prompt" of each shot is a detailed timestamped MiniMax H3 I2VA prompt: first-frame instruction line ("For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced."), then "integrated_multimodal_description:" with [Shot 1] (no timestamp; clips of 6 seconds or more should continue with [Shot 2], [Shot 3] sub-shots at strictly increasing cut times inside the clip duration), then "overall_soundscape:" (1-4 sentences) and "non_diegetic_music:" (1-3 sentences or N/A).

SCENES:
{scene_graph_with_indices}
"""
        provider = get_provider()
        response = provider.ask(prompt, response_format="application/json")
        shots = extract_and_repair_json(response)
        validate_and_repair_shots(shots, shots_agent)

        # Ensure shots is a list
        if isinstance(shots, dict):
            for val in shots.values():
                if isinstance(val, list):
                    shots = val
                    break
            else:
                shots = [shots]
        elif not isinstance(shots, list):
            shots = []

        # The LLM may echo a wrong scene_id (often 0); repair against the
        # scenes this plan actually received
        repair_batch_scene_ids(shots, scenes, 1, 1)

        # Enforce max_shots limit if specified
        if max_shots and len(shots) > max_shots:
            print(f"[INFO] Generated {len(shots)} shots, limiting to {max_shots}")
            shots = shots[:max_shots]

        # Inject stable UUIDs and correct indices
        for i, shot in enumerate(shots):
            shot['id'] = uuid.uuid4().hex[:8]
            shot['index'] = i + 1

        return shots