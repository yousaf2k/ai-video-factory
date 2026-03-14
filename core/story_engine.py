"""
Story Engine - Generate cinematic stories from ideas using LLM agents.
"""
from core.llm_engine import get_provider
from core.agent_loader import load_agent_prompt
from core.logger_config import setup_agent_logger
from web_ui.backend.models.story import ProjectType
import config
import json
import uuid


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

    # Adjust each scene's duration proportionally and ensure scene_id
    adjusted_scenes = []
    for i, scene in enumerate(scenes):
        adjusted_scene = scene.copy()
        # Ensure scene_id exists
        if 'scene_id' not in adjusted_scene:
            adjusted_scene['scene_id'] = i
            
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


def build_story(idea, agent_name="default", target_length=None, aspect_ratio="16:9"):
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
        aspect_ratio: Video aspect ratio (default: "16:9")

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

            # Add aspect_ratio to story dict
            story['aspect_ratio'] = aspect_ratio

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

            # Add aspect_ratio to story dict
            story['aspect_ratio'] = aspect_ratio

            # Ensure scene_id in all scenes
            if 'scenes' in story:
                for i, scene in enumerate(story['scenes']):
                    if 'scene_id' not in scene:
                        scene['scene_id'] = i

            story_json_str = json.dumps(story, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            logger.warning("Failed to parse story JSON for formatting")

    return story_json_str


def build_story_then_vs_now(movie_name: str, target_length: int = None, aspect_ratio: str = "16:9") -> str:
    """
    Build a ThenVsNow story from a movie name.
    Generates both story and shots directly (bypasses shot planner).

    Args:
        movie_name: The movie name to generate a reunion story for
        target_length: Target video length in seconds (optional)
        aspect_ratio: Video aspect ratio (default: "16:9")

    Returns:
        JSON string with story structure including shots
    """
    provider = get_provider()

    # Load the then_vs_now agent
    prompt = load_agent_prompt("story", movie_name, "then_vs_now")
    if target_length:
        prompt = prompt.replace("{VIDEO_LENGTH}", str(int(target_length)))

    # Generate story
    logger.info(f"Generating ThenVsNow story for movie: {movie_name}")
    print(f"[INFO] Generating ThenVsNow story for movie: {movie_name}")

    story_json_str = provider.ask(prompt, response_format="application/json")
    story = json.loads(story_json_str)

    # Ensure project_type is set
    story['project_type'] = ProjectType.THEN_VS_NOW

    # Add aspect_ratio to story
    story['aspect_ratio'] = aspect_ratio

    # CRITICAL: Normalize scene_id to array indices BEFORE generating shots
    # This ensures shots' scene_id values match the scenes array indices
    if 'scenes' in story:
        for i, scene in enumerate(story['scenes']):
            scene['scene_id'] = i

    # Generate shots directly from story
    shots = generate_shots_from_then_vs_now_story(story)
    story['shots'] = shots

    # Validate durations
    if target_length:
        story['total_duration'] = int(target_length)
        _, _, _, adjusted_story = validate_and_adjust_scene_durations(
            story, target_length, config.SCENE_DURATION_TOLERANCE
        )
        story_json_str = json.dumps(adjusted_story, ensure_ascii=False, indent=2)
    else:
        story_json_str = json.dumps(story, ensure_ascii=False, indent=2)

    logger.info(f"Generated {len(shots)} shots for {len(story.get('characters', []))} characters")
    return story_json_str


def generate_shots_from_then_vs_now_story(story: dict) -> list:
    """
    Generate FLFI2V shots directly from a ThenVsNow story.
    Each character gets 1 shot with BOTH Meeting and Departure videos.

    Args:
        story: Story dict with characters and scenes

    Returns:
        List of shot dicts with FLFI2V structure
    """
    characters = story.get('characters', [])
    scenes = story.get('scenes', [])

    # Build scene lookup
    scenes_by_id = {scene.get('scene_id', 0): scene for scene in scenes}

    # Group characters by scene_id
    characters_by_scene = {}
    for char in characters:
        scene_id = char.get('scene_id', 0)  # Use character's scene_id
        if scene_id not in characters_by_scene:
            characters_by_scene[scene_id] = []
        characters_by_scene[scene_id].append(char)

    shots = []
    shot_index = 1

    # Generate shots in scene order
    for scene_id in sorted(characters_by_scene.keys()):
        scene = scenes_by_id.get(scene_id, {})
        scene_name = scene.get('scene_name', f'Scene {scene_id}')
        scene_characters = characters_by_scene[scene_id]

        for char_idx, character in enumerate(scene_characters):
            # Single shot per character with BOTH meeting and departure prompts
            shot = {
                'id': uuid.uuid4().hex[:8],
                'index': shot_index,
                'is_flfi2v': True,
                'character_id': f"char_{scene_id:02d}_{char_idx:02d}",
                'character_name': character.get('name', ''),
                'scene_id': scene_id,
                'scene_name': scene_name,
                'order_in_scene': char_idx,
                'then_image_prompt': character.get('then_prompt', ''),
                'now_image_prompt': character.get('now_prompt', ''),
                'meeting_video_prompt': character.get('meeting_prompt', ''),
                'departure_video_prompt': character.get('departure_prompt', ''),
                'camera': 'tracking',
                'narration': '',
                'batch_number': 1,
                # Standard fields for compatibility
                'image_prompt': character.get('now_prompt', ''),
                'motion_prompt': character.get('meeting_prompt', ''),  # Default to meeting
                'image_generated': False,
                'image_path': None,
                'image_paths': [],
                'video_rendered': False,
                'video_path': None,
                'video_paths': []
            }
            shots.append(shot)
            shot_index += 1

    logger.info(f"Generated {len(shots)} shots for {len(characters)} characters (1 shot per character with both meeting and departure prompts)")
    return shots
