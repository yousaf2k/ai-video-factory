"""
Shot Planner - Plan cinematic shots using LLM agents.
"""
from core.gemini_engine import ask
from core.agent_loader import load_agent_prompt
import json


def plan_shots(scene_graph, max_shots=None, image_agent="default", video_agent="default"):
    """
    Plan cinematic shots for WAN 2.2 video generation.

    Args:
        scene_graph: The scene graph JSON
        max_shots: Maximum number of shots to create (optional)
        image_agent: Name of the image prompt agent to use (default: "default")
                    Available: default, artistic
        video_agent: Name of the video motion agent to use (default: "default")
                    Available: default, cinematic

    Returns:
        List of shot dictionaries with image_prompt, motion_prompt, and camera
    """
    # Build input with scene info and max_shots instruction
    max_shots_instruction = ""
    if max_shots:
        max_shots_instruction = f"\nIMPORTANT: Create exactly {max_shots} shots maximum."

    user_input = f"{scene_graph}{max_shots_instruction}"

    # Try to use agent prompts
    try:
        # Load image agent prompt
        image_prompt = load_agent_prompt("image", user_input, image_agent)

        # Get the response
        response = ask(image_prompt, response_format="application/json")
        shots = json.loads(response)

        # Enforce max_shots limit if specified
        if max_shots and len(shots) > max_shots:
            print(f"[INFO] Generated {len(shots)} shots, limiting to {max_shots}")
            shots = shots[:max_shots]

        return shots

    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        # Fall back to legacy prompt
        print(f"[WARN] Image agent '{image_agent}' not found or error ({e}), using legacy prompt")

        prompt = f"""
Create cinematic shots for WAN 2.2.{max_shots_instruction}

Return JSON list:

[
 {{
   "image_prompt":"",
   "motion_prompt":"",
   "camera":"slow pan | dolly | static | orbit"
 }}
]

SCENES:
{scene_graph}
"""
        res = ask(prompt, response_format="application/json")
        shots = json.loads(res)

        # Enforce max_shots limit if specified
        if max_shots and len(shots) > max_shots:
            print(f"[INFO] Generated {len(shots)} shots, limiting to {max_shots}")
            shots = shots[:max_shots]

        return shots
