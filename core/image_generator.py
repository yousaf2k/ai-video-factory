"""
Image Generation Module - Supports both Gemini and ComfyUI
Generates images from prompts and saves them to organized directory structure
"""
import google.genai as genai
from google.genai import types
import config
import os
from pathlib import Path


def generate_image_gemini(prompt: str, output_path: str, aspect_ratio: str = None, resolution: str = None) -> str:
    """
    Generate a single image from prompt using Gemini.

    Args:
        prompt: Text description of the image to generate
        output_path: Full path where the image will be saved
        aspect_ratio: Optional. Override default aspect ratio from config
        resolution: Optional. Override default resolution from config

    Returns:
        Path to the generated image file, or None if failed
    """
    try:
        # Initialize client with v1alpha for experimental models
        client = genai.Client(
            api_key=config.GEMINI_API_KEY,
            http_options={'api_version': 'v1alpha'}
        )

        # Use config defaults if not specified
        if aspect_ratio is None:
            aspect_ratio = config.IMAGE_ASPECT_RATIO
        if resolution is None:
            resolution = config.IMAGE_RESOLUTION

        # Generate image
        response = client.models.generate_content(
            model=config.GEMINI_IMAGE_MODEL,
            contents=prompt
        )

        # Save image to file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # The response contains the generated image data
        # Extract and save the image bytes
        image_bytes = None

        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]

            if hasattr(candidate, 'content'):
                content = candidate.content

                if hasattr(content, 'parts') and content.parts:
                    part = content.parts[0]

                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_bytes = part.inline_data.data
                    elif hasattr(part, 'raw_data'):
                        image_bytes = part.raw_data

        # Fallback: try to access response directly
        if not image_bytes:
            try:
                if hasattr(response, 'content'):
                    image_bytes = response.content
            except:
                pass

        if not image_bytes:
            print(f"[ERROR] Could not extract image data from response")
            return None

        # Write image to file
        with open(output_path, 'wb') as f:
            f.write(image_bytes)

        print(f"[PASS] Generated (Gemini): {output_path}")
        return output_path

    except Exception as e:
        print(f"[FAIL] Failed to generate image: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_image(prompt: str, output_path: str, aspect_ratio: str = None, resolution: str = None, mode: str = None) -> str:
    """
    Generate a single image using the configured mode (Gemini or ComfyUI).

    Args:
        prompt: Text description of the image to generate
        output_path: Full path where the image will be saved
        aspect_ratio: Optional. Override default aspect ratio
        resolution: Optional. Override default resolution
        mode: Force a specific mode ("gemini" or "comfyui"), None to use config default

    Returns:
        Path to the generated image file, or None if failed
    """
    # Use config mode if not specified
    if mode is None:
        mode = config.IMAGE_GENERATION_MODE

    if mode == "comfyui":
        from core.comfyui_image_generator import generate_image_comfyui
        return generate_image_comfyui(prompt, output_path)
    else:
        return generate_image_gemini(prompt, output_path, aspect_ratio, resolution)


def generate_images_for_shots(shots: list, output_dir: str, mode: str = None, negative_prompt: str = "") -> list:
    """
    Generate images for all shots in the list.

    Args:
        shots: List of shot dictionaries, each containing 'image_prompt'
        output_dir: Directory to save generated images
        mode: Image generation mode ("gemini" or "comfyui"), None to use config default
        negative_prompt: Negative prompt for ComfyUI mode

    Returns:
        Updated list of shots with 'image_path' field added to each shot
    """
    # Use config mode if not specified
    if mode is None:
        mode = config.IMAGE_GENERATION_MODE

    mode_name = "Gemini" if mode == "gemini" else "ComfyUI"
    print(f"\nGenerating {len(shots)} images using {mode_name}...")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    for idx, shot in enumerate(shots, start=1):
        # Generate filename: shot_001.png, shot_002.png, etc.
        filename = f"shot_{idx:03d}.png"
        output_path = os.path.join(output_dir, filename)

        # Generate image
        image_prompt = shot.get('image_prompt', '')
        if not image_prompt:
            print(f"[SKIP] Shot {idx}: No image_prompt found, skipping")
            shot['image_path'] = None
            continue

        print(f"[{idx}/{len(shots)}] Generating image: {image_prompt[:60]}...")

        if mode == "comfyui":
            from core.comfyui_image_generator import generate_image_comfyui
            image_path = generate_image_comfyui(image_prompt, output_path, negative_prompt)
        else:
            image_path = generate_image_gemini(image_prompt, output_path)

        # Add image_path to shot dictionary
        shot['image_path'] = image_path

    print(f"\n[INFO] Image generation complete. Images saved to: {output_dir}")
    return shots
