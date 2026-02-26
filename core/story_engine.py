"""
Story Engine - Generate cinematic stories from ideas using LLM agents.
"""
from core.llm_engine import get_provider
from core.agent_loader import load_agent_prompt
from core.logger_config import setup_agent_logger
import config
import json


# Get logger for story engine operations
logger = setup_agent_logger(__name__)


def validate_and_adjust_scene_durations(story, target_length, tolerance=0.15):
    """
    Validate scene durations sum to approximately target_length.
    Auto-correct if outside tolerance.

    Args:
        story: Story dict with 'scenes' list, or list of scenes directly
        target_length: Target total duration in seconds
        tolerance: Acceptable deviation as fraction (e.g., 0.15 = 15%)

    Returns:
        Tuple: (is_valid, actual_total, difference, adjusted_story)
    """
    # Handle both dict and list inputs
    if isinstance(story, list):
        scenes = story
        story_is_dict = False
    else:
        scenes = story.get('scenes', [])
        story_is_dict = True

    if not scenes:
        return True, 0, 0, story

    # Check if scenes have scene_duration field
    has_durations = any('scene_duration' in s for s in scenes)
    if not has_durations:
        return True, 0, 0, story

    # Calculate actual total duration
    actual_total = sum(s.get('scene_duration', 0) for s in scenes)
    difference = actual_total - target_length
    deviation_ratio = abs(difference) / target_length if target_length > 0 else 0

    # Check if within tolerance
    if deviation_ratio <= tolerance:
        logger.info(f"Scene durations validation passed: {actual_total}s (target: {target_length}s, deviation: {deviation_ratio*100:.1f}%)")
        return True, actual_total, difference, story

    # Outside tolerance - apply proportional correction
    logger.warning(f"Scene duration mismatch: {actual_total}s vs target {target_length}s (deviation: {deviation_ratio*100:.1f}%)")
    print(f"[WARN] Scene duration mismatch: {actual_total}s vs target {target_length}s (deviation: {deviation_ratio*100:.1f}%)")

    # Calculate adjustment factor
    adjustment_factor = target_length / actual_total if actual_total > 0 else 1.0

    # Adjust each scene's duration proportionally
    adjusted_scenes = []
    for scene in scenes:
        adjusted_scene = scene.copy()
        if 'scene_duration' in scene:
            original_duration = scene['scene_duration']
            adjusted_duration = max(config.MIN_SCENE_LENGTH, int(original_duration * adjustment_factor))
            adjusted_scene['scene_duration'] = adjusted_duration
            logger.debug(f"Adjusted scene duration: {original_duration}s -> {adjusted_duration}s")
        adjusted_scenes.append(adjusted_scene)

    # Return in same format as input
    if story_is_dict:
        adjusted_story = story.copy()
        adjusted_story['scenes'] = adjusted_scenes
    else:
        adjusted_story = adjusted_scenes

    new_total = sum(s.get('scene_duration', 0) for s in adjusted_scenes)
    logger.info(f"Auto-corrected scene durations: {actual_total}s -> {new_total}s")
    print(f"[INFO] Auto-corrected scene durations: {actual_total}s -> {new_total}s")

    return False, actual_total, difference, adjusted_story


def build_story(idea, agent_name="default", target_length=None):
    """
    Build a cinematic story from an idea using the specified agent.

    Args:
        idea: The video idea/concept
        agent_name: Name of story agent to use (default: "default")
                   Available: default, dramatic, documentary, time_traveler,
                              netflix_documentary, youtube_documentary,
                              prehistoric_dinosaur, prehistoric_pov
        target_length: Target video length in seconds (optional).
                      Injected via {VIDEO_LENGTH} placeholder in agent prompts.

    Returns:
        JSON string with story structure
    """
    try:
        # Try to use agent prompt
        prompt = load_agent_prompt("story", idea, agent_name)

        # Inject video length context if agent supports it
        if target_length and "{VIDEO_LENGTH}" in prompt:
            prompt = prompt.replace("{VIDEO_LENGTH}", str(int(target_length)))
            logger.info(f"Video length context injected: {int(target_length)}s")
            print(f"[INFO] Video length context: {int(target_length)}s")

    except (FileNotFoundError, ValueError):
        # Fall back to legacy prompt if agent not found
        print(f"[WARN] Story agent '{agent_name}' not found, using legacy prompt")
        prompt = f"""
Expand into cinematic narrative.

Return JSON:

{{
 "title":"",
 "style":"ultra cinematic documentary",
 "scenes":[
   {{
     "location":"",
     "characters":"",
     "action":"",
     "emotion":""
   }}
 ]
}}

IDEA:
{idea}
"""

    provider = get_provider()
    story_json = provider.ask(prompt, response_format="application/json")

    # Validate scene durations if target_length provided
    if target_length:
        try:
            story = json.loads(story_json)
            is_valid, actual_total, diff, adjusted_story = validate_and_adjust_scene_durations(
                story, target_length, config.SCENE_DURATION_TOLERANCE
            )
            story_json = json.dumps(adjusted_story, ensure_ascii=False)
        except json.JSONDecodeError:
            logger.warning("Failed to parse story JSON for validation, skipping duration check")

    return story_json
