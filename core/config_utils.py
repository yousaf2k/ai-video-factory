"""
Configuration utility functions for AI Film Studio System
"""


def calculate_max_shots_from_config(default_max_shots=0, target_video_length=None, default_shot_length=5):
    """
    Calculate maximum number of shots from configuration settings.

    Priority chain (highest to lowest):
    1. default_max_shots > 0: Manual override (exact shot count)
    2. target_video_length > 0: Automatic calculation (length / shot_length)
    3. None: No limit (story-driven generation)

    Args:
        default_max_shots: Maximum number of shots to generate (0 = no limit)
        target_video_length: Target total video length in seconds
        default_shot_length: Default duration per shot in seconds

    Returns:
        int or None: Maximum number of shots, or None for no limit

    Examples:
        calculate_max_shots_from_config(50, 600, 5)
        → Returns 50 (manual override takes priority)

        calculate_max_shots_from_config(0, 600, 5)
        → Returns 120 (automatic: 600s / 5s per shot)

        calculate_max_shots_from_config(0, 0, 5)
        → Returns None (no limit)
    """
    # Priority 1: Manual override in config
    if default_max_shots > 0:
        return default_max_shots

    # Priority 2: Automatic calculation from target video length
    if target_video_length and target_video_length > 0:
        return int(target_video_length / default_shot_length)

    # Priority 3: No limit
    return None


def calculate_image_dimensions(aspect_ratio="16:9", resolution="2048"):
    """
    Calculate image width and height from aspect ratio and resolution.

    Args:
        aspect_ratio: String like "16:9", "9:16", "1:1", "4:3", "3:4"
        resolution: String like "512", "1024", "2048" (width for landscape, height for portrait)

    Returns:
        Tuple of (width, height) as integers
    """
    res = int(resolution)

    # Parse aspect ratio
    if ':' in aspect_ratio:
        parts = aspect_ratio.split(':')
        ar_w = int(parts[0])
        ar_h = int(parts[1])
    else:
        # Default to 1:1 if format is wrong
        ar_w = 1
        ar_h = 1

    # Determine orientation and calculate dimensions
    if ar_w >= ar_h:
        # Landscape or square: resolution is width
        width = res
        height = int(res * ar_h / ar_w)
    else:
        # Portrait: resolution is height
        height = res
        width = int(res * ar_w / ar_h)

    # Ensure dimensions are multiples of 8 (required by most AI models)
    width = (width // 8) * 8
    height = (height // 8) * 8

    return width, height


def calculate_video_dimensions(aspect_ratio="16:9", resolution="1280"):
    """
    Calculate video width and height from aspect ratio and resolution.

    Args:
        aspect_ratio: String like "16:9", "9:16", "1:1", "4:3", "3:4"
        resolution: String like "512", "720", "1024", "1080", "1280", "2048"
                   (width for landscape, height for portrait)

    Returns:
        Tuple of (width, height) as integers
    """
    res = int(resolution)

    # Parse aspect ratio
    if ':' in aspect_ratio:
        parts = aspect_ratio.split(':')
        ar_w = int(parts[0])
        ar_h = int(parts[1])
    else:
        # Default to 1:1 if format is wrong
        ar_w = 1
        ar_h = 1

    # Determine orientation and calculate dimensions
    if ar_w >= ar_h:
        # Landscape or square: resolution is width
        width = res
        height = int(res * ar_h / ar_w)
    else:
        # Portrait: resolution is height
        height = res
        width = int(res * ar_w / ar_h)

    # Ensure dimensions are multiples of 8 (required by most AI models)
    width = (width // 8) * 8
    height = (height // 8) * 8

    return width, height


def update_env_config(updates: dict, env_path: str = ".env"):
    """
    Update .env file with new values.

    Args:
        updates: Dict of key-value pairs to update
        env_path: Path to .env file
    """
    import os

    # Read existing lines
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

    # Create map of existing keys
    key_map = {}
    for i, line in enumerate(lines):
        if '=' in line and not line.strip().startswith('#'):
            key = line.split('=')[0].strip()
            key_map[key] = i

    # Update or add keys
    for key, value in updates.items():
        new_line = f"{key}={value}\n"
        if key in key_map:
            lines[key_map[key]] = new_line
        else:
            if lines and not lines[-1].endswith('\n'):
                lines[-1] += '\n'
            lines.append(new_line)

    # Write back
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
