"""
Image Generation Module - Supports both Gemini and ComfyUI
Generates images from prompts and saves them to organized directory structure

Now supports generating multiple images per shot with different random seeds.
Also supports camera trigger keywords for LoRA activation.
"""
import google.genai as genai
from google.genai import types
import config
import os
import random
from pathlib import Path
from core.logger_config import get_logger


# Get logger for image generation
logger = get_logger(__name__)


def generate_image_gemini(prompt: str, output_path: str, aspect_ratio: str = None, resolution: str = None, seed: int = None) -> str:
    """
    Generate a single image from prompt using Gemini.

    Args:
        prompt: Text description of the image to generate
        output_path: Full path where the image will be saved
        aspect_ratio: Optional. Override default aspect ratio from config
        resolution: Optional. Override default resolution from config
        seed: Optional random seed for reproducibility (not used by Gemini, but kept for API consistency)

    Returns:
        Path to the generated image file, or None if failed
    """
    logger.info(f"Generating image (Gemini): {output_path}")
    logger.debug(f"  Prompt: {prompt[:100]}...")
    logger.debug(f"  Aspect ratio: {aspect_ratio or config.IMAGE_ASPECT_RATIO}")
    logger.debug(f"  Resolution: {resolution or config.IMAGE_RESOLUTION}")
    logger.debug(f"  Seed: {seed}")

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

        # Log success with file size
        file_size = os.path.getsize(output_path)
        logger.info(f"Generated (Gemini): {output_path} ({file_size:,} bytes)")
        print(f"[PASS] Generated (Gemini): {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Failed to generate image (Gemini): {e}")
        print(f"[FAIL] Failed to generate image: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_image(prompt: str, output_path: str, aspect_ratio: str = None, resolution: str = None, mode: str = None, seed: int = None, workflow_name: str = None) -> str:
    """
    Generate a single image using the configured mode (Gemini or ComfyUI).

    Args:
        prompt: Text description of the image to generate
        output_path: Full path where the image will be saved
        aspect_ratio: Optional. Override default aspect ratio
        resolution: Optional. Override default resolution
        mode: Force a specific mode ("gemini" or "comfyui"), None to use config default
        seed: Optional random seed for reproducibility
        workflow_name: Optional ComfyUI workflow name from IMAGE_WORKFLOWS (only for comfyui mode)

    Returns:
        Path to the generated image file, or None if failed
    """
    # Use config mode if not specified
    if mode is None:
        mode = config.IMAGE_GENERATION_MODE

    if mode == "comfyui":
        from core.comfyui_image_generator import generate_image_comfyui
        return generate_image_comfyui(prompt, output_path, seed=seed, workflow_name=workflow_name)
    else:
        return generate_image_gemini(prompt, output_path, aspect_ratio, resolution, seed)


def generate_image_variations(prompt: str, output_dir: str, count: int = 1, mode: str = None, negative_prompt: str = "", shot_idx: int = 1, workflow_name: str = None) -> list:
    """
    Generate multiple variations of an image with different random seeds.

    Args:
        prompt: Text description of the image to generate
        output_dir: Directory to save generated images
        count: Number of variations to generate
        mode: Image generation mode ("gemini" or "comfyui")
        negative_prompt: Negative prompt for ComfyUI mode
        shot_idx: Shot index for naming (e.g., shot_001_001.png)
        workflow_name: ComfyUI workflow name from IMAGE_WORKFLOWS (only for comfyui mode)

    Returns:
        List of generated image paths
    """
    os.makedirs(output_dir, exist_ok=True)
    generated_paths = []

    for variation_idx in range(count):
        # Generate random seed for this variation
        seed = random.randint(0, 2**32 - 1)

        # Generate filename: shot_001_001.png, shot_001_002.png, etc.
        filename = f"shot_{shot_idx:03d}_{variation_idx + 1:03d}.png"
        output_path = os.path.join(output_dir, filename)

        print(f"  [{variation_idx + 1}/{count}] Generating variation (seed: {seed})...")

        # Generate image
        image_path = generate_image(prompt, output_path, mode=mode, seed=seed, workflow_name=workflow_name)

        if image_path:
            generated_paths.append(image_path)
        else:
            print(f"  [FAIL] Variation {variation_idx + 1} failed")

    return generated_paths


def generate_images_for_shots(shots: list, output_dir: str, mode: str = None, negative_prompt: str = "", images_per_shot: int = 1, workflow_name: str = None) -> list:
    """
    Generate images for all shots in the list, with multiple variations per shot.

    Args:
        shots: List of shot dictionaries, each containing 'image_prompt'
        output_dir: Directory to save generated images
        mode: Image generation mode ("gemini" or "comfyui"), None to use config default
        negative_prompt: Negative prompt for ComfyUI mode
        images_per_shot: Number of images to generate per shot (default: 1)

    Returns:
        Updated list of shots with 'image_paths' field added to each shot
    """
    # Use config mode if not specified
    if mode is None:
        mode = config.IMAGE_GENERATION_MODE

    mode_name = "Gemini" if mode == "gemini" else "ComfyUI"
    total_images = len(shots) * images_per_shot
    print(f"\nGenerating {total_images} images ({images_per_shot} per shot) using {mode_name}...")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    for shot_idx, shot in enumerate(shots, start=1):
        # Use sequential index (1-110) for all shots
        image_prompt = shot.get('image_prompt', '')

        if not image_prompt:
            print(f"[SKIP] Shot {shot_idx}: No image_prompt found, skipping")
            shot['image_paths'] = []
            continue

        print(f"\n[Shot {shot_idx}/{len(shots)}] {image_prompt[:80]}...")

        # Generate multiple variations
        image_paths = generate_image_variations(
            prompt=image_prompt,
            output_dir=output_dir,
            count=images_per_shot,
            mode=mode,
            negative_prompt=negative_prompt,
            shot_idx=shot_idx,
            workflow_name=workflow_name
        )

        # Store all image paths (primary image and variations)
        shot['image_paths'] = image_paths

        # For backward compatibility, also store primary image_path
        shot['image_path'] = image_paths[0] if image_paths else None

        if image_paths:
            print(f"  [PASS] Generated {len(image_paths)} variation(s) for shot {shot_idx}")
        else:
            print(f"  [FAIL] All variations failed for shot {shot_idx}")

    print(f"\n[INFO] Image generation complete. Images saved to: {output_dir}")
    return shots
