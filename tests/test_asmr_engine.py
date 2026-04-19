"""
Tests for ASMR glass cutting story engine
"""
import pytest
import json
from core.story_engine import build_story_asmr_glass_cutting


def test_build_story_asmr_specific_objects():
    """Test with specific objects in natural language"""
    story_json = build_story_asmr_glass_cutting(
        "create videos of strawberry and apple"
    )
    story = json.loads(story_json)

    assert story["project_type"] == 4  # ASMR_GLASS_CUTTING
    assert len(story["shots"]) >= 2
    assert any("strawberry" in s["object_name"].lower() for s in story["shots"])
    assert any("apple" in s["object_name"].lower() for s in story["shots"])
    assert all(s["duration"] == 5 for s in story["shots"])
    assert "expanded_objects" in story


def test_build_story_asmr_category_expansion():
    """Test with category expansion"""
    story_json = build_story_asmr_glass_cutting("red fruits")
    story = json.loads(story_json)

    assert 5 <= len(story["shots"]) <= 10
    assert all(s["duration"] == 5 for s in story["shots"])
    assert len(story["expanded_objects"]) >= 5
    assert story["total_duration"] == len(story["shots"]) * 5


def test_build_story_asmr_duration_calculation():
    """Test total duration calculation"""
    story_json = build_story_asmr_glass_cutting(
        "banana and orange",
        shot_duration=8
    )
    story = json.loads(story_json)

    expected_duration = len(story["shots"]) * 8
    assert story["total_duration"] == expected_duration


def test_build_story_asmr_invalid_input():
    """Test error handling for invalid input"""
    with pytest.raises(ValueError, match="describe the fruits"):
        build_story_asmr_glass_cutting("")


def test_build_story_asmr_prompt_quality():
    """Test that prompts follow glass sculpture style"""
    story_json = build_story_asmr_glass_cutting("strawberry")
    story = json.loads(story_json)

    shot = story["shots"][0]
    prompt = shot["prompt"].lower()

    # Check for glass sculpture style keywords
    assert "glass" in prompt
    assert any(word in prompt for word in ["asmr", "cinematic", "8k", "4k"])
    assert len(shot["prompt"]) > 100  # Detailed prompt


def test_build_story_asmr_aspect_ratio():
    """Test aspect ratio is set correctly"""
    story_json = build_story_asmr_glass_cutting(
        "tomato",
        aspect_ratio="9:16"
    )
    story = json.loads(story_json)

    assert story["aspect_ratio"] == "9:16"
