# ElevenLabs TTS Integration Guide

This guide explains how to set up and use ElevenLabs for text-to-speech narration generation.

## Prerequisites

1. **ElevenLabs Account**: Sign up at https://elevenlabs.io
2. **API Key**: Get your API key from https://elevenlabs.io/app/settings/api-keys
3. **Python Requests Library**: Install with `pip install requests`

## Configuration

### Option 1: Environment Variable (Recommended)

Set the `ELEVENLABS_API_KEY` environment variable:

```bash
# Windows PowerShell
$env:ELEVENLABS_API_KEY="your_api_key_here"

# Windows CMD
set ELEVENLABS_API_KEY=your_api_key_here

# Linux/Mac
export ELEVENLABS_API_KEY="your_api_key_here"
```

### Option 2: config.py

Edit `config.py` and add your API key:

```python
ELEVENLABS_API_KEY = "your_api_key_here"
```

## Available Voices

List all available voices in your ElevenLabs account:

```bash
python core/main.py --list-voices
```

Or use the narration generator directly:

```bash
python core/narration_generator.py --list-voices
```

## Popular ElevenLabs Voices

| Voice Name | Description | Best For |
|------------|-------------|----------|
| Rachel | Female, warm, professional | Narration, tutorials |
| Domi | Male, calm, authoritative | Documentary, educational |
| Clyde | Male, deep, serious | Dramatic content |
| Mimi | Female, expressive, energetic | Marketing, upbeat content |
| Fin | Male, friendly, casual | Conversational content |

## Usage Examples

### Basic Narration with ElevenLabs

```bash
python core/main.py --idea "Nature documentary" \
  --narration-agent professional \
  --tts-method elevenlabs \
  --tts-voice "Rachel"
```

### Using Voice ID Directly

```bash
python core/main.py --idea "Tutorial" \
  --tts-method elevenlabs \
  --tts-voice "21m00Tcm4TlvDq8ikWAM"  # Rachel's ID
```

### Adjust Voice Settings

Edit `config.py` to customize voice behavior:

```python
# Model selection (quality vs speed)
ELEVENLABS_MODEL = "eleven_multilingual_v2"  # Best quality
# Options:
#   - eleven_multilingual_v2 (best quality, multilingual)
#   - eleven_turbo_v2 (faster, good quality)
#   - eleven_monolingual_v1 (English only)

# Voice stability (0.0 to 1.0)
ELEVENLABS_STABILITY = 0.5  # Higher = more consistent

# Similarity boost (0.0 to 1.0)
ELEVENLABS_SIMILARITY = 0.75  # Higher = more like original voice
```

## Script Cleaning

The system automatically cleans narration scripts before sending to ElevenLabs:

- Removes timing markers like `[0:00-0:08]`
- Removes section headers like `[INTRO]`, `[CONCLUSION]`
- Removes pause markers like `[PAUSE]`
- Cleans up extra whitespace

This ensures only the spoken text is sent to TTS.

## Quota and Limits

ElevenLabs has character-based quotas:

- **Free Tier**: 10,000 characters per month
- **Starter Tier**: 30,000 characters per month
- **Creator Tier**: 100,000 characters per month

Check your quota at: https://elevenlabs.io/app/settings

## Troubleshooting

### API Key Error

```
[ERROR] ELEVENLABS_API_KEY not set
```

**Solution**: Set your API key in config.py or as environment variable.

### Authentication Failed

```
[ERROR] ElevenLabs API authentication failed
```

**Solution**: Verify your API key is correct and active.

### Quota Exceeded

```
[ERROR] ElevenLabs API quota exceeded
```

**Solution**: Check your quota at https://elevenlabs.io/app/settings or upgrade your plan.

### Voice Not Found

```
[ERROR] Could not find voice 'VoiceName'
```

**Solution**: Use `--list-voices` to see available voices in your account.

### Requests Library Missing

```
[ERROR] requests library not installed
```

**Solution**: Install with `pip install requests`

## Advanced Usage

### Custom Voice Settings Per Project

```bash
# Professional narration
python core/main.py --idea "Corporate video" \
  --tts-method elevenlabs \
  --tts-voice "Rachel" \
  && export ELEVENLABS_STABILITY=0.8 \
  && export ELEVENLABS_SIMILARITY=0.9

# Dynamic narration
python core/main.py --idea "Action movie trailer" \
  --tts-method elevenlabs \
  --tts-voice "Clyde" \
  && export ELEVENLABS_STABILITY=0.3 \
  && export ELEVENLABS_SIMILARITY=0.6
```

## Comparison: ElevenLabs vs Alternatives

| Feature | ElevenLabs | edge-tts (local) | ComfyUI |
|---------|-----------|------------------|---------|
| Cost | Paid (free tier) | Free | Free |
| Quality | Best | Good | Variable |
| Speed | Fast | Fast | Variable |
| Voices | 100+ | 100+ | Depends |
| Offline | No | Yes | Yes |
| Setup | API key needed | pip install | Workflow needed |

## API Reference

### Text-to-Speech Endpoint

```
POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
```

**Headers:**
- `xi-api-key`: Your API key
- `Content-Type`: application/json
- `Accept`: audio/mpeg

**Body:**
```json
{
  "text": "Your narration text here",
  "model_id": "eleven_multilingual_v2",
  "voice_settings": {
    "stability": 0.5,
    "similarity_boost": 0.75
  }
}
```

For more information, see: https://elevenlabs.io/docs
