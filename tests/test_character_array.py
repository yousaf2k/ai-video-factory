import json
import pytest
from core.story_engine import build_story
from unittest.mock import MagicMock, patch

def test_character_array_generation():
    """Test that story generation includes the characters array with expected fields."""
    
    # Mock LLM response for Pass 1 (Master Script)
    master_json = json.dumps({
        "title": "Starship Discovery",
        "style": "sci-fi",
        "characters": ["Captain Nova", "Android Echo"],
        "master_script": "The starship Discovery orbits a crystal planet..."
    })
    
    # Mock LLM response for Pass 2 (Scenes + Characters)
    story_json = json.dumps({
        "title": "Starship Discovery",
        "style": "sci-fi",
        "characters": [
            {
                "name": "Captain Nova",
                "image_prompt_face": "Captain Nova face on white background",
                "image_prompt_full": "Captain Nova full body standing",
                "voice_type": "Commanding female voice",
                "personality": "Brave and decisive",
                "attire": "Silver flight suit"
            },
            {
                "name": "Android Echo",
                "image_prompt_face": "Android Echo face on white background",
                "image_prompt_full": "Android Echo full body standing",
                "voice_type": "Synthetic calm voice",
                "personality": "Logical and observant",
                "attire": "Integrated chassis components"
            }
        ],
        "scenes": [
            {
                "location": "Bridge",
                "characters": "Captain Nova, Android Echo",
                "action": "Monitoring sensors",
                "emotion": "Tense",
                "narration": "They approached the unknown...",
                "scene_duration": 30
            }
        ]
    })
    
    with patch('core.story_engine.get_provider') as mock_get_provider:
        mock_provider = MagicMock()
        mock_get_provider.return_value = mock_provider
        
        # Configure side effects for the two passes
        mock_provider.ask.side_effect = [master_json, story_json]
        
        result_json = build_story("A sci-fi adventure", target_length=30)
        result = json.loads(result_json)
        
        # Assertions
        assert "characters" in result
        assert len(result["characters"]) == 2
        
        char1 = result["characters"][0]
        assert char1["name"] == "Captain Nova"
        assert "image_prompt_face" in char1
        assert "image_prompt_full" in char1
        assert "voice_type" in char1
        assert "personality" in char1
        assert "attire" in char1
        assert "white background" in char1["image_prompt_face"].lower()
        assert "standing" in char1["image_prompt_full"].lower()

if __name__ == "__main__":
    test_character_array_generation()
    print("Test Passed!")
