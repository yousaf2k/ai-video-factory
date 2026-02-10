"""
Narration Generator - Generate voice-over narration using LLM and TTS.

Supports:
- LLM-based narration script generation
- ComfyUI TTS workflow integration
- Local TTS fallback (edge-tts)
- ElevenLabs API integration
"""
import os
import json
from pathlib import Path
from core.gemini_engine import ask
from core.agent_loader import load_agent_prompt
from core.comfy_client import submit, wait_for_prompt_completion
import config


def generate_narration_script(story_json, shots, total_duration=None, agent_name="default"):
    """
    Generate a narration script from story and shots.

    Args:
        story_json: The story JSON
        shots: List of shot dictionaries
        total_duration: Total video duration in seconds (optional)
        agent_name: Name of the narration agent to use

    Returns:
        Dictionary with narration script and timing
    """
    # Build input for the agent
    story_data = json.loads(story_json) if isinstance(story_json, str) else story_json

    input_text = f"""
STORY:
Title: {story_data.get('title', '')}
Style: {story_data.get('style', '')}

SCENES ({len(story_data.get('scenes', []))} total):
"""

    for i, scene in enumerate(story_data.get('scenes', []), 1):
        input_text += f"""
Scene {i}:
  Location: {scene.get('location', '')}
  Characters: {scene.get('characters', '')}
  Action: {scene.get('action', '')}
  Emotion: {scene.get('emotion', '')}
"""

    if total_duration:
        input_text += f"\nTARGET VIDEO DURATION: {total_duration} seconds"
    else:
        # Estimate duration from shots (5 seconds per shot)
        estimated_duration = len(shots) * config.DEFAULT_SHOT_LENGTH
        input_text += f"\nESTIMATED VIDEO DURATION: {estimated_duration} seconds"

    # Try to use agent prompt
    try:
        prompt = load_agent_prompt("narration", input_text, agent_name)
    except (FileNotFoundError, ValueError):
        # Fallback to simple prompt
        print(f"[WARN] Narration agent '{agent_name}' not found, using legacy prompt")
        prompt = f"""Create a narration script for the following story.

Target duration: {total_duration or 'variable'} seconds

Create a narration with timing cues:
[0:00-0:05] Opening
[0:05-0:15] Story development
[0:15-0:30] Main content
[0:30-0:45] Conclusion

STORY:
{input_text}
"""

    response = ask(prompt, response_format="text/plain")
    return response


