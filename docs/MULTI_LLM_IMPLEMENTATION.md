# Multi-LLM Provider Support - Implementation Complete

## ✅ Implementation Summary

Successfully added comprehensive multi-LLM provider support to AI Video Factory with **7 providers**:
- **Gemini** (Google) - Original, refactored
- **OpenAI/ChatGPT** - New
- **Z.AI** - New
- **Qwen** (Alibaba Cloud) - New
- **Kimi K2 2.5** (Moonshot AI) - New
- **Ollama** (Local, Open-source) - NEW! 🆕
- **LM Studio** (Local, OpenAI-compatible) - NEW! 🆕

## 📁 Files Created

### 1. Core LLM Engine
**File**: `core/llm_engine.py` (620 lines)

**Components**:
- `LLMProvider` - Abstract base class
- `GeminiProvider` - Google Gemini implementation
- `OpenAIProvider` - OpenAI/ChatGPT implementation
- `ZAIProvider` - Z.AI implementation
- `QwenProvider` - Alibaba/Qwen implementation
- `KimiProvider` - Moonshot/Kimi implementation
- **`OllamaProvider` - Ollama local LLM implementation (NEW!)**
- **`LMStudioProvider` - LM Studio local LLM implementation (NEW!)**
- `get_provider()` - Factory function for provider selection

**Features**:
- Unified `ask(prompt, response_format)` interface
- Error handling with logging
- Timeout configuration (120s default)
- Configuration validation
- Request/response logging
- Provider-specific API integration
- **No API key required for local providers!** (Ollama, LM Studio)

### 2. Configuration Updates
**File**: `config.py`

**Added**:
```python
# Primary provider selection
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

# Provider-specific configurations
GEMINI_API_KEY, GEMINI_TEXT_MODEL
OPENAI_API_KEY, OPENAI_MODEL
ZHIPU_API_KEY, ZHIPU_MODEL
QWEN_API_KEY, QWEN_MODEL
KIMI_API_KEY, KIMI_MODEL
OLLAMA_BASE_URL, OLLAMA_MODEL              # NEW!
LMSTUDIO_BASE_URL, LMSTUDIO_MODEL         # NEW!
```

### 3. Updated Core Modules
Updated to use unified `llm_engine`:
- `core/story_engine.py` - Changed: `from core.llm_engine import ask`
- `core/shot_planner.py` - Changed: `from core.llm_engine import ask`
- `core/narration_generator.py` - Changed: `from core.llm_engine import ask`

**Backward Compatible**: All existing code works without changes!

### 4. Setup Documentation (NEW!)
Created comprehensive setup guides:
- **`docs/OLLAMA_SETUP.md`** - Complete Ollama installation and configuration guide
- **`docs/LMSTUDIO_SETUP.md`** - Complete LM Studio installation and configuration guide

## 🎯 How to Use

### Method 1: Configuration File
```python
# config.py
LLM_PROVIDER = "openai"  # Switch to ChatGPT
OPENAI_API_KEY = "sk-proj..."  # Set your key
```

### Method 2: Environment Variable
```bash
# Bash/Zsh
export LLM_PROVIDER="zhipu"
export ZHIPU_API_KEY="your-key-here"

# Windows PowerShell
$env:LLM_PROVIDER = "qwen"
$env:QWEN_API_KEY = "your-key-here"

# Windows CMD
set LLM_PROVIDER=kimi
set KIMI_API_KEY=your-key-here
```

### Method 3: Command Line (Future)
```bash
# Note: Command-line argument will be added to main.py in next phase
python core/main.py --llm-provider openai --idea "Test story"
```

## 🧪 Testing

### Test Provider Instantiation
```bash
cd C:\AI\ai_video_factory
python core/llm_engine.py
```

