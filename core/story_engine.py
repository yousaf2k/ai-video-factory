"""
Story Engine - Generate cinematic stories from ideas using LLM agents.
"""
from core.gemini_engine import ask
from core.agent_loader import load_agent_prompt
import config


def build_story(idea, agent_name="default"):
    """
    Build a cinematic story from an idea using the specified agent.

    Args:
        idea: The video idea/concept
        agent_name: Name of the story agent to use (default: "default")
                   Available: default, dramatic, documentary

    Returns:
        JSON string with story structure
    """
    try:
        # Try to use agent prompt
        prompt = load_agent_prompt("story", idea, agent_name)
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

    return ask(prompt, response_format="application/json")
