# Local LLM Providers - Quick Start Guide

## 🆕 New Feature: Local LLM Support

AI Video Factory now supports **three local LLM providers** that run entirely on your machine:

## Available Providers

### 1. Ollama (Open-source, CLI-focused)

**Setup Guide**: See `docs/OLLAMA_SETUP.md`

**Quick Install**:
```bash
# 1. Download from https://ollama.com
# 2. Install and run server
ollama serve

# 3. Download a model
ollama pull llama2

# 4. Configure AI Video Factory
# In config.py:
LLM_PROVIDER = "ollama"
OLLAMA_MODEL = "llama2"
```

**Models**: llama2, mistral, qwen2, codellama, llama3, and more

### 3. Strata (OpenAI-compatible, local server)

**Quick Install**:
```bash
# 1. Start your Strata local server (default: http://127.0.0.1:8080)

# 2. Configure AI Video Factory
# In Settings -> LLM Providers, pick "Strata (Local)" and set the
# model name your server exposes, or via config.py:
LLM_PROVIDER = "strata"
STRATA_BASE_URL = "http://127.0.0.1:8080"
STRATA_MODEL = "strata"
```

**Thinking control**: like LM Studio, the configured thinking level is passed
through as `reasoning_effort` on `/v1/chat/completions` (Default sends nothing).

### 2. LM Studio (OpenAI-compatible, GUI-focused)

**Setup Guide**: See `docs/LMSTUDIO_SETUP.md`

**Quick Install**:
```bash
# 1. Download from https://lmstudio.ai
# 2. Install application
# 3. Start server (via UI or CLI)
lmstudio serve

# 4. Configure AI Video Factory
# In config.py:
LLM_PROVIDER = "lmstudio"
LMSTUDIO_MODEL = "lmstudio-community/qwen2"
```

**Models**: 150+ models including Qwen, Llama, Mistral, Phi, and more

## Key Benefits

### ✅ Privacy
- **100% Local** - All prompts and responses stay on your machine
- **No data sent to cloud** - Complete privacy for sensitive content
- **Audit control** - Full visibility into all operations

### ✅ Cost
- **Zero API fees** - Free after hardware investment
- **Best for development** - Test and iterate without costs
- **Production savings** - Use local for dev, cloud for final output

### ✅ Offline
- **No internet required** - Works completely offline
- **Air-gapped compatible** - Secure environments
- **Reliable** - No third-party outages

### ✅ No API Keys!
- **Simplified setup** - No API key management needed
- **Reduced attack surface** - No credentials to store/protect
- **Easy configuration** - Just set provider name and model

## Comparison

| Feature | Ollama | LM Studio | Cloud Providers |
|---------|---------|-----------|-----------------|
| **Cost** | FREE | FREE | Pay-per-token |
| **Privacy** | ⭐⭐⭐ (local) | ⭐⭐⭐ (local) | ⭐⭐ (cloud) |
| **Setup** | Easy (CLI) | Easy (GUI) | Easiest |
| **Models** | 20+ | 150+ | Provider-specific |
| **Offline** | ✅ Yes | ✅ Yes | ❌ No |
| **API Key** | ❌ Not needed | ❌ Not needed | ✅ Required |
| **Speed** | Hardware-dependent | Hardware-dependent | Network-dependent |

## When to Use Local Providers ✅

- **Development & Testing** - Free iteration
- **Privacy-Sensitive Content** - Medical, legal, proprietary
- **Offline Environments** - No internet available
- **Cost Optimization** - Reduce cloud API costs
- **Custom Models** - Use finetuned/private models
- **Air-Gapped Systems** - Secure facilities

## When to Use Cloud Providers ☁️

- **Production** - Need guaranteed reliability
- **No GPU** - Limited local hardware
- **Best Quality** - State-of-the-art models (GPT-4, etc.)
- **Simple Setup** - Don't want to manage servers

## Quick Test