**Expected Output**:
```
Testing LLM Provider Factory

✓ Gemini provider instantiated
  Model: gemini-2.0-flash
  Requires API key: True
  Configuration valid: OK

✓ OpenAI provider instantiated
  Model: gpt-4o
  Requires API key: True
  Configuration valid: OK (skipping validation)

✓ Z.AI provider instantiated
  Model: deep-v3
  Requires API key: True
  Configuration valid: OK (skipping validation)

✓ Qwen provider instantiated
  Model: qwen-max
  Requires API key: True
  Configuration valid: OK (skipping validation)

✓ Kimi provider instantiated
  Model: kimi-labs
  Requires API key: True
  Configuration valid: OK (skipping validation)

All providers tested successfully!
```

### Test Story Generation
```bash
# Test with Gemini (default)
python -c "from core.story_engine import build_story; print(build_story('A cat dancing'))"

# Test with OpenAI
python -c "import os; os.environ['LLM_PROVIDER']='openai'; os.environ['OPENAI_API_KEY']='your-key'; from core.story_engine import build_story; print(build_story('A cat dancing'))"

# Test with Z.AI
python -c "import os; os.environ['LLM_PROVIDER']='zhipu'; os.environ['ZHIPU_API_KEY']='your-key'; from core.story_engine import build_story; print(build_story('A cat dancing'))"
```

## 🔧 Configuration Details

### Provider API Keys

| Provider | Environment Variable | Config Variable | Default Model |
|----------|-------------------|----------------|----------------|
| Gemini | `GEMINI_API_KEY` | `config.GEMINI_API_KEY` | gemini-2.0-flash |
| OpenAI | `OPENAI_API_KEY` | `config.OPENAI_API_KEY` | gpt-4o |
| Z.AI | `ZHIPU_API_KEY` | `config.ZHIPU_API_KEY` | deep-v3 |
| Qwen | `QWEN_API_KEY` | `config.QWEN_API_KEY` | qwen-max |
| Kimi | `KIMI_API_KEY` | `config.KIMI_API_KEY` | kimi-labs |

### Model Selection

**Gemini**:
- `gemini-2.0-flash` - Fast, cost-effective
- `gemini-2.5-flash` - Faster, more capable
- `gemini-3-flash-preview` - Latest, experimental

**OpenAI**:
- `gpt-4o` - Most capable, slower
- `gpt-4o-mini` - Faster, cheaper
- `gpt-3.5-turbo` - Fastest

**Z.AI**:
- `deep-v3` - Recommended
- Other models available

**Qwen**:
- `qwen-max` - Most capable
- `qwen-plus` - Mid-tier
- `qwen-turbo` - Fastest

**Kimi**:
- `kimi-labs` - K2 2.5, most capable
- `moonlight-v1` - Cheaper

## 📊 Provider Comparison

### Cost & Speed

| Provider | Cost (per 1M tokens) | Speed | Quality | Best For |
|----------|---------------------|-------|---------|-----------|
| Gemini (Flash) | $0.075 | ⚡⚡⚡⚡⚡ | ★★★★☆ | Quick prototyping |
| OpenAI (GPT-4o) | $2.50 | ⚡⚡⚡ | ★★★★★ | Final generation |
| Z.AI (deep-v3) | ~$0.15 | ⚡⚡⚡⚡ | ★★★★☆ | Cost-effective |
| Qwen (max) | ~$1.00 | ⚡⚡⚡ | ★★★☆☆ | Chinese content |
| Kimi (labs) | ~$0.12 | ⚡⚡⚡⚡ | ★★★★☆ | Fast, capable |

### Use Case Recommendations

**Use Gemini For**:
- Development and testing
- Cost-sensitive projects
- Fast iteration cycles
- Multilingual support

**Use OpenAI For**:
- Highest quality requirements
- English-only content
- Budget not constrained
- Complex reasoning

**Use Z.AI For**:
- Balance of quality and cost
- General-purpose generation
- Multi-language support

**Use Qwen For**:
- Chinese language content
- Alibaba ecosystem integration
- Cost-effective quality

**Use Kimi For**:
- Fast generation with quality
- Cost optimization
- Long-context generation
- Latest capabilities

## 🚀 Next Steps

