"""
Image Generation Module - Supports both Gemini and ComfyUI
Generates images from prompts and saves them to organized directory structure

Now supports generating multiple images per shot with different random seeds.
Also supports camera trigger keywords for LoRA activation.

Features automatic retry mechanism for failed generations.
"""
import google.genai as genai
from google.genai import types
import config
import os
import random
import time
from pathlib import Path
from core.logger_config import get_logger
from typing import Optional, Tuple


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


def generate_images_for_shots(
    shots: list,
    output_dir: str,
    mode: str = None,
    negative_prompt: str = "",
    images_per_shot: int = 1,
    workflow_name: str = None,
    progress_callback=None,
    retry_tracker=None
) -> Tuple[list, Optional['RetryTracker']]:
    """
    Generate images for all shots in the list, with multiple variations per shot.
    Implements automatic retry mechanism for failed generations.

    Args:
        shots: List of shot dictionaries, each containing 'image_prompt'
        output_dir: Directory to save generated images
        mode: Image generation mode ("gemini" or "comfyui"), None to use config default
        negative_prompt: Negative prompt for ComfyUI mode
        images_per_shot: Number of images to generate per shot (default: 1)
        workflow_name: Workflow name for ComfyUI mode
        progress_callback: Optional callback function(shot_idx, image_path) called after each image generation
        retry_tracker: Optional RetryTracker instance for tracking failures

    Returns:
        Tuple of (shots, retry_tracker):
            - Updated list of shots with 'image_paths' field added to each shot
            - RetryTracker instance with statistics (None if retry_tracker was None)
    """
    # Import RetryTracker here to avoid circular dependency
    from core.retry_tracker import RetryTracker

    # Initialize retry tracker if not provided
    if retry_tracker is None:
        retry_tracker = None  # Backward compatibility: don't create tracker if not requested
        track_retries = False
    else:
        track_retries = True

    # Use config mode if not specified
    if mode is None:
        mode = config.IMAGE_GENERATION_MODE

    mode_name = "Gemini" if mode == "gemini" else "ComfyUI"
    total_images = len(shots) * images_per_shot

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # =========================================================================
    # PHASE 1: Initial Generation
    # =========================================================================
    print(f"\n[PHASE 1] Initial image generation...")
    print(f"Generating {total_images} images ({images_per_shot} per shot) using {mode_name}...")

    if track_retries:
        retry_tracker.summary.total_variations_attempted = total_images

    for shot in shots:
        # Use the shot's stored index field for consistency
        shot_idx = shot.get('index', shots.index(shot) + 1)
        image_prompt = shot.get('image_prompt', '')

        if not image_prompt:
            print(f"[SKIP] Shot {shot_idx}: No image_prompt found, skipping")
            shot['image_paths'] = []
            continue

        print(f"\n[Shot {shot_idx}/{len(shots)}] Generating...")
        print(f"  Prompt: {image_prompt[:80]}...")

        # Generate multiple variations
        image_paths = []
        for variation_idx in range(images_per_shot):
            # Generate random seed for this variation
            seed = random.randint(0, 2**32 - 1)

            # Generate filename: shot_001_001.png, shot_001_002.png, etc.
            filename = f"shot_{shot_idx:03d}_{variation_idx + 1:03d}.png"
            output_path = os.path.join(output_dir, filename)

            print(f"  [{variation_idx + 1}/{images_per_shot}] Generating variation (seed: {seed})...")

            # Generate image
            image_path = generate_image(
                prompt=image_prompt,
                output_path=output_path,
                mode=mode,
                seed=seed,
                workflow_name=workflow_name
            )

            if image_path:
                image_paths.append(image_path)
                print(f"    [PASS] Variation {variation_idx + 1} succeeded")
                if track_retries:
                    retry_tracker.record_success(shot_idx, variation_idx)
                if progress_callback:
                    progress_callback(shot_idx, image_path)
            else:
                print(f"    [FAIL] Variation {variation_idx + 1} failed - will retry later")
                if track_retries:
                    retry_tracker.record_failure(shot_idx, variation_idx, image_prompt)
                    retry_tracker.summary.total_failed_initial += 1

        # Store all image paths (primary image and variations)
        shot['image_paths'] = image_paths

        # For backward compatibility, also store primary image_path
        shot['image_path'] = image_paths[0] if image_paths else None

        if image_paths:
            print(f"  [SUMMARY] Generated {len(image_paths)}/{images_per_shot} variation(s) for shot {shot_idx}")
        else:
            print(f"  [SUMMARY] All variations failed for shot {shot_idx}")

    # =========================================================================
    # PHASE 2: Retry Loop
    # =========================================================================
    if track_retries:
        pending_retries = retry_tracker.get_pending_retries()

        if pending_retries:
            max_retry_rounds = config.IMAGE_GENERATION_MAX_RETRIES - 1  # -1 because initial was round 1

            for retry_round in range(1, max_retry_rounds + 1):
                pending_retries = retry_tracker.get_pending_retries()

                if not pending_retries:
                    # All retries succeeded!
                    break

                print(f"\n[PHASE 2.{retry_round}] Retry round {retry_round}/{max_retry_rounds}...")
                print(f"            {len(pending_retries)} variation(s) to retry")

                # Optional delay between retry rounds
                if retry_round > 1 and config.IMAGE_GENERATION_RETRY_DELAY > 0:
                    print(f"[DELAY] Waiting {config.IMAGE_GENERATION_RETRY_DELAY} seconds before retry...")
                    time.sleep(config.IMAGE_GENERATION_RETRY_DELAY)

                # Retry each failed variation
                for failed_var in pending_retries:
                    shot_idx = failed_var.shot_index
                    variation_idx = failed_var.variation_index

                    # Check if we should continue retrying
                    if not retry_tracker.increment_attempts(shot_idx, variation_idx):
                        # Max retries reached, mark as permanent failure
                        retry_tracker.mark_permanent_failure(shot_idx, variation_idx)
                        continue

                    attempt_num = failed_var.attempts_made + 1
                    print(f"  [Shot {shot_idx}] Retrying variation {variation_idx + 1} (attempt {attempt_num}/{config.IMAGE_GENERATION_MAX_RETRIES})...")

                    # Generate new random seed for retry
                    seed = random.randint(0, 2**32 - 1)
                    filename = f"shot_{shot_idx:03d}_{variation_idx + 1:03d}.png"
                    output_path = os.path.join(output_dir, filename)

                    # Retry image generation
                    image_path = generate_image(
                        prompt=failed_var.prompt,
                        output_path=output_path,
                        mode=mode,
                        seed=seed,
                        workflow_name=workflow_name
                    )

                    if image_path:
                        print(f"    [PASS] Retry succeeded")
                        retry_tracker.mark_success(shot_idx, variation_idx, image_path)

                        # Update the shot's image_paths list
                        for shot in shots:
                            if shot.get('index') == shot_idx:
                                # Ensure list is long enough
                                while len(shot.get('image_paths', [])) <= variation_idx:
                                    shot.setdefault('image_paths', []).append(None)
                                shot['image_paths'][variation_idx] = image_path
                                # Update primary image_path if this is the first variation
                                shot['image_path'] = shot['image_paths'][0]
                                break

                        if progress_callback:
                            progress_callback(shot_idx, image_path)
                    else:
                        print(f"    [FAIL] Retry attempt {attempt_num} failed")
                        # Variation remains in pending list for next round

                # Check if any retries remain
                pending_retries = retry_tracker.get_pending_retries()
                if not pending_retries:
                    print("\n[SUCCESS] All retries completed successfully!")
                    break

    # =========================================================================
    # PHASE 3: Summary
    # =========================================================================
    print(f"\n[INFO] Image generation complete. Images saved to: {output_dir}")

    if track_retries:
        retry_tracker.print_summary()

        # Final count of shots with images
        shots_with_images = [s for s in shots if s.get('image_path')]
        print(f"\n[FINAL] {len(shots_with_images)}/{len(shots)} shots have at least one image")

    return shots, retry_tracker
