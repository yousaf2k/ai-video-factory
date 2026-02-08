from core.gemini_engine import ask

def build_story(idea):

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