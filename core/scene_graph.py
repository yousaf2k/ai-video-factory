import json
import logging

logger = logging.getLogger(__name__)

def build_scene_graph(story_json):

    # Handle both JSON string and parsed dict
    if isinstance(story_json, str):
        story = json.loads(story_json)
    else:
        story = story_json

    # Debug logging
    logger.debug(f"build_scene_graph: story type = {type(story)}")
    if isinstance(story, dict):
        logger.debug(f"build_scene_graph: story keys = {list(story.keys())}")
    elif isinstance(story, list):
        logger.debug(f"build_scene_graph: story is list with {len(story)} items")
        if len(story) > 0:
            logger.debug(f"build_scene_graph: first item type = {type(story[0])}, keys = {list(story[0].keys()) if isinstance(story[0], dict) else 'N/A'}")

    # Handle case where LLM returns an array of scenes directly (without wrapping in object)
    if isinstance(story, list):
        if len(story) == 0:
            return []
        # Check if first item has scene structure (location, action, etc.)
        # If so, treat entire list as scenes
        if len(story) > 0 and isinstance(story[0], dict):
            if "location" in story[0] or "action" in story[0]:
                # This is a list of scenes, use it directly
                scenes = story
            elif "scenes" in story[0]:
                # List contains story object with scenes key
                story = story[0]
                scenes = story["scenes"]
            else:
                # Unknown format, try to use as scenes
                scenes = story
        else:
            scenes = story
    else:
        # Story is an object with scenes key
        scenes = story.get("scenes", [])

    graph = []

    for i, s in enumerate(scenes):
        # Handle both dict scenes and string scenes
        if isinstance(s, str):
            # Skip string entries or convert to minimal scene
            logger.warning(f"Scene {i} is a string, skipping: {s[:50]}...")
            continue
        if not isinstance(s, dict):
            logger.warning(f"Scene {i} is not a dict (type: {type(s)}), skipping")
            continue

        # Validate required fields
        if not any(key in s for key in ["location", "action", "emotion", "characters"]):
            logger.warning(f"Scene {i} missing required fields, skipping. Available keys: {list(s.keys())}")
            continue

        graph.append({
            "id": i,
            "location": s.get("location", ""),
            "action": s.get("action", ""),
            "emotion": s.get("emotion", ""),
            "characters": s.get("characters", ""),
            "narration": s.get("narration", "")  # Include narration from story
        })

    logger.info(f"Built scene graph with {len(graph)} scenes from {len(scenes)} input scenes")
    return graph