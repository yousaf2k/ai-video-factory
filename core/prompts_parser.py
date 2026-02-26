"""
Prompts Parser Module

This module parses user-provided prompts files and converts them to the shot format
used by the video generation pipeline. This allows users to skip story generation
and use their own pre-written prompts.

Author: AIVideoFactory
"""

import re
import os
import logging
from typing import List, Dict, Tuple, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Default values
DEFAULT_CAMERA = "static"
DEFAULT_MOTION = "Subtle camera movement, slow and smooth"

# Camera type keywords for auto-detection (ordered by priority)
CAMERA_KEYWORDS = {
    'dronedive': ['dronedive', 'drone dive', 'dive'],
    'fpv': ['fpv', 'first person view', 'first-person'],
    'bullettime': ['bullet time', 'bullet-time', 'freeze frame'],
    'arc': ['arc shot', 'arc movement'],
    'walk': ['walk', 'walking', 'stroll'],
    'dolly': ['dolly', 'dolly in', 'dolly out', 'push in', 'pull back'],
    'orbit': ['orbit', 'orbit shot', '360 shot', '360 degree', 'circular'],
    'tracking': ['tracking', 'tracking shot', 'follow', 'following'],
    'zoom': ['zoom', 'zoom in', 'zoom out'],
    'pan': ['pan', 'panning', 'pan shot'],
    'drone': ['drone', 'aerial', 'bird\'s eye', 'birdseye', 'top-down', 'overhead'],
    'slow pan': ['slow pan'],
    'static': ['static', 'still', 'fixed', 'stationary', 'tripod']
}

# Motion defaults for different camera types
CAMERA_TO_MOTION = {
    'slow pan': 'Slow, smooth panoramic pan movement, cinematic and steady',
    'pan': 'Smooth panning movement, steady and controlled',
    'static': 'Very subtle breathing motion, minimal movement, steady and stable',
    'orbit': 'Smooth orbital movement around subject, 360-degree rotation',
    'zoom': 'Smooth zoom motion, controlled and cinematic',
    'tracking': 'Following movement alongside subject, smooth tracking',
    'drone': 'Cinematic drone movement, smooth aerial motion, slow and steady',
    'arc': 'Smooth arc movement around subject, curved trajectory',
    'walk': 'Smooth walking movement, handheld but stable, gentle motion',
    'fpv': 'First-person perspective movement, dynamic and immersive',
    'dronedive': 'Smooth diving motion, cinematic descent',
    'bullettime': 'Freeze-frame effect with subtle rotation, matrix-style',
    'dolly': 'Smooth dolly movement, push in or pull out, cinematic'
}