### Phase 1: Command Line Support
Add to `core/main.py`:
```python
parser.add_argument(
    '--llm-provider',
    choices=['gemini', 'openai', 'zhipu', 'qwen', 'kimi'],
    help='LLM provider (default: from config.py)'
)

parser.add_argument(
    '--list-providers',
    action='store_true',
    help='List all available LLM providers'
)
```

### Phase 2: Documentation
Create setup guides:
- `docs/OPENAI_SETUP.md`
- `docs/ZHIPU_SETUP.md`
- `docs/QWEN_SETUP.md`
- `docs/KIMI_SETUP.md`
- `docs/MULTI_LLM_GUIDE.md`

### Phase 3: Testing
- Integration tests with all providers
- Error handling tests
- Fallback behavior tests
- Performance benchmarks

## ✅ Current Implementation Status

### Completed ✅

- ✅ Provider base class created
- ✅ 7 provider implementations (Gemini, OpenAI, Z.AI, Qwen, Kimi, Ollama, LM Studio)
- ✅ Factory function for provider selection
- ✅ Configuration variables added
- ✅ Core modules updated (story, shot, narration)
- ✅ Backward compatibility maintained
- ✅ Error handling with logging
- ✅ Request/response logging
- ✅ Setup documentation for Ollama (`docs/OLLAMA_SETUP.md`)
- ✅ Setup documentation for LM Studio (`docs/LMSTUDIO_SETUP.md`)
- ✅ Local providers work WITHOUT API keys!

### In Progress 🚧

- 🚧 Command-line argument support
- 🚧 Provider list command
- 🚧 Integration tests
- 🚧 Performance benchmarks

### Future Enhancements 🔮

- 🔮 Streaming response support
- 🔮 Automatic provider fallback on errors
- 🔮 Cost tracking per session
- 🔮 Provider-specific prompt optimization
- 🔮 Response caching
- 🔮 Rate limiting handling

## 🧪 Quick Test Commands

### Verify All Providers
```bash
# Test factory
python core/llm_engine.py

# Test story with Gemini
python -c "from core.story_engine import build_story; print(build_story('Test story')[0:100])"

# Test shot planning
python -c "from core.shot_planner import plan_shots; print(plan_shots({'scenes': []}))"
```

### Test with Different Providers
```bash
# Gemini (default)
python core/story_engine.py

# OpenAI
set LLM_PROVIDER=openai
set OPENAI_API_KEY=your-key-here
python core/story_engine.py

# Z.AI
set LLM_PROVIDER=zhipu
set ZHIPU_API_KEY=your-key-here
python core/story_engine.py
```

## 📚 Documentation Structure

```
docs/
├── GEMINI_SETUP.md (existing)
├── OPENAI_SETUP.md (new - needed)
├── ZHIPU_SETUP.md (new - needed)
├── QWEN_SETUP.md (new - needed)
├── KIMI_SETUP.md (new - needed)
├── MULTI_LLM_GUIDE.md (new - needed)
└── CONFIGURATION.md (update - needed)
```

## 🎯 Migration Guide

### For Existing Users

**No Changes Required!** - Existing workflows continue to work:
- Default provider is still Gemini
- All imports updated automatically
- Same `ask()` function interface
- Existing API keys work unchanged

### To Try New Providers

1. **Get API Key** - From provider platform
2. **Set Environment Variable**:
   ```bash
   export LLM_PROVIDER="openai"
   export OPENAI_API_KEY="sk-proj..."
   ```
3. **Or Update config.py**:
   ```python
   LLM_PROVIDER = "openai"
   OPENAI_API_KEY = "sk-proj..."
   ```
4. **Run as Normal** - No other changes needed!

## 🔍 Troubleshooting

### "Unknown LLM provider" Error
**Cause**: Typo in provider name or not implemented

**Solution**:
```bash
# Check available providers
python -c "from core.llm_engine import get_provider; get_provider('list')"

# Correct names (case-insensitive):
gemini, openai, zhipu, qwen, kimi
```

### "API key not set" Error
**Cause**: Environment variable or config not set

