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
    Performs a two-pass generation:
    1. Generates a master script (story.json base)
    2. Breaks the master script down into detailed scenes.

    Args:
        idea: The video idea/concept
        agent_name: Name of story agent to use (default: "default")
        target_length: Target video length in seconds (optional).
                      Injected via {VIDEO_LENGTH} placeholder in agent prompts.

    Returns:
        JSON string with story structure including scenes
    """
    provider = get_provider()

    # Pass 1: Generate Master Script
    try:
        master_prompt = load_agent_prompt("story", idea, "master_script")
        if target_length:
            master_prompt = master_prompt.replace("{VIDEO_LENGTH}", str(int(target_length)))
            word_count = int(target_length * 2.5)
            master_prompt = master_prompt.replace("{MASTER_WORD_COUNT}", str(word_count))
            logger.info(f"Master script requested: {int(target_length)}s (~{word_count} words)")
            print(f"[INFO] Master script requested: {int(target_length)}s (~{word_count} words)")
    except (FileNotFoundError, ValueError):
        logger.error("Master script agent (master_script.md) not found.")
        print("[WARN] Master script agent not found. Generating basic story instead.")
        master_prompt = f"Write a full voice-over script for this idea: {idea}\n\nReturn JSON:\n{{\n 'title': '',\n 'style': '',\n 'master_script': ''\n}}"

    print("\n[STORY] Pass 1: Generating Master Script...")
    master_json_str = provider.ask(master_prompt, response_format="application/json")
    
    try:
        master_data = json.loads(master_json_str)
        master_script = master_data.get("master_script", "")
    except json.JSONDecodeError:
        logger.warning("Failed to parse master script JSON. Proceeding without master script data.")
        master_script = idea
        master_data = {"title": "Generated Story", "style": "cinematic", "master_script": master_script}

    # Pass 2: Break down into scenes
    print("\n[STORY] Pass 2: Generating Scenes from Master Script...")
    scene_idea = f"IDEA: {idea}\n\nMASTER SCRIPT TO BREAK DOWN INTO SCENES:\n{master_script}"
    
    try:
        # Try to use agent prompt
        prompt = load_agent_prompt("story", scene_idea, agent_name)

        # Inject video length context if agent supports it
        if target_length and "{VIDEO_LENGTH}" in prompt:
            prompt = prompt.replace("{VIDEO_LENGTH}", str(int(target_length)))
            logger.info(f"Video length context injected into scene gen: {int(target_length)}s")

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
     "emotion":"",
     "narration":"",
     "scene_duration":15
   }}
 ]
}}

{scene_idea}
"""

    story_json_str = provider.ask(prompt, response_format="application/json")

    # Merge, Validate, and Format
    if target_length:
        try:
            story = json.loads(story_json_str)
            # Add total_duration to story dict
            story['total_duration'] = int(target_length)
            
            # Inject master data
            story['title'] = master_data.get('title', story.get('title', 'Video'))
            story['style'] = master_data.get('style', story.get('style', 'cinematic'))
            story['master_script'] = master_script
            
            is_valid, actual_total, diff, adjusted_story = validate_and_adjust_scene_durations(
                story, target_length, config.SCENE_DURATION_TOLERANCE
            )
            story_json_str = json.dumps(adjusted_story, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            logger.warning("Failed to parse story JSON for validation, skipping duration check")
    else:
        # Format JSON with proper indentation even when no target_length
        try:
            story = json.loads(story_json_str)
            story['title'] = master_data.get('title', story.get('title', 'Video'))
            story['style'] = master_data.get('style', story.get('style', 'cinematic'))
            story['master_script'] = master_script
            story_json_str = json.dumps(story, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            logger.warning("Failed to parse story JSON for formatting")

    return story_json_str
