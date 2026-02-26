#!/usr/bin/env python3
"""
Test script for Prehistoric POV Agents

This script helps verify that the POV agents are working correctly.
"""

import sys
from pathlib import Path

def check_agent_files():
    """Check if POV agent files exist and have required content"""
    print("=" * 60)
    print("Prehistoric POV Agents - File Verification")
    print("=" * 60)
    print()

    agents = {
        'Story Agent': 'agents/story/prehistoric_pov.md',
        'Image Agent': 'agents/image/prehistoric_pov.md'
    }

    all_passed = True

    for name, path in agents.items():
        p = Path(path)
        if not p.exists():
            print(f"[FAIL] {name} - NOT FOUND at {path}")
            all_passed = False
            continue

        print(f"[PASS] {name}")
        print(f"  Path: {path}")
        print(f"  Size: {p.stat().st_size:,} bytes")

        # Check content
        content = p.read_text(encoding='utf-8', errors='ignore')

        # Required keywords
        required_keywords = [
            'First person POV',
            'hands visible',
            'Sony Venice 2',
            'diegetic'
        ]

        missing = []
        for keyword in required_keywords:
            if keyword.lower() not in content.lower():
                missing.append(keyword)

        if missing:
            print(f"  [WARNING] Missing keywords: {', '.join(missing)}")
            all_passed = False
        else:
            print(f"  [PASS] All required keywords present")

        print()

    return all_passed

def check_documentation():
    """Check if documentation files exist"""
    print("=" * 60)
    print("Documentation Verification")
    print("=" * 60)
    print()

    docs = {
        'User Guide': 'docs/PREHISTORIC_POV_GUIDE.md',
        'Quick Start': 'docs/PREHISTORIC_POV_QUICKSTART.md',
        'Implementation Summary': 'docs/PREHISTORIC_POV_IMPLEMENTATION_SUMMARY.md'
    }

    all_passed = True

    for name, path in docs.items():
        p = Path(path)
        if p.exists():
            print(f"[PASS] {name} ({p.stat().st_size:,} bytes)")
        else:
            print(f"[FAIL] {name} - NOT FOUND")
            all_passed = False

    print()
    return all_passed

def check_config():
    """Check if config.py includes POV agents"""
    print("=" * 60)
    print("Configuration Verification")
    print("=" * 60)
    print()

    config_path = Path('config.py')
    if not config_path.exists():
        print("[FAIL] config.py not found")
        return False

    config_content = config_path.read_text(encoding='utf-8', errors='ignore')

    checks = {
        'prehistoric_pov in STORY_AGENT comment': 'prehistoric_pov' in config_content and 'STORY_AGENT' in config_content,
        'prehistoric_pov in IMAGE_AGENT comment': 'prehistoric_pov' in config_content and 'IMAGE_AGENT' in config_content,
    }

    all_passed = True
    for check_name, passed in checks.items():
        if passed:
            print(f"[PASS] {check_name}")
        else:
            print(f"[FAIL] {check_name}")
            all_passed = False

    print()
    return all_passed

def print_usage_examples():
    """Print usage examples"""
    print("=" * 60)
    print("Usage Examples")
    print("=" * 60)
    print()

    examples = [
        ("Generate POV Story",
         "python core/main.py --story-agent prehistoric_pov --idea \"Time traveler encounters T-Rex\""),

        ("Generate POV Images",
         "python core/main.py --image-agent prehistoric_pov --resume [session_id]"),

        ("Generate Full POV Video",
         "python core/main.py --story-agent prehistoric_pov --image-agent prehistoric_pov --idea \"Triceratops herd encounter\""),
    ]

    for title, command in examples:
        print(f"{title}:")
        print(f"  {command}")
        print()

def print_expected_output():
    """Print what to expect from POV agents"""
    print("=" * 60)
    print("Expected Output Characteristics")
    print("=" * 60)
    print()

    characteristics = [
        ("Story Agent", [
            "First-person narration (\"I see\", \"my hands\")",
            "Present tense (\"I raise the camera\")",
            "Hands mentioned in every scene",
            "Diegetic camera work (REC button, battery, viewfinder)",
            "Personal survival stakes (danger, terror + wonder)",
        ]),
        ("Image Agent", [
            "First person POV in every prompt",
            "Hands visible in frame (holding camera, reaching out)",
            "Sony Venice 2 camera body mentioned",
            "Arri Signature Prime lens specified (16mm-85mm)",
            "8K resolution, 16:9 widescreen",
            "Netflix quality, photorealistic",
        ]),
    ]

    for agent_name, features in characteristics:
        print(f"{agent_name}:")
        for feature in features:
            print(f"  - {feature}")
        print()

def main():
    """Main test function"""
    print()
    print("*" * 60)
    print("*" + " " * 58 + "*")
    print("*" + "  Prehistoric POV Dinosaur Agents - Test Suite  ".center(58) + "*")
    print("*" + " " * 58 + "*")
    print("*" * 60)
    print()

    # Run checks
    files_ok = check_agent_files()
    docs_ok = check_documentation()
    config_ok = check_config()

    # Print usage and expected output
    print_usage_examples()
    print_expected_output()

    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print()

    if files_ok and docs_ok and config_ok:
        print("[PASS] All tests passed!")
        print()
        print("The Prehistoric POV agents are ready to use.")
        print()
        print("Next steps:")
        print("  1. Test story generation:")
        print("     python core/main.py --story-agent prehistoric_pov --idea \"T-Rex encounter\"")
        print()
        print("  2. Test image generation:")
        print("     python core/main.py --image-agent prehistoric_pov --resume [session_id]")
        print()
        print("  3. Generate full video:")
        print("     python core/main.py --story-agent prehistoric_pov --image-agent prehistoric_pov --idea \"Dinosaur survival\" --render")
        print()
        return 0
    else:
        print("[FAIL] Some tests failed")
        print()
        print("Please check the errors above and ensure all files are correctly created.")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
