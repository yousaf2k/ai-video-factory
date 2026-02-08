"""
Gemini Text Generation Engine
Replaces OpenAI for all text generation tasks
"""
import google.genai as genai
from google.genai import types  # Recommended for configuration types
import config

# REMOVED: genai.configure() - This is for the legacy 'google-generativeai' library.

def ask(prompt: str, response_format: str = None) -> str:
    # Initialize client once with your API key
    # Use v1alpha for experimental models (like gemini-2.0-flash-exp)
    client = genai.Client(
        api_key=config.GEMINI_API_KEY,
        http_options={'api_version': 'v1alpha'} 
    )

    # Use types.GenerateContentConfig for robust configuration
    gen_config = None
    if response_format == "application/json":
        gen_config = types.GenerateContentConfig(
            response_mime_type="application/json"
        )

    response = client.models.generate_content(
        model=config.GEMINI_TEXT_MODEL,
        contents=prompt,
        config=gen_config
    )

    return response.text