def parse_prompts_file(file_path: str) -> Tuple[List[Dict[str, any]], Optional[str]]:
    """
    Parse a prompts file and extract individual prompts.

    Supported formats:
    1. Blank-line separated (no numbers):
       (Technical details). Prompt text here...

       (Technical details). Another prompt here...

    2. "Prompt N: Title" format:
       Prompt 1: Title Here
       Full prompt text goes here...

    3. Numbered list format:
       1. Title
       Description text...

       OR

       1. Full prompt text here...
       2. Full prompt text here...

    4. Markdown headers:
       ## Title
       Content here...

    Args:
        file_path: Path to the prompts file

    Returns:
        Tuple of (list of prompt dictionaries, overall title)
        Each dict has: index, title, text (full content)

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file format is invalid
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Prompts file not found: {file_path}")

    logger.info(f"Parsing prompts file: {file_path}")

    # Read file with UTF-8 encoding, fallback to latin-1
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        logger.warning("UTF-8 decode failed, trying latin-1")
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()

    # Try different regex patterns to parse prompts
    prompts_data = []

    # Pattern 1: Prompts separated by blank lines (no numbers)
    # Each prompt is a paragraph/block of text separated by double newlines
    # Split by double newlines to get individual blocks
    blocks = re.split(r'\n\s*\n', content.strip())

    logger.debug(f"Split content into {len(blocks)} blocks")

    # Only use this pattern if we found multiple blocks
    if len(blocks) > 1:
        # Check if these are really unnumbered prompts (first block doesn't start with number)
        first_block = blocks[0].strip()
        if not first_block or not first_block[0].isdigit():
            for i, text in enumerate(blocks, 1):
                text_clean = text.strip()
                if not text_clean:
                    continue

                # Generate title from first sentence
                title_match = re.match(r'^([^.!?]*[.!?]?)', text_clean)
                if title_match:
                    title = title_match.group(1).strip()
                else:
                    title = text_clean[:80]

                prompts_data.append({
                    'index': i,
                    'title': title,
                    'text': text_clean
                })
            logger.info(f"Parsed {len(prompts_data)} prompts using blank-line separated format")

            # Debug: log first and last prompt lengths
            if prompts_data:
                first_len = len(prompts_data[0]['text'])
                last_len = len(prompts_data[-1]['text'])
                logger.debug(f"First prompt: {first_len} chars, Last prompt: {last_len} chars")
                if last_len > 5000:  # Suspiciously long
                    logger.warning(f"Last prompt is very long ({last_len} chars), may contain multiple prompts")

    # Only try other patterns if first pattern didn't work
    if not prompts_data:
        # Pattern 2: "Prompt N: Title" format (explicit "Prompt" keyword)
        pattern2 = r'Prompt\s+\d+:\s*([^\n]+)\s*\n(.*?)(?=\n\s*Prompt\s+\d+:|$)'
        matches2 = re.findall(pattern2, content, re.DOTALL | re.IGNORECASE)

        if matches2:
            for i, (title, text) in enumerate(matches2, 1):
                prompts_data.append({
                    'index': i,  # Use sequential numbering, ignore file numbering
                    'title': title.strip(),
                    'text': title.strip() + '\n' + text.strip()
                })
            logger.info(f"Parsed {len(prompts_data)} prompts using 'Prompt N: Title' pattern")
        else:
            # Pattern 3: Numbered list with full prompt content "1. Prompt text here..." or "1) Prompt text here..."
            # Matches number followed by complete prompt (may span multiple lines)
            pattern3 = r'(?:\d+[\.)]\s+)(.*?)(?=\n\s*\d+[\.)]\s+|$)'
            matches3 = re.findall(pattern3, content, re.DOTALL)

            if matches3 and len(matches3) > 1:
                for i, text in enumerate(matches3, 1):
                    # Use first 80 chars as title (since no separate title exists)
                    text_clean = text.strip()
                    # Remove leading number if present
                    text_clean = re.sub(r'^\d+[\.)]\s+', '', text_clean)

                    # Generate title from first part of prompt
                    title_match = re.match(r'^([^.!?]*[.!?]?)', text_clean)
                    if title_match:
                        title = title_match.group(1).strip()
                    else:
                        title = text_clean[:80]

                    prompts_data.append({
                        'index': i,
                        'title': title,
                        'text': text_clean
                    })
                logger.info(f"Parsed {len(prompts_data)} prompts using numbered list pattern (full content)")
            else:
                # Pattern 4: Traditional numbered list with title "1. Title\nDescription" or "1) Title\nDescription"
                pattern4 = r'\d+[\.)]\s*([^\n]+)\s*\n(.*?)(?=\n\s*\d+[\.)]|$)'
                matches4 = re.findall(pattern4, content, re.DOTALL)

                if matches4:
                    for i, (title, text) in enumerate(matches4, 1):
                        prompts_data.append({
                            'index': i,
                            'title': title.strip(),
                            'text': title.strip() + '\n' + text.strip()
                        })
                    logger.info(f"Parsed {len(prompts_data)} prompts using numbered list pattern (title + description)")
                else:
                    # Pattern 5: Markdown headers "## Title"
                    pattern5 = r'##+\s*([^\n]+)\s*\n(.*?)(?=##+|$)'
                    matches5 = re.findall(pattern5, content, re.DOTALL)

                    if matches5:
                        for i, (title, text) in enumerate(matches5, 1):
                            prompts_data.append({
                                'index': i,
                                'title': title.strip(),
                                'text': title.strip() + '\n' + text.strip()
                            })
                        logger.info(f"Parsed {len(prompts_data)} prompts using markdown headers")
                    else:
                        # Fallback: Treat entire file as single prompt
                        lines = content.strip().split('\n')
                        if lines:
                            first_line = lines[0].strip()
                            rest = '\n'.join(lines[1:]).strip()
                            prompts_data.append({
                                'index': 1,
                                'title': first_line[:100],  # First 100 chars as title
                                'text': content.strip()
                            })
                            logger.warning("Could not detect standard format, treating as single prompt")

    if not prompts_data:
        raise ValueError("No prompts found in file. Expected format:\nPrompt 1: Title\nPrompt text here...")

    # Extract overall title from first prompt if it seems like a main title
    overall_title = None
    if prompts_data:
        first_title = prompts_data[0]['title'].lower()
        if any(keyword in first_title for keyword in ['overview', 'introduction', 'title', 'main']):
            overall_title = prompts_data[0]['title']
            prompts_data = prompts_data[1:]  # Remove the title entry
            # Re-index remaining prompts
            for i, prompt in enumerate(prompts_data, 1):
                prompt['index'] = i

    return prompts_data, overall_title


def _extract_camera_from_prompt(prompt_text: str) -> str:
    """
    Auto-detect camera type from prompt text.

    Args:
        prompt_text: The prompt text to analyze

    Returns:
        Detected camera type or DEFAULT_CAMERA
    """
    if not prompt_text:
        return DEFAULT_CAMERA

    prompt_lower = prompt_text.lower()

    # Check for camera type keywords (in priority order)
    for camera_type, keywords in CAMERA_KEYWORDS.items():
        for keyword in keywords:
            if keyword in prompt_lower:
                logger.debug(f"Detected camera type '{camera_type}' from keyword '{keyword}'")
                return camera_type

    logger.debug(f"No camera type detected, using default: {DEFAULT_CAMERA}")
    return DEFAULT_CAMERA


def _extract_narration_from_prompt(prompt_text: str) -> str:
    """
    Extract narration text from prompt.

    Looks for patterns like:
    - "Action: ..."
    - "Scene: ..."
    - "Narration: ..."

    Args:
        prompt_text: The prompt text to extract narration from

    Returns:
        Extracted narration text or empty string
    """
    if not prompt_text:
        return ""

    # Try to find action/scene/narration patterns
    patterns = [
        r'(?:Action|Scene|Narration):\s*([^\n\.]+\.?[^\n]*)',
        r'(?:What\'s happening|Description):\s*([^\n\.]+\.?[^\n]*)'
    ]

    for pattern in patterns:
        match = re.search(pattern, prompt_text, re.IGNORECASE)
        if match:
            narration = match.group(1).strip()
            logger.debug(f"Extracted narration: {narration[:50]}...")
            return narration

    # Fallback: extract first meaningful sentence
    # Look for sentences that describe action
    lines = prompt_text.split('\n')
    for line in lines:
        line = line.strip()
        # Skip title/short lines
        if len(line) < 20:
            continue
        # Skip lines that are clearly part of image generation prompt
        if any(marker in line.lower() for marker in ['(', ':', ',', 'scale', 'quality', 'resolution']):
            continue
        # Found a good candidate
        if '.' in line:
            first_sentence = line.split('.')[0] + '.'
            return first_sentence.strip()

    return ""


def prompts_to_shots(prompts_data: List[Dict[str, any]]) -> List[Dict[str, any]]:
    """
    Convert parsed prompts to shot format.

    Args:
        prompts_data: List of prompt dictionaries from parse_prompts_file()

    Returns:
        List of shot dictionaries with keys: index, image_prompt, motion_prompt, camera, narration
    """
    shots = []

    for seq_idx, prompt_data in enumerate(prompts_data, 1):
        text = prompt_data['text']
        title = prompt_data.get('title', '')

        # Extract camera type
        camera = _extract_camera_from_prompt(text)

        # Extract motion prompt based on camera type
        motion_prompt = CAMERA_TO_MOTION.get(camera, DEFAULT_MOTION)

        # Extract narration
        narration = _extract_narration_from_prompt(text)

        # Create shot with sequential index (always 1, 2, 3... regardless of file numbering)
        shot = {
            'index': seq_idx,
            'scene': seq_idx,  # Scene number matches shot index for 1:1 mapping
            'title': title,
            'image_prompt': text,
            'motion_prompt': motion_prompt,
            'camera': camera,
            'narration': narration,
            'from_prompt_file': True  # Flag to indicate this came from a prompt file
        }

        shots.append(shot)
        logger.debug(f"Created shot {seq_idx}: camera={camera}, narration={bool(narration)}, from_prompt_file=True")

    logger.info(f"Converted {len(prompts_data)} prompts to {len(shots)} shots")
    return shots


def validate_and_fix_prompts(prompts_data: List[Dict[str, any]]) -> List[Dict[str, any]]:
    """
    Validate and fix common issues with parsed prompts.

    Args:
        prompts_data: List of prompt dictionaries

    Returns:
        Validated and fixed list of prompts
    """
    if not prompts_data:
        return prompts_data

    valid_cameras = set(CAMERA_KEYWORDS.keys())

    for prompt in prompts_data:
        # Fix whitespace issues
        if 'text' in prompt:
            prompt['text'] = ' '.join(prompt['text'].split())  # Normalize whitespace
        if 'title' in prompt:
            prompt['title'] = prompt['title'].strip()

        # Ensure index is present and valid
        if 'index' not in prompt:
            prompt['index'] = prompts_data.index(prompt) + 1

        # Validate camera if present
        if 'camera' in prompt and prompt['camera'] not in valid_cameras:
            logger.warning(f"Invalid camera '{prompt['camera']}', using default")
            prompt['camera'] = DEFAULT_CAMERA

    logger.info(f"Validated {len(prompts_data)} prompts")
    return prompts_data


# Example usage and testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python prompts_parser.py <prompts_file.txt>")
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        # Parse
        prompts_data, overall_title = parse_prompts_file(file_path)
        print(f"\nParsed {len(prompts_data)} prompts")
        if overall_title:
            print(f"Overall title: {overall_title}")

        # Validate
        prompts_data = validate_and_fix_prompts(prompts_data)

        # Convert to shots
        shots = prompts_to_shots(prompts_data)

        # Display results
        print("\n" + "="*70)
        print("SHOTS PREVIEW")
        print("="*70)
        for shot in shots[:3]:  # Show first 3
            print(f"\nShot {shot['index']}: {shot.get('title', 'No title')}")
            print(f"  Camera: {shot['camera']}")
            print(f"  Narration: {shot.get('narration', 'No narration')[:80]}...")
            print(f"  Prompt: {shot['image_prompt'][:100]}...")

        if len(shots) > 3:
            print(f"\n... and {len(shots) - 3} more shots")

        print(f"\nTotal: {len(shots)} shots ready for generation")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
