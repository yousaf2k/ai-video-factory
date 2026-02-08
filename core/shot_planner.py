from core.gemini_engine import ask
import json

def plan_shots(scene_graph, max_shots=None):

    max_shots_instruction = ""
    if max_shots:
        max_shots_instruction = f"\nIMPORTANT: Create exactly {max_shots} shots maximum."

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