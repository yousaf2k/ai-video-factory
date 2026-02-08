from openai import OpenAI
import config

client = OpenAI(api_key=config.OPENAI_API_KEY)

def ask(prompt: str):
    r = client.responses.create(
        model=config.MODEL,
        input=prompt
    )
    return r.output_text