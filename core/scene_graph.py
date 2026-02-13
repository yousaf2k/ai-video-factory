import json

def build_scene_graph(story_json):

    # Handle both JSON string and parsed dict
    if isinstance(story_json, str):
        story = json.loads(story_json)
    else:
        story = story_json

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