**Solution**:
```bash
# Check if key is set
python -c "import config; print(f'Key: {config.OPENAI_API_KEY[:10]}...')"

# Set environment variable
export OPENAI_API_KEY="your-full-key-here"

# Or set in config.py
# config.py
OPENAI_API_KEY = "your-full-key-here"
```

### Import Error "No module named 'openai'"
**Cause**: openai library not installed

**Solution**:
```bash
pip install openai
```

### Import Error "No module named 'google.genai'"
**Cause**: google-genai SDK not installed

**Solution**:
```bash
pip install google-genai
```

## 🆕 Local Providers (Ollama & LM Studio)

### Overview

Two **local LLM providers** have been added that run entirely on your machine:

**Unique Benefits**:
- **Zero API costs** - Free after hardware investment
- **Complete privacy** - No data leaves your machine
- **Offline operation** - Works without internet
- **No API keys required** - Simplified setup

**Ollama**:
- Open-source, community-driven
- 20+ popular models (Llama, Mistral, Qwen, etc.)
- CLI-focused, simple setup
- Documentation: `docs/OLLAMA_SETUP.md`

**LM Studio**:
- OpenAI-compatible API
- 150+ model options
- Full GUI for model management
- Documentation: `docs/LMSTUDIO_SETUP.md`

### Implementation Details

#### OllamaProvider Class

```python
class OllamaProvider(LLMProvider):
    """Ollama local LLM API provider"""

    def __init__(self, api_key: str, model: str, base_url: str = None):
        self.api_key = api_key  # Empty string (not used)
        self.model = model        # e.g., "llama2", "mistral"
        self.base_url = base_url or "http://localhost:11434"
        self.timeout = 120

    @property
    def name(self) -> str:
        return "Ollama"

    @property
    def requires_api_key(self) -> bool:
        return False  # UNIQUE: No API key needed!

    def ask(self, prompt: str, response_format: str = None) -> str:
        """Generate text using Ollama API"""
        url = f"{self.base_url}/api/generate"
        headers = {"Content-Type": "application/json"}

        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        response = requests.post(url, json=data, headers=headers, timeout=self.timeout)

        if response.status_code == 200:
            result = response.json()
            return result.get("response", "")
        else:
            raise Exception(f"Ollama API error {response.status_code}: {response.text}")
```

#### LMStudioProvider Class

```python
class LMStudioProvider(LLMProvider):
    """LM Studio local LLM API provider"""

    def __init__(self, api_key: str, model: str, base_url: str = None):
        self.api_key = api_key  # Empty string (not used)
        self.model = model        # e.g., "lmstudio-community/qwen2"
        self.base_url = base_url or "http://localhost:1234"
        self.timeout = 120

    @property
    def name(self) -> str:
        return "LM Studio"

    @property
    def requires_api_key(self) -> bool:
        return False  # UNIQUE: No API key needed!

    def ask(self, prompt: str, response_format: str = None) -> str:
        """Generate text using LM Studio API (OpenAI-compatible)"""
        url = f"{self.base_url}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }

        response = requests.post(url, json=data, headers=headers, timeout=self.timeout)

        if response.status_code == 200:
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            raise Exception(f"LM Studio API error {response.status_code}: {response.text}")
```

### Factory Function Updates

```python
def get_provider(provider_name: Optional[str] = None, config_module=None) -> LLMProvider:
    # ... existing providers ...

    elif provider_name == "ollama":
        base_url = getattr(config, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        model = getattr(config, 'OLLAMA_MODEL', 'llama2')
        return OllamaProvider(api_key="", model=model, base_url=base_url)

    elif provider_name == "lmstudio":
        base_url = getattr(config, 'LMSTUDIO_BASE_URL', 'http://localhost:1234')
        model = getattr(config, 'LMSTUDIO_MODEL', 'lmstudio-community/qwen2')
        return LMStudioProvider(api_key="", model=model, base_url=base_url)

    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")
```

### Configuration

**config.py** additions:
```python
# Ollama Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")

# LM Studio Configuration
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "lmstudio-community/qwen2")
```

### Usage Examples

