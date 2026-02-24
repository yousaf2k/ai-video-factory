import json

def build_scene_graph(story_json):

    # Handle both JSON string and parsed dict
    if isinstance(story_json, str):
        story = json.loads(story_json)
    else:
        story = story_json

    # Handle case where LLM returns an array containing the story object
    if isinstance(story, list):
        if len(story) > 0:
            story = story[0]
        else:
            return []

    graph = []

    for i, s in enumerate(story["scenes"]):
        graph.append({
            "id": i,
            "location": s["location"],
            "action": s["action"],
            "emotion": s["emotion"],
            "characters": s["characters"],
            "narration": s.get("narration", "")  # Include narration from story
        })

    return graph