"""
pytest configuration and shared fixtures
"""
import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Manual verification scripts excluded from pytest collection. They require
# live services (LLM providers, the web backend on :8000, ComfyUI, Gemini Flow
# browser automation) or are scratch/stale files. Run them directly instead,
# e.g. `python tests/test_queue.py`.
collect_ignore = [
    # Live web backend
    "test_api_endpoints.py",
    "test_assets_api.py",
    "test_queue.py",
    "test_req.py",
    # Live LLM providers
    "test_asmr_engine.py",
    "test_json_formatting.py",
    "test_multi_scene.py",
    "test_video_length_agents.py",
    "test_pov_agents.py",
    # Live ComfyUI / Gemini Flow / browser automation
    "test_dl.py",
    "test_flow.py",
    "test_flow_download.py",
    "test_flow_e2e.py",
    "test_gem.py",
    "test_gs.py",
    "test_playwright_direct.py",
    "test_threads.py",
    # Scratch / stale
    "test_ws.py",                     # UTF-16 encoded ComfyUI websocket scratch script
    "test_departure_video_logic.py",  # imports removed web_ui...session_service module
    # Integration scripts (live providers; run directly with python)
    "integration/test_gemini.py",
    "integration/test_image_generation.py",
    "integration/test_lmstudio.py",
    "integration/test_setup.py",
    "integration/test_zai_correct.py",
    "integration/test_zhipu.py",
    "integration/test_zhipu_endpoints.py",
    "integration/test_zhipu_models.py",
]


# Shared fixtures for tests can be added here

def temp_output_dir(tmp_path):
    """Fixture providing temporary output directory for tests"""
    return tmp_path