def generate_narration_audio(script, output_path, tts_method="local", comfyui_workflow=None, voice="default"):
    """
    Generate narration audio from script using TTS.

    Args:
        script: Narration script text
        output_path: Where to save the audio file
        tts_method: TTS method to use ("local", "comfyui", "elevenlabs")
        comfyui_workflow: Path to ComfyUI TTS workflow JSON
        voice: Voice selection (model-dependent)

    Returns:
        Path to generated audio file, or None if failed
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if tts_method == "comfyui" and comfyui_workflow:
        return _generate_with_comfyui(script, output_path, comfyui_workflow, voice)
    elif tts_method == "elevenlabs":
        return _generate_with_elevenlabs(script, output_path, voice)
    else:
        return _generate_with_local_tts(script, output_path, voice)


def _generate_with_elevenlabs(script, output_path, voice="default"):
    """
    Generate audio using ElevenLabs API.

    Args:
        script: Text to synthesize
        output_path: Output audio file path
        voice: Voice ID or name (e.g., "Rachel", "Domi", "21m00Tcm4TlvDq8ikWAM")

    Returns:
        Path to generated audio or None
    """
    try:
        import requests

        api_key = config.ELEVENLABS_API_KEY
        if not api_key:
            print("[ERROR] ELEVENLABS_API_KEY not set in config.py or environment variables")
            print("[HINT] Get your API key from: https://elevenlabs.io/app/settings/api-keys")
            print("[HINT] Set it with: os.environ['ELEVENLABS_API_KEY'] = 'your_key_here'")
            return None

        # Use default voice if not specified
        if voice == "default":
            voice = "Rachel"  # Popular default voice

        print(f"[INFO] Using ElevenLabs TTS with voice: {voice}")
        print(f"[INFO] Model: {config.ELEVENLABS_MODEL}")

        # First, try to get the voice ID if a name is provided
        voice_id = voice

        # If voice doesn't look like an ID (not 24 chars), try to find it
        if len(voice) != 24 or not voice.isalnum():
            voice_id = _get_elevenlabs_voice_id(voice)
            if not voice_id:
                print(f"[ERROR] Could not find voice '{voice}' in your ElevenLabs account")
                print(f"[HINT] Available voices: Use --list-voices to see all voices")
                return None
            print(f"[INFO] Found voice ID: {voice_id}")

        # Clean the script - remove timing markers
        cleaned_script = _clean_script_for_tts(script)

        # API endpoint for text-to-speech
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }

        data = {
            "text": cleaned_script,
            "model_id": config.ELEVENLABS_MODEL,
            "voice_settings": {
                "stability": config.ELEVENLABS_STABILITY,
                "similarity_boost": config.ELEVENLABS_SIMILARITY
            }
        }

        print(f"[TTS] Sending to ElevenLabs API...")
        print(f"[TTS] Script length: {len(cleaned_script)} characters")

        response = requests.post(url, json=data, headers=headers, timeout=120)

        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"[PASS] Narration audio saved: {output_path}")
            print(f"[INFO] File size: {os.path.getsize(output_path):,} bytes")
            return output_path
        elif response.status_code == 401:
            print("[ERROR] ElevenLabs API authentication failed")
            print("[HINT] Check your ELEVENLABS_API_KEY")
            return None
        elif response.status_code == 429:
            print("[ERROR] ElevenLabs API quota exceeded")
            print("[HINT] Check your quota at: https://elevenlabs.io/app/settings")
            return None
        else:
            print(f"[ERROR] ElevenLabs API error: {response.status_code}")
            print(f"[ERROR] Response: {response.text}")
            return None

    except ImportError:
        print("[ERROR] requests library not installed. Install with: pip install requests")
        return None
    except Exception as e:
        print(f"[ERROR] ElevenLabs TTS generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def _get_elevenlabs_voice_id(voice_name):
    """
    Get the voice ID for a given voice name from ElevenLabs.

    Args:
        voice_name: Name of the voice (e.g., "Rachel", "Domi")

    Returns:
        Voice ID string or None if not found
    """
    try:
        import requests

        api_key = config.ELEVENLABS_API_KEY
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {"xi-api-key": api_key}

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            voices_data = response.json()
            voices = voices_data.get('voices', [])

            # Search for matching voice name (case-insensitive)
            voice_name_lower = voice_name.lower()
            for voice in voices:
                if voice.get('name', '').lower() == voice_name_lower:
                    return voice.get('voice_id')

            # Not found, print available voices
            print(f"[WARN] Voice '{voice_name}' not found. Available voices:")
            for voice in voices[:10]:  # Show first 10
                print(f"       - {voice.get('name')} ({voice.get('voice_id')})")
            if len(voices) > 10:
                print(f"       ... and {len(voices) - 10} more")

            return None
        else:
            print(f"[ERROR] Failed to get voices: {response.status_code}")
            return None

    except Exception as e:
        print(f"[ERROR] Error fetching voices: {e}")
        return None


def _clean_script_for_tts(script):
    """
    Clean narration script by removing timing markers and formatting cues.

    Args:
        script: Raw script with timing markers

    Returns:
        Cleaned text suitable for TTS
    """
    import re

    # Remove timing markers like [0:00-0:08]
    script = re.sub(r'\[\d+:\d+-\d+:\d+\]', '', script)

    # Remove section headers like [INTRO], [CONCLUSION]
    script = re.sub(r'\[[A-Z]+\s*[A-Z]*\]', '', script)

    # Remove [PAUSE] markers
    script = script.replace('[PAUSE]', '')

    # Clean up extra whitespace
    script = re.sub(r'\n\s*\n', '\n\n', script)  # Multiple blank lines
    script = re.sub(r' +', ' ', script)  # Multiple spaces

    return script.strip()


def list_elevenlabs_voices():
    """
    List all available voices from ElevenLabs account.

    Returns:
        List of voice dictionaries or None if failed
    """
    try:
        import requests

        api_key = config.ELEVENLABS_API_KEY
        if not api_key:
            print("[ERROR] ELEVENLABS_API_KEY not set")
            return None

        url = "https://api.elevenlabs.io/v1/voices"
        headers = {"xi-api-key": api_key}

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            voices_data = response.json()
            return voices_data.get('voices', [])
        else:
            print(f"[ERROR] Failed to get voices: {response.status_code}")
            return None

    except Exception as e:
        print(f"[ERROR] Error fetching voices: {e}")
        return None


def _generate_with_comfyui(script, output_path, workflow_path, voice):
    """
    Generate audio using ComfyUI TTS workflow.

    Args:
        script: Text to synthesize
        output_path: Output audio file path
        workflow_path: Path to TTS workflow JSON
        voice: Voice model name

    Returns:
        Path to generated audio or None
    """
    try:
        # Load workflow template
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)

        # Find text input node (usually a KSampler or String Literal node)
        # Common node IDs for text input in TTS workflows
        text_node_patterns = ['text', 'prompt', 'tts_text', 'input_text']

        for node_id, node_data in workflow.items():
            if 'inputs' in node_data:
                # Check for text input widgets
                for key, value in node_data['inputs'].items():
                    if any(pattern in str(key).lower() for pattern in text_node_patterns):
                        if isinstance(value, str) and len(value) < 100:  # Likely a placeholder
                            workflow[node_id]['inputs'][key] = script
                            print(f"[INFO] Injected script into node {node_id}.{key}")

        # Find voice/model selection node
        voice_node_patterns = ['voice', 'model', 'speaker', 'tts_model']
        for node_id, node_data in workflow.items():
            if 'inputs' in node_data:
                for key in node_data['inputs'].keys():
                    if any(pattern in str(key).lower() for pattern in voice_node_patterns):
                        if isinstance(node_data['inputs'].get(key), str):
                            workflow[node_id]['inputs'][key] = voice
                            print(f"[INFO] Set voice to '{voice}' in node {node_id}.{key}")

        # Submit to ComfyUI
        result = submit(workflow)
        prompt_id = result.get('prompt_id')

        if not prompt_id:
            print("[ERROR] No prompt_id returned from ComfyUI")
            return None

        print(f"[QUEUE] Narration TTS: Prompt {prompt_id[:8]}... submitted")

        # Wait for completion
        wait_result = wait_for_prompt_completion(prompt_id, timeout=300)  # 5 min timeout

        if not wait_result['success']:
            print(f"[ERROR] TTS generation failed: {wait_result.get('error', 'Unknown error')}")
            return None

        # Get audio output
        outputs = wait_result.get('outputs', [])
        audio_outputs = [o for o in outputs if o['type'] in ['audio', 'sound']]

        if audio_outputs:
            # Copy first audio output to target path
            audio_info = audio_outputs[0]
            source_path = audio_info.get('filename', '')

            if source_path:
                # ComfyUI outputs go to ComfyUI/output/audio by default
                comfy_output_dir = Path(config.COMFY_URL.replace('http://', '').replace(':', '')) / 'output' / 'audio'
                full_source = comfy_output_dir / source_path

                if full_source.exists():
                    import shutil
                    shutil.copy2(full_source, output_path)
                    print(f"[PASS] Narration audio saved: {output_path}")
                    return output_path
                else:
                    print(f"[WARN] Source audio not found at {full_source}")
                    return str(full_source)  # Return path anyway
            else:
                print("[WARN] Audio output filename not found")
        else:
            print("[WARN] No audio outputs found in ComfyUI response")

        return None

    except Exception as e:
        print(f"[ERROR] ComfyUI TTS generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def _generate_with_local_tts(script, output_path, voice):
    """
    Generate audio using local TTS (edge-tts fallback).

    Args:
        script: Text to synthesize
        output_path: Output audio file path
        voice: Voice name

    Returns:
        Path to generated audio or None
    """
    try:
        import edge_tts

        # Default female voice
        voice_name = voice if voice.startswith("en-") else "en-US-AriaNeural"

        print(f"[INFO] Using edge-tts with voice: {voice_name}")

        async def generate():
            communicate = edge_tts.Communicate(script, voice_name)
            await communicate.save(output_path)

        import asyncio
        asyncio.run(generate())

        if os.path.exists(output_path):
            print(f"[PASS] Narration audio saved: {output_path}")
            return output_path
        else:
            print("[ERROR] Audio file was not created")
            return None

    except ImportError:
        print("[ERROR] edge-tts not installed. Install with: pip install edge-tts")
        print("[HINT] Or use ComfyUI TTS workflow with --tts-workflow")
        return None
    except Exception as e:
        print(f"[ERROR] Local TTS generation failed: {e}")
        return None


def generate_narration_for_session(session_id, story_json, shots, total_duration, agent_name="default",
                                   tts_method="local", tts_workflow_path=None, voice="default"):
    """
    Complete narration generation workflow for a session.

    Args:
        session_id: Session identifier
        story_json: Story data
        shots: Shot list
        total_duration: Total video duration
        agent_name: Narration agent to use
        tts_method: TTS method ("local", "comfyui", "elevenlabs")
        tts_workflow_path: Path to TTS workflow JSON (for comfyui)
        voice: Voice selection

    Returns:
        Tuple of (script_path, audio_path) or (None, None) if failed
    """
    from core.session_manager import SessionManager

    session_mgr = SessionManager()
    narration_dir = session_mgr.get_session_dir(session_id) / "narration"
    os.makedirs(narration_dir, exist_ok=True)

    # Step 1: Generate script
    print("\n[NARRATION] Step 1: Generating script...")
    script = generate_narration_script(story_json, shots, total_duration, agent_name)

    # Save script
    script_path = narration_dir / "narration_script.txt"
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script)
    print(f"[PASS] Script saved: {script_path}")

    # Step 2: Generate audio
    print("\n[NARRATION] Step 2: Generating audio...")
    audio_path = narration_dir / "narration.wav"

    generated_audio = generate_narration_audio(script, audio_path, tts_method=tts_method,
                                               comfyui_workflow=tts_workflow_path, voice=voice)

    if generated_audio:
        # Mark narration as complete
        session_mgr.mark_step_complete(session_id, 'narration')
        return str(script_path), str(audio_path)
    else:
        print("[FAIL] Narration audio generation failed")
        return str(script_path), None


if __name__ == "__main__":
    # Test listing ElevenLabs voices
    import argparse

    parser = argparse.ArgumentParser(description="Narration generator utilities")
    parser.add_argument('--list-voices', action='store_true', help='List ElevenLabs voices')
    parser.add_argument('--test-script', action='store_true', help='Test script generation')

    args = parser.parse_args()

    if args.list_voices:
        print("\n" + "="*70)
        print("ELEVENLABS VOICES")
        print("="*70)

        voices = list_elevenlabs_voices()
        if voices:
            print(f"\nFound {len(voices)} voices:\n")
            for voice in voices:
                name = voice.get('name', 'Unknown')
                voice_id = voice.get('voice_id', 'Unknown')
                labels = voice.get('labels', {})
                accent = labels.get('accent', 'N/A')
                gender = labels.get('gender', 'N/A')
                age = labels.get('age', 'N/A')
                print(f"  {name}")
                print(f"    ID: {voice_id}")
                print(f"    Accent: {accent}, Gender: {gender}, Age: {age}")
                print()
        else:
            print("\n[ERROR] Could not fetch voices. Check your API key.")
        print("="*70)

    elif args.test_script:
        # Test narration script generation
        test_story = json.dumps({
            "title": "Test Video",
            "style": "documentary",
            "scenes": [
                {"location": "Forest", "characters": "Explorer", "action": "Walking", "emotion": "Curious"}
            ]
        })

        test_shots = [{"index": 1}]

        script = generate_narration_script(test_story, test_shots, total_duration=30)
        print("\nGenerated Narration Script:")
        print("="*60)
        print(script)