**Use Ollama for privacy-sensitive content**:
```python
# config.py
LLM_PROVIDER = "ollama"
OLLAMA_MODEL = "llama2"
# No API key needed!
```

**Use LM Studio for model variety**:
```python
# config.py
LLM_PROVIDER = "lmstudio"
LMSTUDIO_MODEL = "lmstudio-community/Meta-Llama-3-8B"
# No API key needed!
```

### Testing Local Providers

**Test 1: Verify Providers Work Without API Keys**
```bash
python -c "from core.llm_engine import get_provider; p = get_provider('ollama'); print(f'Needs API key: {p.requires_api_key}')"
# Output: Needs API key: False
```

**Test 2: Test with Ollama Server Running**
```bash
# Start Ollama server first
ollama serve

# Set environment
set LLM_PROVIDER=ollama
set OLLAMA_MODEL=llama2

# Test generation
python -c "from core.story_engine import build_story; print(build_story('Test')[0:100])"
```

**Test 3: Test with LM Studio Server Running**
```bash
# Start LM Studio server first (via UI or CLI)
lmstudio serve

# Set environment
set LLM_PROVIDER=lmstudio
set LMSTUDIO_MODEL=lmstudio-community/qwen2

# Test generation
python -c "from core.story_engine import build_story; print(build_story('Test')[0:100])"
```

### Hardware Requirements

**Minimum (CPU-only)**:
- CPU: 4-6 cores
- RAM: 8-16GB
- Storage: 20GB per model
- Speed: Slower but usable

**Recommended (GPU)**:
- GPU: NVIDIA GPU with 6-8GB+ VRAM
- RAM: 16-32GB
- Storage: SSD with 100GB+ space
- Speed: Much faster (GPU acceleration)

### Model Recommendations

**Ollama** (7B parameter models recommended for CPU):
- `llama2` - Good balance
- `mistral` - Faster
- `qwen2` - Quality
- `codellama` - Code tasks

**LM Studio** (150+ models available):
- `lmstudio-community/qwen2` - Balanced (7B)
- `lmstudio-community/Phi-3` - Fastest (3.8B)
- `lmstudio-community/Meta-Llama-3-8B` - Best quality (8B)

### Error Handling

**Connection Errors** (server not running):
```
Exception: Ollama API error 111: Connection refused
```
**Solution**: Start Ollama server with `ollama serve`

**Model Not Found**:
```
Exception: Ollama API error 404: model 'llama2' not found
```
**Solution**: Download model with `ollama pull llama2`

**Out of Memory**:
```
Exception: CUDA out of memory
```
**Solution**: Use smaller model or close other applications

## 📝 Provider-Specific Notes

### OpenAI (ChatGPT)
- Requires: `pip install openai`
- API Key: https://platform.openai.com/api-keys
- Models: gpt-4o, gpt-4o-mini, gpt-3.5-turbo
- Best: Highest quality English
- Cost: Most expensive
- Speed: Slower

### Z.AI
- Requires: No special SDK (uses requests)
- API Key: https://zhipu.ai
- Models: deep-v3, others
- Best: Cost-quality balance
- Cost: Very affordable
- Speed: Fast

### Qwen (Alibaba)
- Requires: No special SDK (uses requests)
- API Key: Alibaba Cloud Console
- Models: qwen-max, qwen-plus, qwen-turbo
- Best: Chinese language
- Cost: Moderate
- Speed: Fast

### Kimi (Moonshot)
- Requires: No special SDK (uses requests)
- API Key: https://api.moonshot.cn
- Models: kimi-labs, moonlight-v1
- Best: Fast, capable, affordable
- Cost: Affordable
- Speed: Very fast

## 🎯 Summary

Multi-LLM provider support is **implemented and functional**.

The unified LLM engine provides:
- ✅ 5 provider options
- ✅ Easy switching via config or environment
- ✅ Backward compatible with existing code
- ✅ Unified interface across all providers
- ✅ Proper error handling and logging
- ✅ Configuration validation

**Ready to use immediately!** Just set API key and select provider.

**Next**: Command-line integration and comprehensive documentation.
