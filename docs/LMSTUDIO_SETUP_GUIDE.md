# LM Studio Setup Guide

## Status: Not Running

LM Studio is not accessible at `http://localhost:1234`

## What is LM Studio?

LM Studio is a **free, local LLM application** that:
- Runs AI models on your computer (no API costs)
- Works offline after downloading models
- Has OpenAI-compatible API
- No rate limits or quotas

## Setup Instructions

### Step 1: Download LM Studio

1. Visit: https://lmstudio.ai/
2. Download the Windows version
3. Install the application

### Step 2: Load a Model

1. Open LM Studio application
2. Click on "AI" or search for models
3. Search for: `gpt-oss-20b` or any other model you prefer
4. Click "Download" next to the model
   - Models are large (10-20GB+)
   - Download time depends on your internet speed
5. Once downloaded, click "Run" or "Load"

### Step 3: Enable the API Server

1. In LM Studio, look for a "Server" or "API" button (usually in the sidebar)
2. Click on it to open the server settings
3. Make sure these settings:
   - **Port**: 1234 (or note the port if different)
   - **CORS**: Enable if needed
4. Click "Start Server" or toggle it on
5. You should see "Server running at http://localhost:1234"

### Step 4: Verify Connection

Once LM Studio is running with the API server enabled:

```bash
# Test the connection
python test_lmstudio.py
```

You should see:
```
[OK] Server is running!
Available models: 1
  - lmstudio-community/gpt-oss-20b

[OK] Text generation successful!
Response: SUCCESS
```

### Step 5: Use in Your Application

Update your `.env` file:

```bash
# Use LM Studio as your LLM provider
LLM_PROVIDER=lmstudio

# LM Studio configuration
LMSTUDIO_BASE_URL=http://localhost:1234
LMSTUDIO_MODEL=lmstudio-community/gpt-oss-20b
```

Then run your application:
```bash
python core/main.py
```

## Troubleshooting

### Issue: "Cannot connect to LM Studio"

**Solution**:
1. Make sure LM Studio application is open
2. Make sure the API server is started (look for "Server" button)
3. Check the port number (default is 1234)
4. Check Windows Firewall - may need to allow LM Studio

### Issue: "Model not found"

**Solution**:
1. In LM Studio, check what model is loaded
2. Go to the "AI" or "Models" section
3. Download and load the model
4. Update `LMSTUDIO_MODEL` in `.env` to match exactly

### Issue: Very slow responses

**Solution**:
1. Check your system resources (CPU/GPU/RAM)
2. Try a smaller model (e.g., 7B instead of 20B)
3. Make sure GPU acceleration is enabled in LM Studio settings
4. Close other applications to free up resources

## Alternative: Ollama

If LM Studio doesn't work for you, try **Ollama**:
- Download: https://ollama.com/
- Runs locally like LM Studio
- Command-line based
- Also free and no API limits

## Recommended Models

For LM Studio, these models work well:
- `gpt-oss-20b` - Large, capable
- `lmstudio-community/Meta-Llama-3.1-8B-Instruct` - Medium size
- `lmstudio-community/Mistral-7B-Instruct-v0.3` - Fast, good quality
- `lmstudio-community/Qwen2.5-7B-Instruct` - Excellent multilingual

## Current Configuration

```
Provider: LM Studio (lmstudio)
Base URL: http://localhost:1234
Model: lmstudio-community/gpt-oss-20b
Status: Not running
```

## Next Steps

1. ✓ Install LM Studio (if not installed)
2. ✓ Load a model in LM Studio
3. ✓ Enable the API server
4. ✓ Run: `python test_lmstudio.py`
5. ✓ If test passes, update `.env`: `LLM_PROVIDER=lmstudio`
6. ✓ Run: `python core/main.py`

## Advantages of LM Studio

✓ **Free** - No API costs
✓ **Private** - Runs locally on your machine
✓ **No limits** - Unlimited requests
✓ **Offline** - Works without internet after model download
✓ **Flexible** - Try many different models

## Disadvantages

✗ Slower than cloud APIs (depends on your hardware)
✗ Requires good computer specs (RAM, GPU)
✗ Large model downloads (10-20GB+ per model)
✗ Need to keep LM Studio open while using

---

**Links**:
- LM Studio: https://lmstudio.ai/
- Models: https://lmstudio.ai/models
