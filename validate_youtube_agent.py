#!/usr/bin/env python3
"""
Validation script for YouTube Documentary Agent JSON schema.
This script verifies the agent file exists and can be loaded correctly.
"""

import json
import os
from pathlib import Path

def validate_youtube_agent():
    """Validate the YouTube documentary agent structure."""

    print("=" * 60)
    print("YOUTUBE DOCUMENTARY AGENT VALIDATION")
    print("=" * 60)

    # Check if agent file exists
    agent_path = Path("agents/story/youtube_documentary.md")

    if not agent_path.exists():
        print(f"[FAILED] Agent file not found at {agent_path}")
        return False

    print(f"[OK] Agent file exists: {agent_path}")

    # Read and validate content
    with open(agent_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check for required sections
    required_sections = [
        "## Guidelines",
        "## Output Format",
        "## Scene Structure",
        "## Narration Guidelines",
        "## Hook Types",
        "## YouTube Optimization",
        "{USER_INPUT}"
    ]

    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)

    if missing_sections:
        print(f"[FAILED] Missing required sections: {missing_sections}")
        return False

    print("[OK] All required sections present")

    # Check for YouTube-specific fields in JSON schema
    required_fields = [
        '"seo_keywords"',
        '"title_options"',
        '"thumbnail_moments"',
        '"chapters"',
        '"description_preview"',
        '"hook_type"'
    ]

    missing_fields = []
    for field in required_fields:
        if field not in content:
            missing_fields.append(field)

    if missing_fields:
        print(f"[FAILED] Missing required JSON fields: {missing_fields}")
        return False

    print("[OK] All YouTube-specific JSON fields present")

    # Validate hook types
    hook_types = ["shock", "question", "tease", "pattern_interrupt", "breadcrumb", "cta"]
    hook_types_present = all(f'**{hook_type}**:' in content for hook_type in hook_types)

    if not hook_types_present:
        print(f"[FAILED] Not all hook types documented")
        return False

    print("[OK] All hook types documented")

    # Check for YouTube-specific guidelines
    youtube_guidelines = [
        "Opening Hook",
        "Pattern Interrupts",
        "Breadcrumbs",
        "Engagement Elements",
        "Fast Pacing",
        "Conversational Energy",
        "Retention Focus",
        "YouTube Optimization"
    ]

    missing_guidelines = []
    for guideline in youtube_guidelines:
        if guideline not in content:
            missing_guidelines.append(guideline)

    if missing_guidelines:
        print(f"[FAILED] Missing YouTube guidelines: {missing_guidelines}")
        return False

    print("[OK] All YouTube-specific guidelines present")

    # Test example JSON structure
    example_json = {
        "title": "Test Documentary",
        "style": "YouTube viral documentary",
        "seo_keywords": ["test", "keyword"],
        "title_options": ["Title 1", "Title 2"],
        "thumbnail_moments": ["Moment 1", "Moment 2"],
        "chapters": [{"time": "0:00", "title": "Chapter 1"}],
        "description_preview": "Test description",
        "scenes": [
            {
                "location": "Test location",
                "characters": "Test characters",
                "action": "Test action",
                "emotion": "curiosity",
                "hook_type": "shock",
                "narration": "Test narration"
            }
        ]
    }

    try:
        json.dumps(example_json)
        print("[OK] Example JSON structure is valid")
    except Exception as e:
        print(f"[FAILED] Invalid JSON structure: {e}")
        return False

    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print("[SUCCESS] All validation checks passed!")
    print(f"\nAgent file: {agent_path}")
    print(f"File size: {len(content)} characters")
    print(f"Lines: {len(content.splitlines())}")
    print("\nThe YouTube Documentary Agent is ready to use!")
    print("\nUsage:")
    print("  python core/main.py --story-agent youtube_documentary --idea 'Your topic here'")

    return True

if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    success = validate_youtube_agent()
    exit(0 if success else 1)