### Test Ollama (server must be running)
```bash
# Start Ollama server
ollama serve

# Test with AI Video Factory
set LLM_PROVIDER=ollama
set OLLAMA_MODEL=llama2
python -c "from core.story_engine import build_story; print(build_story('A cat dancing')[0:100])"
```

### Test LM Studio (server must be running)
```bash
# Start LM Studio server (via UI or CLI)
lmstudio serve

# Test with AI Video Factory
set LLM_PROVIDER=lmstudio
set LMSTUDIO_MODEL=lmstudio-community/qwen2
python -c "from core.story_engine import build_story; print(build_story('A cat dancing')[0:100])"
```

## Verification

### Test Factory Instantiation
```bash
python -c "from core.llm_engine import get_provider; p = get_provider('ollama'); print(f'{p.name}: API Key Required = {p.requires_api_key}')"
# Output: Ollama: API Key Required = False
```

### Test All Providers
```bash
python core/llm_engine.py
# Should show all 7 providers (5 cloud + 2 local)
```

## Configuration Examples

### Example 1: Development with Ollama
```python
# config.py
LLM_PROVIDER = "ollama"
OLLAMA_MODEL = "mistral"  # Fast for iteration
OLLAMA_BASE_URL = "http://localhost:11434"
```

### Example 2: High-Quality with LM Studio
```python
# config.py
LLM_PROVIDER = "lmstudio"
LMSTUDIO_MODEL = "lmstudio-community/Meta-Llama-3-8B"
LMSTUDIO_BASE_URL = "http://localhost:1234"
```

### Example 3: Hybrid Approach
```python
# Development: Use Ollama (free)
LLM_PROVIDER = "ollama"

# Production: Switch to OpenAI (quality)
# LLM_PROVIDER = "openai"
# OPENAI_API_KEY = "sk-proj..."
```

## Hardware Recommendations

### Minimum (CPU-only)
- **CPU**: 4-6 cores
- **RAM**: 8-16GB
- **Storage**: 20GB SSD
- **Models**: Use 7B or smaller
- **Speed**: Slower but usable

### Recommended (GPU)
- **GPU**: NVIDIA with 6-8GB+ VRAM
- **RAM**: 16-32GB
- **Storage**: 100GB+ SSD
- **Models**: 7B-70B
- **Speed**: Much faster

## Troubleshooting

### "Connection refused" Error
**Cause**: Server not running

**Solution**:
- Ollama: `ollama serve`
- LM Studio: Start via application UI

### "Model not found" Error
**Cause**: Model not downloaded

**Solution**:
- Ollama: `ollama pull llama2`
- LM Studio: Download via application UI

### Slow Generation
**Cause**: CPU-only inference

**Solutions**:
1. Use smaller model (Phi-3, mistral)
2. Enable GPU acceleration
3. Reduce prompt length
4. Close background applications

## Next Steps

1. **Choose provider**: Ollama (CLI) or LM Studio (GUI)
2. **Install software**: Download from official website
3. **Download model**: Pull model via CLI or GUI
4. **Start server**: Run server (background or foreground)
5. **Configure**: Update `config.py` or set environment variables
6. **Test**: Run quick test commands above

## Documentation

- **Ollama Full Guide**: `docs/OLLAMA_SETUP.md`
- **LM Studio Full Guide**: `docs/LMSTUDIO_SETUP.md`
- **Multi-LLM Summary**: `MULTI_LLM_SUMMARY.md`
- **Implementation Details**: `MULTI_LLM_IMPLEMENTATION.md`

## Summary

**Local LLM providers are now fully functional!**

- ✅ Ollama provider implemented
- ✅ LM Studio provider implemented
- ✅ No API keys required
- ✅ Complete documentation
- ✅ Privacy-friendly
- ✅ Cost-free (after hardware)
- ✅ Offline capable

**Ready to use!** Just install the software, start the server, and configure.

Choose **Ollama** for simplicity and CLI workflow.
Choose **LM Studio** for GUI and more model options.

Both provide excellent privacy and cost savings! 🎉
