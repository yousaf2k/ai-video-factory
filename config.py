"""
Configuration for AI Film Studio System
"""
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file in the same directory as config.py
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=True)

# Import secrets management for decryption
from core.secrets import decrypt_env_var

# ==========================================
# LLM PROVIDER CONFIGURATION
# ==========================================
# Primary LLM provider (gemini, openai, zhipu, qwen, kimi, ollama, lmstudio)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")

# Maximum tokens for LLM responses (increase for large JSON outputs)
# Set higher to avoid truncation when generating many shots
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "16384"))  # Default: 16K tokens

# Batch size for generating shots (process scenes in batches to avoid truncation)
SHOT_GENERATION_BATCH_SIZE = int(os.getenv("SHOT_GENERATION_BATCH_SIZE", "1"))  # Process 1 scenes at a time to prevent LLM context errors

# Maximum parallel threads for batch processing (only for cloud providers, not local models)
# Higher values = faster processing but more API rate limits
# Recommended: 3-5 for most APIs, 1-2 for free tier accounts
MAX_PARALLEL_BATCH_THREADS = int(os.getenv("MAX_PARALLEL_BATCH_THREADS", "5"))  # Default: 5 parallel threads

# Maximum concurrent generations in the background queue per engine type
# This allows separate limits for different backends (useful for local GPUs vs cloud APIs)
CONCURRENT_GENERATION_LIMITS = {
    "comfyui": int(os.getenv("CONCURRENT_COMFYUI_LIMIT", "1")),     # ComfyUI is VRAM heavy
    "gemini": int(os.getenv("CONCURRENT_GEMINI_LIMIT", "2")),       # Gemini API can handle more
    "geminiweb": int(os.getenv("CONCURRENT_GEMINIWEB_LIMIT", "1")), # Browser automation is heavy
    "default": int(os.getenv("CONCURRENT_DEFAULT_LIMIT", "1"))      # Fallback for other engines
}

# Legacy limit for backwards compatibility
CONCURRENT_GENERATION_LIMIT = int(os.getenv("CONCURRENT_GENERATION_LIMIT", "1"))  # Default: 1 concurrent generations

# ==========================================
# GEMINI API CONFIGURATION
# ==========================================
# Get your API key from: https://ai.google.dev/
GEMINI_API_KEY = decrypt_env_var("GEMINI_API_KEY", "")

# Text generation model (for story, shots, etc. "gemini-2.0-flash" and "gemini-3-flash-preview" is faster and cheaper, "gemini-3-pro-preview" is higher quality but more expensive)
GEMINI_TEXT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

# ==========================================
# OPENAI (CHATGPT) CONFIGURATION
# ==========================================
# Get your API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY = decrypt_env_var("OPENAI_API_KEY", "")

# ChatGPT model (gpt-4o is latest, gpt-4o-mini is faster/cheaper)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# ==========================================
# ZHIPU CONFIGURATION
# ==========================================
# Get your API key from Z.AI platform
ZHIPU_API_KEY = decrypt_env_var("ZHIPU_API_KEY", "")


# ==========================================
# QWEN (ALIBABA CLOUD) CONFIGURATION
# ==========================================
# Get your API key from Alibaba Cloud
QWEN_API_KEY = decrypt_env_var("QWEN_API_KEY", "")

# Qwen model (qwen-max is latest)
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-max")

# ==========================================
# KIMI (MOONSHOT) CONFIGURATION
# ==========================================
# Get your API key from Moonshot AI
KIMI_API_KEY = decrypt_env_var("KIMI_API_KEY", "")

# Kimi K2 2.5 model (kimi-labs is recommended)
KIMI_MODEL = os.getenv("KIMI_MODEL", "kimi-labs")

# ==========================================
# OLLAMA CONFIGURATION (Local LLM)
# ==========================================
# Ollama server URL (default: localhost:11434)
# Download Ollama from: https://ollama.com
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Model to use (e.g., llama2, mistral, codellama, qwen2, etc.)
# List available models: ollama list
# Download models: ollama pull <model-name>
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")

# ==========================================
# LM STUDIO CONFIGURATION (Local LLM)
# ==========================================
# LM Studio server URL (default: localhost:1234)
# Download LM Studio from: https://lmstudio.ai
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234")

# Model to use (e.g., lmstudio-community/qwen2, etc.)
# Models are managed in LM Studio application
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "lmstudio-community/qwen2")

# Image generation model (NanoBanana Pro)
GEMINI_IMAGE_MODEL = "gemini-3-pro-image-preview"

# ==========================================
# SYSTEM PATHS CONFIGURATION
# ==========================================
# Project root directory (absolute path to the folder containing this config.py)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Global output directory
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

# Projects directory (where project data is stored)
PROJECTS_DIR = os.path.join(OUTPUT_DIR, "projects")

# Helper to resolve relative paths to project root or output dir
def resolve_path(relative_path):
    if not relative_path:
        return relative_path
    if os.path.isabs(relative_path):
        return relative_path
        
    # Standardize to forward slashes for prefix checking
    norm_rel = relative_path.replace('\\', '/')
    
    # If the path starts with "output/", try to resolve it relative to where OUTPUT_DIR is
    # This handles cases where OUTPUT_DIR is on a different drive than PROJECT_ROOT
    if norm_rel.startswith('output/'):
        if os.path.isabs(OUTPUT_DIR):
            # Resolve relative to the parent of OUTPUT_DIR
            # e.g., if OUTPUT_DIR is E:/output, parent is E:/
            # joining E:/ with output/projects/xxx/shot.png correctly resolves it
            output_parent = os.path.dirname(OUTPUT_DIR)
            return os.path.join(output_parent, relative_path)
            
    return os.path.join(PROJECT_ROOT, relative_path)

# Absolute versions of directories
ABS_OUTPUT_DIR = resolve_path(OUTPUT_DIR)
ABS_PROJECTS_DIR = resolve_path(PROJECTS_DIR)

# ==========================================
# CONFIGURATION UTILITY WRAPPERS
# ==========================================
# These wrapper functions provide convenient access to utility functions
# with config values pre-filled, maintaining backward compatibility

def get_max_shots_from_config():
    """
    Wrapper that calls calculate_max_shots_from_config with current config values.
    
    Returns:
        int or None: Maximum number of shots, or None for no limit
    """
    from core.config_utils import calculate_max_shots_from_config as _calculate_max_shots
    return _calculate_max_shots(
        default_max_shots=DEFAULT_MAX_SHOTS,
        target_video_length=TARGET_VIDEO_LENGTH,
        default_shot_length=DEFAULT_SHOT_LENGTH
    )


def get_image_dimensions():
    """
    Wrapper that calls calculate_image_dimensions with current config values.
    
    Returns:
        Tuple of (width, height) as integers
    """
    from core.config_utils import calculate_image_dimensions as _calculate_image_dims
    return _calculate_image_dims(
        aspect_ratio=IMAGE_ASPECT_RATIO,
        resolution=IMAGE_RESOLUTION
    )


def get_video_dimensions():
    """
    Wrapper that calls calculate_video_dimensions with current config values.
    
    Returns:
        Tuple of (width, height) as integers
    """
    from core.config_utils import calculate_video_dimensions as _calculate_video_dims
    return _calculate_video_dims(
        aspect_ratio=VIDEO_ASPECT_RATIO,
        resolution=VIDEO_RESOLUTION
    )


# Backward compatibility - original function names
def calculate_max_shots_from_config():
    """
    Calculate maximum number of shots from configuration settings.
    
    This is a wrapper that maintains backward compatibility with existing code.
    
    Returns:
        int or None: Maximum number of shots, or None for no limit
    """
    return get_max_shots_from_config()


def calculate_image_dimensions(aspect_ratio=None, resolution=None):
    """
    Calculate image width and height from aspect ratio and resolution.
    
    Args:
        aspect_ratio: String like "16:9", "9:16", "1:1", "4:3", "3:4" (uses IMAGE_ASPECT_RATIO if None)
        resolution: String like "512", "1024", "2048" (uses IMAGE_RESOLUTION if None)
    
    Returns:
        Tuple of (width, height) as integers
    """
    if aspect_ratio is None:
        aspect_ratio = IMAGE_ASPECT_RATIO
    if resolution is None:
        resolution = IMAGE_RESOLUTION
    
    from core.config_utils import calculate_image_dimensions as _calculate_image_dims
    return _calculate_image_dims(aspect_ratio, resolution)


def calculate_video_dimensions(aspect_ratio=None, resolution=None, draft_low_res_video=False):
    """
    Calculate video width and height from aspect ratio and resolution.
    
    Args:
        aspect_ratio: String like "16:9", "9:16", "1:1", "4:3", "3:4" (uses VIDEO_ASPECT_RATIO if None)
        resolution: String like "512", "720", "1024", "1080", "1280", "2048" (uses VIDEO_RESOLUTION if None)
        draft_low_res_video: Generate at half resolution
    
    Returns:
        Tuple of (width, height) as integers
    """
    if aspect_ratio is None:
        aspect_ratio = VIDEO_ASPECT_RATIO
    if resolution is None:
        resolution = VIDEO_RESOLUTION
    
    from core.config_utils import calculate_video_dimensions as _calculate_video_dims
    return _calculate_video_dims(aspect_ratio, resolution, draft_low_res_video=draft_low_res_video)

# ==========================================
# COMFYUI CONFIGURATION
# ==========================================
# ComfyUI server URL
COMFY_URL = "http://127.0.0.1:8188"

# ComfyUI output directory (where ComfyUI saves generated videos/images)
# Set this if ComfyUI is installed in a different location
# Leave as empty string "" to auto-detect from ComfyUI API
# Examples:
#   COMFY_OUTPUT_DIR = ""  # Auto-detect (recommended)
#   COMFY_OUTPUT_DIR = "C:/ComfyUI/output"  # Manual path for Windows
#   COMFY_OUTPUT_DIR = "/home/user/ComfyUI/output"  # Manual path for Linux/Mac
COMFY_OUTPUT_DIR = os.getenv("COMFY_OUTPUT_DIR", r"E:\ComfyUI\Output")

# ComfyUI input directory (where ComfyUI loads input images)
# Set this if ComfyUI is installed in a different location
# Leave as empty string "" to auto-detect from ComfyUI API
# Examples:
#   COMFY_INPUT_DIR = ""  # Auto-detect (recommended)
#   COMFY_INPUT_DIR = "C:/ComfyUI/input"  # Manual path for Windows
COMFY_INPUT_DIR = os.getenv("COMFY_INPUT_DIR", "")


# ==========================================
# VIDEO WORKFLOW CONFIGURATION
# ==========================================
# Active video workflow to use (must exist in VIDEO_WORKFLOWS)
VIDEO_WORKFLOW = "wan22_workflow"

# Video workflow definitions
# Each workflow is auto-detected from the workflow/video directory
VIDEO_WORKFLOWS = {}

# ==========================================
# DYNAMIC VIDEO WORKFLOW DISCOVERY
# ==========================================
# Auto-discover any new video workflows in the workflow/video directory
# Uses Node Title Tags (e.g., "[prompt]", "[image_in]", "[video_out]") or smart heuristics
_video_workflow_dir = resolve_path("workflow/video")
if os.path.exists(_video_workflow_dir):
    for _wf_file in os.listdir(_video_workflow_dir):
        if _wf_file.endswith(".json"):
            _wf_key = os.path.splitext(_wf_file)[0]
            if _wf_key not in VIDEO_WORKFLOWS:
                _wf_path = os.path.join(_video_workflow_dir, _wf_file)
                try:
                    with open(_wf_path, "r", encoding="utf-8") as _f:
                        _wf_raw = json.load(_f)
                    
                    # Normalize workflow format (API JSON vs Workflow JSON)
                    _wf_nodes = {}
                    if "nodes" in _wf_raw and isinstance(_wf_raw["nodes"], list):
                        # Workflow JSON format
                        _links = {}
                        if "links" in _wf_raw and isinstance(_wf_raw["links"], list):
                            for _l in _wf_raw["links"]:
                                # Link: [id, origin_id, origin_slot, target_id, target_slot, type]
                                if len(_l) >= 2:
                                    _links[_l[0]] = [_l[1], _l[2]]
                                    
                        for _n in _wf_raw["nodes"]:
                            _n_id = str(_n.get("id", ""))
                            if _n_id:
                                _node_inputs = {}
                                # Convert UI links to API-style inputs for tracing
                                if "inputs" in _n and isinstance(_n["inputs"], list):
                                    for _inp in _n["inputs"]:
                                        _name = _inp.get("name")
                                        _link_id = _inp.get("link")
                                        if _name and _link_id in _links:
                                            _node_inputs[_name] = _links[_link_id]
                                            
                                _wf_nodes[_n_id] = {
                                    "class_type": _n.get("type", ""),
                                    "inputs": _node_inputs,
                                    "_meta": {"title": _n.get("title", "")}
                                }
                    elif isinstance(_wf_raw, dict):
                        # API JSON format
                        _wf_nodes = _wf_raw
                    
                    _load_image_node_id = None
                    _load_image_first_node_id = None
                    _load_image_last_node_id = None
                    _motion_prompt_node_id = None
                    _wan_video_node_id = None
                    _seed_node_id = None
                    
                    _load_image_candidates = []
                    _text_encode_candidates = []
                    _video_gen_candidates = []
                    _seed_candidates = []
                    
                    # 1. First pass: strict tag matching and gathering candidates
                    for _n_id, _n_data in _wf_nodes.items():
                        if not isinstance(_n_data, dict): continue
                        _title = _n_data.get("_meta", {}).get("title", "")
                        if not _title: _title = ""
                        _title = _title.lower()
                        _class_type = _n_data.get("class_type", "")
                        
                        # Explicit title tag discovery
                        if "[motion_prompt]" in _title or "[prompt]" in _title:
                            _motion_prompt_node_id = _n_id
                        elif "[image_in_first]" in _title:
                            _load_image_first_node_id = _n_id
                        elif "[image_in_last]" in _title:
                            _load_image_last_node_id = _n_id
                        elif "[image_in]" in _title:
                            _load_image_node_id = _n_id
                        elif "[video_out]" in _title or "[video_gen]" in _title:
                            _wan_video_node_id = _n_id
                        elif "[seed]" in _title:
                            _seed_node_id = _n_id
                            
                        # Candidate gathering for heuristics
                        if "LoadImage" == _class_type:
                            _load_image_candidates.append(_n_id)
                        if "CLIPTextEncode" == _class_type:
                            _text_encode_candidates.append((_n_id, _title))
                        if any(x in _class_type for x in ["WanImageToVideo", "WanVideoTextToVideo", "WanVideoSampler", "WanSampler", "WanVideoGenerator", "WanFirstLastFrameToVideo", "WanVideoFirstLastFrameToVideo"]):
                            # Prioritize specialized Wan nodes
                            _video_gen_candidates.insert(0, _n_id)
                        elif "Sampler" in _class_type or "KSampler" in _class_type:
                            _video_gen_candidates.append(_n_id)
                        if any(x in _class_type for x in ["Seed", "RandomNoise", "KSamplerAdvanced", "KSampler (Advanced)"]):
                            _seed_candidates.append(_n_id)
                    
                    # 2. Second pass: Tracing connections from the identified Video Sampler
                    # This is much more robust than title matching
                    if not _wan_video_node_id and _video_gen_candidates:
                        _wan_video_node_id = _video_gen_candidates[0]
                        
                    if _wan_video_node_id:
                        _sampler_node = _wf_nodes.get(_wan_video_node_id)
                        _inputs = _sampler_node.get("inputs", {})
                        
                        # Trace Positive Prompt (Motion Prompt)
                        if not _motion_prompt_node_id and "positive" in _inputs:
                            _p_val = _inputs["positive"]
                            if isinstance(_p_val, list) and len(_p_val) > 0:
                                _motion_prompt_node_id = str(_p_val[0])
                        
                        # Trace Load Image
                        if not _load_image_node_id and not _load_image_first_node_id:
                            for _img_input in ["start_image", "image", "pixels"]:
                                if _img_input in _inputs:
                                    _i_val = _inputs[_img_input]
                                    if isinstance(_i_val, list) and len(_i_val) > 0:
                                        _load_image_node_id = str(_i_val[0])
                                        break

                    # 3. Third pass: Heuristics fallbacks for missing IDs
                    # Text/Motion Prompt: Look for nodes called "prompt" or "motion"
                    if not _motion_prompt_node_id:
                        _motion_filter = [c[0] for c in _text_encode_candidates if "motion" in c[1] or "prompt" in c[1]]
                        # Exclude likely negative prompts
                        _motion_filter = [c for c in _motion_filter if "negative" not in _wf_nodes[c].get("_meta", {}).get("title", "").lower()]
                        if _motion_filter:
                            _motion_prompt_node_id = _motion_filter[0]
                        elif len(_text_encode_candidates) > 0:
                            _motion_prompt_node_id = _text_encode_candidates[0][0]

                    # Image Loaders:
                    if not _load_image_node_id and not _load_image_first_node_id:
                        if len(_load_image_candidates) == 1:
                            _load_image_node_id = _load_image_candidates[0]
                        elif len(_load_image_candidates) == 2:
                            _load_image_first_node_id = _load_image_candidates[0]
                            _load_image_last_node_id = _load_image_candidates[1]
                            
                    # Seed: Use first candidate as per user request
                    if not _seed_node_id and _seed_candidates:
                        _seed_node_id = _seed_candidates[0]

                    # Detect if this is an FLFI2V workflow
                    _is_flfi2v = "flf2v" in _wf_key.lower() or "flfi2v" in _wf_key.lower()

                    # Always add the workflow if it was parseable
                    _detected_wf = {
                        "workflow_path": _wf_path,
                        "description": f"Auto-detected workflow: {_wf_key}",
                        "is_flfi2v": _is_flfi2v
                    }
                    if _load_image_node_id: _detected_wf["load_image_node_id"] = _load_image_node_id
                    if _load_image_first_node_id: _detected_wf["load_image_first_node_id"] = _load_image_first_node_id
                    if _load_image_last_node_id: _detected_wf["load_image_last_node_id"] = _load_image_last_node_id
                    if _motion_prompt_node_id: _detected_wf["motion_prompt_node_id"] = _motion_prompt_node_id
                    if _wan_video_node_id: _detected_wf["wan_video_node_id"] = _wan_video_node_id
                    if _seed_node_id: _detected_wf["seed_node_id"] = _seed_node_id
                    
                    VIDEO_WORKFLOWS[_wf_key] = _detected_wf
                        
                except Exception as e:
                    # Silently skip unparseable files
                    pass

# Legacy Key Mapping & Defaults
# Resolve wan22_flfi2v to any discovered FLFI2V workflow
if "wan22_flfi2v" not in VIDEO_WORKFLOWS:
    _fl_candidates = [k for k, v in VIDEO_WORKFLOWS.items() if v.get("is_flfi2v")]
    if _fl_candidates:
        VIDEO_WORKFLOWS["wan22_flfi2v"] = VIDEO_WORKFLOWS[_fl_candidates[0]]
    elif "default" in VIDEO_WORKFLOWS:
        VIDEO_WORKFLOWS["wan22_flfi2v"] = VIDEO_WORKFLOWS["default"]

# Ensure a "default" workflow exists for backward compatibility
if "default" not in VIDEO_WORKFLOWS:
    if "wan22_workflow" in VIDEO_WORKFLOWS:
        VIDEO_WORKFLOWS["default"] = VIDEO_WORKFLOWS["wan22_workflow"]
    elif VIDEO_WORKFLOWS:
        _first_key = list(VIDEO_WORKFLOWS.keys())[0]
        VIDEO_WORKFLOWS["default"] = VIDEO_WORKFLOWS[_first_key]

# Helper constant for ThenVsNow agents
THEN_VS_NOW_AGENTS = ["then_vs_now"]

# Legacy single workflow settings (deprecated, use VIDEO_WORKFLOWS instead)
# Kept for backward compatibility
WORKFLOW_PATH = resolve_path("workflow/video/wan22_workflow.json")
LOAD_IMAGE_NODE_ID = "97"
MOTION_PROMPT_NODE_ID = "93"
WAN_VIDEO_NODE_ID = "98"

# ==========================================
# IMAGE GENERATION CONFIGURATION
# ==========================================
# Image generation mode: "gemini", "comfyui", or "geminiweb"
IMAGE_GENERATION_MODE = "comfyui"  # Options: "gemini", "comfyui", "geminiweb"

# Default negative prompt for ComfyUI image generation
# Common negative prompts: "blurry, low quality, distorted, deformed"
DEFAULT_NEGATIVE_PROMPT = "Vibrant colors, overexposed, static, blurry details, subtitles, style, artwork, painting, image, still, overall grayish, worst quality, low quality, JPEG compression residue, ugly, incomplete, extra fingers, poorly drawn hands, poorly drawn faces, deformed, disfigured, distorted limbs, fingers fused together, static image, cluttered background, three legs, many people in the background, walking backwards, blurry, too dark, too bright, too saturated, too sharp, too soft, too high contrast, too bland, too monotonous, too complex, too simple, too abstract, text, logo, watermark, signature"

# Number of images to generate per shot (with different seeds)
# Set to 1 for single image per shot, or higher for multiple variations
# Each image will be named: shot_001_001.png, shot_001_002.png, etc.
IMAGES_PER_SHOT = 1

# Output directory for generated images
IMAGES_OUTPUT_DIR = resolve_path(os.path.join(OUTPUT_DIR, "generated_images"))

# Image aspect ratio (options: "1:1", "16:9", "9:16", "4:3", "3:4")
IMAGE_ASPECT_RATIO = "16:9"

# Image resolution (options: "512", "1024", "1280" "2048")
IMAGE_RESOLUTION = "2048"

# ==========================================
# IMAGE WORKFLOW CONFIGURATION
# ==========================================
# Active image workflow to use (must exist in IMAGE_WORKFLOWS)
IMAGE_WORKFLOW = "flux"

# Image workflow definitions
# Each workflow is auto-detected from the workflow/image directory
IMAGE_WORKFLOWS = {}

# ==========================================
# DYNAMIC IMAGE WORKFLOW DISCOVERY
# ==========================================
# Auto-discover any new image workflows in the workflow/image directory
_image_workflow_dir = resolve_path("workflow/image")
if os.path.exists(_image_workflow_dir):
    for _wf_file in os.listdir(_image_workflow_dir):
        if _wf_file.endswith(".json"):
            _wf_key = os.path.splitext(_wf_file)[0]
            if _wf_key not in IMAGE_WORKFLOWS:
                _wf_path = os.path.join(_image_workflow_dir, _wf_file)
                try:
                    with open(_wf_path, "r", encoding="utf-8") as _f:
                        _wf_raw = json.load(_f)
                    
                    # Normalize workflow format (API JSON vs Workflow JSON)
                    _wf_nodes = {}
                    if "nodes" in _wf_raw and isinstance(_wf_raw["nodes"], list):
                        # Workflow JSON format
                        for _n in _wf_raw["nodes"]:
                            _n_id = str(_n.get("id", ""))
                            if _n_id:
                                _wf_nodes[_n_id] = {
                                    "class_type": _n.get("type", ""),
                                    "_meta": {"title": _n.get("title", "")}
                                }
                    elif isinstance(_wf_raw, dict):
                        # API JSON format
                        _wf_nodes = _wf_raw
                    
                    _text_node_id = None
                    _neg_text_node_id = None
                    _ksampler_node_id = None
                    _vae_node_id = None
                    _save_node_id = None
                    _load_reference_node_id = None
                    _ipadapter_node_id = None
                    
                    _text_candidates = []
                    _sampler_candidates = []
                    _vae_candidates = []
                    _save_candidates = []
                    _load_image_candidates = []
                    _ipadapter_candidates = []
                    
                    # 1. First pass: strict tag matching and gathering candidates
                    for _n_id, _n_data in _wf_nodes.items():
                        if not isinstance(_n_data, dict): continue
                        _title = _n_data.get("_meta", {}).get("title", "")
                        if not _title: _title = ""
                        _title = _title.lower()
                        _class_type = _n_data.get("class_type", "")
                        
                        # Explicit title tag discovery
                        if "[positive]" in _title or "[prompt]" in _title:
                            _text_node_id = _n_id
                        elif "[negative]" in _title or "[neg]" in _title:
                            _neg_text_node_id = _n_id
                        elif "[ksampler]" in _title or "[sampler]" in _title:
                            _ksampler_node_id = _n_id
                        elif "[vae]" in _title:
                            _vae_node_id = _n_id
                        elif "[save]" in _title:
                            _save_node_id = _n_id
                        elif "[reference]" in _title or "[load_ref]" in _title:
                            _load_reference_node_id = _n_id
                        elif "[ipadapter]" in _title:
                            _ipadapter_node_id = _n_id
                            
                        # Candidate gathering for heuristics
                        if "CLIPTextEncode" == _class_type:
                            _text_candidates.append((_n_id, _title))
                        if any(x in _class_type for x in ["KSampler", "SamplerCustomAdvanced", "KSamplerAdvanced", "KSampler (Advanced)"]):
                            _sampler_candidates.append(_n_id)
                        if "VAEDecode" == _class_type:
                            _vae_candidates.append(_n_id)
                        if "SaveImage" == _class_type:
                            _save_candidates.append(_n_id)
                        if "LoadImage" == _class_type:
                            _load_image_candidates.append(_n_id)
                        if "IPAdapter" in _class_type:
                            _ipadapter_candidates.append(_n_id)
                    
                    # 2. Second pass: Tracing connections from the identified KSampler
                    # This is much more robust than title matching
                    if not _ksampler_node_id and _sampler_candidates:
                        _ksampler_node_id = _sampler_candidates[0]
                    
                    if _ksampler_node_id:
                        _sampler_node = _wf_nodes.get(_ksampler_node_id)
                        _inputs = _sampler_node.get("inputs", {})

                        # Trace Positive Prompt - follow full chain until CLIPTextEncode
                        if not _text_node_id:
                            for _pos_input in ["positive", "conditioning", "guider"]:
                                if _pos_input in _inputs:
                                    _p_val = _inputs[_pos_input]
                                    if isinstance(_p_val, list) and len(_p_val) > 0:
                                        _current_node_id = str(_p_val[0])

                                        # Follow the chain recursively (max 10 hops to prevent infinite loops)
                                        for _hop in range(10):
                                            _current_node = _wf_nodes.get(_current_node_id)
                                            if not _current_node:
                                                break

                                            _class_type = _current_node.get("class_type", "")

                                            # Found CLIPTextEncode - this is the target
                                            if "CLIPTextEncode" in _class_type:
                                                _text_node_id = _current_node_id
                                                break

                                            # For guider nodes, trace through their conditioning input
                                            _current_inputs = _current_node.get("inputs", {})
                                            if "conditioning" in _current_inputs:
                                                _c_val = _current_inputs["conditioning"]
                                                if isinstance(_c_val, list) and len(_c_val) > 0:
                                                    _current_node_id = str(_c_val[0])
                                                    continue

                                            # Not a guider or CLIPTextEncode, stop tracing
                                            break

                                    if _text_node_id:
                                        break

                        # Trace Negative Prompt
                        if not _neg_text_node_id and "negative" in _inputs:
                            _n_val = _inputs["negative"]
                            if isinstance(_n_val, list) and len(_n_val) > 0:
                                _neg_text_node_id = str(_n_val[0])

                    # 3. Third pass: Heuristics for missing IDs
                    # Text Nodes (Positive/Negative)
                    if not _text_node_id:
                        # Improved heuristic: pick "positive" or "prompt", but EXCLUDE those that look like negative prompts
                        _pos_filter = [c[0] for c in _text_candidates if "positive" in c[1] or ("prompt" in c[1] and "negative" not in c[1] and "neg " not in c[1])]
                        if _pos_filter: _text_node_id = _pos_filter[0]
                        elif len(_text_candidates) > 0: _text_node_id = _text_candidates[0][0]
                    
                    if not _neg_text_node_id:
                        _neg_filter = [c[0] for c in _text_candidates if "negative" in c[1] or "neg" in c[1]]
                        if _neg_filter: _neg_text_node_id = _neg_filter[0]
                        elif len(_text_candidates) > 1:
                            # If we have 2+ nodes and haven't picked the positive one already
                            if _text_candidates[1][0] != _text_node_id:
                                _neg_text_node_id = _text_candidates[1][0]
                    
                    # VAE / Save / LoadRef / IPAdapter (Sampler already handled in tracing pass)
                    if not _vae_node_id and _vae_candidates: _vae_node_id = _vae_candidates[0]
                    if not _save_node_id and _save_candidates: _save_node_id = _save_candidates[0]
                    if not _load_reference_node_id and _load_image_candidates: _load_reference_node_id = _load_image_candidates[0]
                    if not _ipadapter_node_id and _ipadapter_candidates: _ipadapter_node_id = _ipadapter_candidates[0]

                    # Always add the workflow if it was parseable
                    IMAGE_WORKFLOWS[_wf_key] = {
                        "workflow_path": _wf_path,
                        "text_node_id": _text_node_id,
                        "neg_text_node_id": _neg_text_node_id,
                        "ksampler_node_id": _ksampler_node_id,
                        "vae_node_id": _vae_node_id,
                        "save_node_id": _save_node_id,
                        "load_reference_node_id": _load_reference_node_id,
                        "ipadapter_node_id": _ipadapter_node_id,
                        "description": f"Auto-detected image workflow: {_wf_key}"
                    }
                        
                except Exception as e:
                    # Silently skip unparseable files
                    pass

# Ensure a "default" image workflow exists
if "default" not in IMAGE_WORKFLOWS:
    if "flux" in IMAGE_WORKFLOWS:
        IMAGE_WORKFLOWS["default"] = IMAGE_WORKFLOWS["flux"]
    elif "image_generation_workflow" in IMAGE_WORKFLOWS:
        IMAGE_WORKFLOWS["default"] = IMAGE_WORKFLOWS["image_generation_workflow"]
    elif IMAGE_WORKFLOWS:
        _first_key = list(IMAGE_WORKFLOWS.keys())[0]
        IMAGE_WORKFLOWS["default"] = IMAGE_WORKFLOWS[_first_key]

# Legacy single workflow settings (deprecated, use IMAGE_WORKFLOWS instead)
# Kept for backward compatibility
IMAGE_WORKFLOW_PATH = resolve_path("workflow/image/image_generation_workflow.json")
IMAGE_TEXT_NODE_ID = "6"
IMAGE_NEG_TEXT_NODE_ID = None
IMAGE_KSAMPLER_NODE_ID = "13"
IMAGE_VAE_NODE_ID = "8"
IMAGE_SAVE_NODE_ID = "9"

# ==========================================
# VIDEO GENERATION CONFIGURATION
# ==========================================
# Video generation mode: "comfyui" or "geminiweb"
VIDEO_GENERATION_MODE = os.getenv("VIDEO_GENERATION_MODE", "comfyui")

# Default video length per shot (in seconds)
DEFAULT_SHOT_LENGTH = 5

# Maximum number of shots to generate (for testing)
# Set to 0 for no limit (generates all shots from story)
# Recommended for testing: 3-5 shots
DEFAULT_MAX_SHOTS = 0  # 0 = no limit

# ==========================================
# SHOT PLANNING CONFIGURATION
# ==========================================
# Default number of shots to generate per scene (when no max_shots specified)
DEFAULT_SHOTS_PER_SCENE = 0  # 0 = auto (LLM determines based on context or duration)

# Minimum shots per scene (enforced in planning logic)
MIN_SHOTS_PER_SCENE = 0  # 0 = no hard minimum

# Maximum shots per scene (prevents over-generation for long stories)
MAX_SHOTS_PER_SCENE = 0  # 0 = no hard maximum

# ==========================================
# SCENE DURATION CONFIGURATION
# ==========================================
# Minimum scene duration in seconds (for intelligent scene-based shot distribution)
MIN_SCENE_LENGTH = 15  # Each scene should be at least 15 seconds

# Tolerance for scene duration validation (as percentage, e.g., 0.15 = 15%)
# If sum of scene durations deviates more than this from target, auto-correction is applied
SCENE_DURATION_TOLERANCE = 0.15  # 15% tolerance for duration validation

# Video framerate (fps)
VIDEO_FPS = 16

# Video aspect ratio (options: "1:1", "16:9", "9:16", "4:3", "3:4")
# Default uses same as images for compatibility
VIDEO_ASPECT_RATIO = "16:9"

# Video resolution (options: "512", "720", "1024", "1080", "1280" "2048")
# For landscape: width = resolution, height calculated from aspect ratio
# For portrait: height = resolution, width calculated from aspect ratio
VIDEO_RESOLUTION = os.getenv("VIDEO_RESOLUTION", "1280")  # 720p HD (1280x720 for 16:9)

# Append image prompt to motion prompt for video generation
# When enabled, the image_prompt will be concatenated with motion_prompt
# This can help video AI models better understand the scene context and generate more accurate videos
#
# Benefits:
# - Provides visual context to the video generation model
# - Helps maintain consistency between the reference image and generated video
# - Can improve motion prediction based on scene description
#
# Trade-offs:
# - Longer prompts may slow down video generation slightly
# - Some video models work better with shorter prompts
#
# Recommendations:
# - Enable for Wan 2.2 and similar models that benefit from detailed context
# - Set to "end" for most use cases (motion + image description)
# - Set to "start" if you want visual context emphasized first
APPEND_IMAGE_TO_MOTION_PROMPT = False  # Set to True to enable image prompt appending

# Position to append image prompt: "start" or "end"
# "start" = image_prompt + motion_prompt (image description first, then motion)
# "end" = motion_prompt + image_prompt (motion first, then image description)
IMAGE_PROMPT_APPEND_POSITION = "end"  # Options: "start", "end"

# Target total video length (in seconds)
# Set to None to generate based on story length
# Note: If both DEFAULT_MAX_SHOTS and TARGET_VIDEO_LENGTH are set,
#       max_shots will be calculated as: int(TARGET_VIDEO_LENGTH / DEFAULT_SHOT_LENGTH)
TARGET_VIDEO_LENGTH = 600  # or specify like: 60.0 for 60 seconds

# Video rendering timeout (in seconds)
# Maximum time to wait for a single video render to complete
VIDEO_RENDER_TIMEOUT = 900  # 15 minutes

# LoRA node IDs in the workflow (for camera-based LoRA loading)
# Array of LoRA node pairs - each pair contains HIGH_NOISE_LORA_NODE_ID and LOW_NOISE_LORA_NODE_ID
# This allows up to 4 different camera types to load their LoRAs simultaneously
LORA_NODES = [
    {"HIGH_NOISE_LORA_NODE_ID": "128", "LOW_NOISE_LORA_NODE_ID": "127"},
    {"HIGH_NOISE_LORA_NODE_ID": "130", "LOW_NOISE_LORA_NODE_ID": "131"},
    {"HIGH_NOISE_LORA_NODE_ID": "132", "LOW_NOISE_LORA_NODE_ID": "133"},
    {"HIGH_NOISE_LORA_NODE_ID": "134", "LOW_NOISE_LORA_NODE_ID": "135"},
]

# Legacy single node IDs (for backward compatibility)
LORA_NODE_ID = "127"
LORA_NODE_ID_2 = "128"

# ==========================================
# CAMERA-TO-LORA MAPPING
# ==========================================
# Map camera types to specific LoRA files and trigger keywords for different motion effects
# Camera types from shots.json will be matched to these LoRAs
# Trigger keywords are appended to motion prompts to activate specific LoRA effects
#
# Each shot can have multiple cameras (e.g., "dolly,pan" or ["pan", "drone"])
# When multiple cameras are present, they are assigned to LORA_NODES pairs sequentially:
# - First camera -> LORA_NODES[0]
# - Second camera -> LORA_NODES[1]
# - Third camera -> LORA_NODES[2]
# - Fourth camera -> LORA_NODES[3]
#
# Each camera type has:
# - high_noise_lora: High noise model for more dynamic motion
# - low_noise_lora: Low noise model for more stable/subtle motion
# - trigger_keyword: Text appended to motion prompt to activate LoRA effects
# - strength_low: LoRA strength for low noise model (0.0 to 1.0), required
# - strength_high: LoRA strength for high noise model (0.0 to 1.0), required
CAMERA_LORA_MAPPING = {
    "slow pan": {
        "high_noise_lora": "",
        "low_noise_lora": "",
        "trigger_keyword": "slow pan",
        "strength_low": 0.0,
        "strength_high": 0.0
    },
    "pan": {
        "high_noise_lora": "",
        "low_noise_lora": "",
        "trigger_keyword": "pan",
        "strength_low": 0.0,
        "strength_high": 0.0
    },
    "static": {
        "high_noise_lora": "",
        "low_noise_lora": "",
        "trigger_keyword": "static shot",
        "strength_low": 0.0,
        "strength_high": 0.0
    },
    "dolly": {
        "high_noise_lora": "dolly-zoom-wan22-high.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "dolly-zoom shot",
        "strength_low": 0.0,
        "strength_high": 1.0
    },
    "orbit": {
        "high_noise_lora": "Surround_Camera_S1440.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "ymq",
        "strength_low": 0.0,
        "strength_high": 1.0
    },
    "zoom": {
        "high_noise_lora": "POV_Parkour_high_noise.safetensors",
        "low_noise_lora": "POV_Parkour_low_noise.safetensors",
        "trigger_keyword": "POV Parkour",
        "strength_low": 1.0,
        "strength_high": 1.0
    },
    "tracking": {
        "high_noise_lora": "",
        "low_noise_lora": "",
        "trigger_keyword": "tracking shot",
        "strength_low": 0.0,
        "strength_high": 0.8
    },
    "drone": {
        "high_noise_lora": "wan22-video8-drone-16-sel-2.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "drone shot",
        "strength_low": 0.0,
        "strength_high": 0.9
    },
    "arc": {
        "high_noise_lora": "wan22-video10-arcshot-16-sel-7-high.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "arc shot",
        "strength_low": 0.0,
        "strength_high": 0.8
    },
    "walk": {
        "high_noise_lora": "Walk01_HighWan2_2.safetensors",
        "low_noise_lora": "Walk01_LowWan2_2.safetensors",
        "trigger_keyword": "walking into the direction of the moving camera",
        "strength_low": 0.0,
        "strength_high": 0.9
    },
    "fpv": {
        "high_noise_lora": "wan2.2extremebodycam_000000300_high_noise.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "the viewer runs trought , the hand shows throught camera",
        "strength_low": 0.0,
        "strength_high": 0.9
    },
    "dronedive": {
        "high_noise_lora": "FPV_drone_dive_high_noise.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "Dr0ne Div3",
        "strength_low": 0.0,
        "strength_high": 1.0
    },
    "bullettime": {
        "high_noise_lora": "wan2.2bullet_time_high_noise.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "BULLETTIME",
        "strength_low": 0.0,
        "strength_high": 0.9
    },
    "selfie": {
        "high_noise_lora": "wan2.2extremebodycam_000000300_high_noise.safetensors",
        "low_noise_lora": "",
        "trigger_keyword": "handheld POV movement",
        "strength_low": 0.0,
        "strength_high": 0.8
    },
    "default": {
        "high_noise_lora": "",
        "low_noise_lora": "",
        "trigger_keyword": "",
        "strength_low": 0.0,
        "strength_high": 0.8
    }
}

# ==========================================
# WORKFLOW EXECUTION MODE
# ==========================================
# Step progression mode: "auto" or "manual"
# - auto: Automatically proceed to next step after completion
# - manual: Stop after each step, require user to continue or re-execute
AUTO_STEP_MODE = True  # True = auto, False = manual


# ==========================================
# AGENT CONFIGURATION
# ==========================================
# Default agents to use for each step
# Agent files are stored in agents/{type}/{name}.md
# Available agents depend on files in the agents folder

# Story generation agent (default, dramatic, documentary, time_traveler, netflix_documentary, youtube_documentary, prehistoric_dinosaur, prehistoric_pov)
STORY_AGENT = "default"

# Shots agent (default, artistic, time_traveler, prehistoric_dinosaur, prehistoric_pov)
SHOTS_AGENT = "default"


# ==========================================
# WATERMARK REMOVAL CONFIGURATION
# ==========================================
# External watermark removal tools (full paths)
GEMINI_WATERMARK_TOOL_IMAGE = os.getenv("GEMINI_WATERMARK_TOOL_IMAGE", "GeminiWatermarkTool")
GEMINI_WATERMARK_TOOL_VIDEO = os.getenv("GEMINI_WATERMARK_TOOL_VIDEO", "")

# Watermark removal method: "builtin" or "external"
# - builtin: Uses the internal high-precision image restoration (for images only)
# - external: Calls the configured external tool with the file path as the first argument
WATERMARK_REMOVAL_METHOD = os.getenv("WATERMARK_REMOVAL_METHOD", "builtin")

# ==========================================
# NARRATION/TTS CONFIGURATION
# ==========================================
# Whether to generate narration for videos
GENERATE_NARRATION = False  # Set to True to enable narration by default

# TTS method: "comfyui", "local" (edge-tts), or "elevenlabs"
TTS_METHOD = "local"  # Options: "comfyui", "local", "elevenlabs"

# ComfyUI TTS workflows
# Each workflow defines its own node IDs and path
TTS_WORKFLOW = "default"
TTS_WORKFLOWS = {
    "default": {
        "workflow_path": resolve_path("workflow/voice/tts_workflow.json"),
        "text_node_id": "text_input_node",  # Node ID for text input
        "save_node_id": "save_audio_node",   # Node ID for audio output/save
        "description": "Default ComfyUI TTS workflow"
    }
}

# ==========================================
# SOUNDFX CONFIGURATION
# ==========================================
# Active soundfx workflow to use (must exist in SOUNDFX_WORKFLOWS)
SOUNDFX_WORKFLOW = "mmaudio"

# SoundFX workflow definitions
# Each workflow is auto-detected from the workflow/soundfx directory
SOUNDFX_WORKFLOWS = {}

# ==========================================
# DYNAMIC SOUNDFX WORKFLOW DISCOVERY
# ==========================================
# Auto-discover any new soundfx workflows in the workflow/soundfx directory
_soundfx_workflow_dir = resolve_path("workflow/soundfx")
if os.path.exists(_soundfx_workflow_dir):
    for _wf_file in os.listdir(_soundfx_workflow_dir):
        if _wf_file.endswith(".json"):
            _wf_key = os.path.splitext(_wf_file)[0]
            if _wf_key not in SOUNDFX_WORKFLOWS:
                _wf_path = os.path.join(_soundfx_workflow_dir, _wf_file)
                try:
                    with open(_wf_path, "r", encoding="utf-8") as _f:
                        _wf_raw = json.load(_f)
                    
                    # Normalize workflow format (API JSON vs Workflow JSON)
                    _wf_nodes = {}
                    if "nodes" in _wf_raw and isinstance(_wf_raw["nodes"], list):
                        # Workflow JSON format
                        for _n in _wf_raw["nodes"]:
                            _n_id = str(_n.get("id", ""))
                            if _n_id:
                                _wf_nodes[_n_id] = {
                                    "class_type": _n.get("type", ""),
                                    "_meta": {"title": _n.get("title", "")}
                                }
                    elif isinstance(_wf_raw, dict):
                        # API JSON format
                        _wf_nodes = _wf_raw
                    
                    _load_video_node_id = None
                    _sampler_node_id = None
                    _combine_node_id = None
                    
                    # Candidates
                    _load_video_candidates = []
                    _sampler_candidates = []
                    _combine_candidates = []
                    
                    # 1. First pass: strict tag matching and gathering candidates
                    for _n_id, _n_data in _wf_nodes.items():
                        if not isinstance(_n_data, dict): continue
                        _title = _n_data.get("_meta", {}).get("title", "")
                        if not _title: _title = ""
                        _title = _title.lower()
                        _class_type = _n_data.get("class_type", "")
                        
                        # Explicit title tag discovery
                        if any(tag in _title for tag in ["[video_in]", "[in_video]", "[input_video]", "[load_video]"]):
                            _load_video_node_id = _n_id
                        elif any(tag in _title for tag in ["[sampler]", "[prompt]", "[generator]", "[woosh_sampler]"]):
                            _sampler_node_id = _n_id
                        elif any(tag in _title for tag in ["[video_out]", "[out_video]", "[combine]", "[video_combine]", "[save_video]"]):
                            _combine_node_id = _n_id
                            
                        # Candidate gathering for heuristics
                        if _class_type in ["VHS_LoadVideo", "WooshLoadVideo"]:
                            _load_video_candidates.append(_n_id)
                        if _class_type in ["MMAudioSampler", "WooshSample"]:
                            _sampler_candidates.append(_n_id)
                        if _class_type in ["VHS_VideoCombine"]:
                            _combine_candidates.append(_n_id)
                    
                    # 2. Heuristics fallbacks for missing IDs
                    if not _load_video_node_id and _load_video_candidates:
                        # Prefer VHS_LoadVideo if multiple candidates exist during heuristics
                        _vhs_loads = [cid for cid in _load_video_candidates if _wf_nodes.get(cid, {}).get("class_type") == "VHS_LoadVideo"]
                        _load_video_node_id = _vhs_loads[0] if _vhs_loads else _load_video_candidates[0]
                        
                    if not _sampler_node_id and _sampler_candidates:
                        _sampler_node_id = _sampler_candidates[0]
                    if not _combine_node_id and _combine_candidates:
                        _combine_node_id = _combine_candidates[0]

                    # Always add the workflow if it was parseable
                    SOUNDFX_WORKFLOWS[_wf_key] = {
                        "workflow_path": _wf_path,
                        "load_video_node_id": _load_video_node_id,
                        "sampler_node_id": _sampler_node_id,
                        "combine_node_id": _combine_node_id,
                        "description": f"Auto-detected soundfx workflow: {_wf_key}"
                    }
                        
                except Exception as e:
                    # Silently skip unparseable files
                    pass

# Ensure a "default" soundfx workflow exists
if "default" not in SOUNDFX_WORKFLOWS:
    if "mmaudio" in SOUNDFX_WORKFLOWS:
        SOUNDFX_WORKFLOWS["default"] = SOUNDFX_WORKFLOWS["mmaudio"]
    elif SOUNDFX_WORKFLOWS:
        _first_key = list(SOUNDFX_WORKFLOWS.keys())[0]
        SOUNDFX_WORKFLOWS["default"] = SOUNDFX_WORKFLOWS[_first_key]

# Legacy single workflow setting (deprecated)
TTS_WORKFLOW_PATH = resolve_path("workflow/voice/tts_workflow.json")

# ==========================================
# ELEVENLABS API CONFIGURATION
# ==========================================
# Get your API key from: https://elevenlabs.io/app/settings/api-keys
ELEVENLABS_API_KEY = decrypt_env_var("ELEVENLABS_API_KEY", "")

# Default voice for TTS
# For edge-tts: voice names like "en-US-AriaNeural", "en-GB-SoniaNeural"
# For ComfyUI: depends on your workflow (e.g., "female_01", "male_01")
# For ElevenLabs: voice IDs or names (e.g., "Rachel", "Domi", "21m00Tcm4TlvDq8ikWAM")
TTS_VOICE = "en-US-AriaNeural"

# ElevenLabs model selection
# Options: "eleven_multilingual_v2", "eleven_turbo_v2", "eleven_monolingual_v1"
ELEVENLABS_MODEL = "eleven_multilingual_v2"

# ElevenLabs voice settings
ELEVENLABS_STABILITY = 0.5  # 0.0 to 1.0 (higher = more stable)
ELEVENLABS_SIMILARITY = 0.75  # 0.0 to 1.0 (higher = more similar to original voice)


# ==========================================
# LOGGING CONFIGURATION
# ==========================================
LOG_DIR = resolve_path(os.path.join(OUTPUT_DIR, "logs"))
CONSOLE_LOG_LEVEL = "INFO"
FILE_LOG_LEVEL = "DEBUG"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5


# ==========================================
# CUSTOM PROMPTS FILE CONFIGURATION
# ==========================================
# Default camera type for prompts without explicit camera specification
DEFAULT_CAMERA_FOR_PROMPTS = "static"

# Default motion prompt for shots without explicit motion
DEFAULT_MOTION_FOR_PROMPTS = "Subtle camera movement, slow and smooth"

# Auto-detect camera from prompt text (enabled by default)
AUTO_DETECT_CAMERA_FROM_PROMPTS = True


# Pre-calculate current dimensions
IMAGE_WIDTH, IMAGE_HEIGHT = get_image_dimensions()

# Pre-calculate video dimensions
VIDEO_WIDTH, VIDEO_HEIGHT = get_video_dimensions()


# ==========================================
# IMAGE GENERATION RETRY CONFIGURATION
# ==========================================
# Maximum retry attempts for failed image generation (including initial attempt)
IMAGE_GENERATION_MAX_RETRIES = 3

# Delay between retry attempts in seconds
IMAGE_GENERATION_RETRY_DELAY = 5

# Continue to video generation even if some images failed
CONTINUE_ON_PARTIAL_IMAGE_FAILURE = True


# ==========================================
# GEMINIWEB (BROWSER-BASED) IMAGE GENERATION
# ==========================================
# Playwright browser configuration
# Options: "chromium", "firefox", "webkit"
PLAYWRIGHT_BROWSER = os.getenv("PLAYWRIGHT_BROWSER", "chromium").lower()

# Browser channel (only for chromium/webkit)
# Options: "chrome", "msedge", "chrome-beta", etc.
PLAYWRIGHT_CHANNEL = os.getenv("PLAYWRIGHT_CHANNEL", "chrome").lower()

# Browser profile directory for persistent Google login
# We use separate folders for different browsers to avoid compatibility issues
def _get_profile_folder_name():
    if PLAYWRIGHT_BROWSER == "firefox":
        return "firefox_profile"
    if PLAYWRIGHT_BROWSER == "webkit":
        return "webkit_profile"
    
    # Handle chromium-based browsers
    if "msedge" in PLAYWRIGHT_CHANNEL:
        return "edge_profile"
    if "chrome" in PLAYWRIGHT_CHANNEL:
        return "chrome_profile"
    
    return "chromium_profile"

_default_profile_name = _get_profile_folder_name()
GEMINIWEB_CHROME_PROFILE = os.getenv("GEMINIWEB_CHROME_PROFILE", resolve_path(os.path.join(OUTPUT_DIR, _default_profile_name)))
if not os.path.isabs(GEMINIWEB_CHROME_PROFILE):
    GEMINIWEB_CHROME_PROFILE = resolve_path(GEMINIWEB_CHROME_PROFILE)

# Timeout for waiting for image generation (seconds)
GEMINIWEB_TIMEOUT = 300

# Gemini web URL
GEMINIWEB_URL = "https://gemini.google.com/app"

# Default Gemini Mode: "Fast", "Thinking", or "Pro"
GEMINIWEB_DEFAULT_MODE = os.getenv("GEMINIWEB_DEFAULT_MODE", "Fast")
# ==========================================
# Web UI Configuration
# ==========================================
# Enable/disable Web UI server
WEB_UI_ENABLED = os.getenv("WEB_UI_ENABLED", "true").lower() == "true"

# Backend Configuration
# BACKEND_HOST: External hostname/IP for URLs (default: 127.0.0.1)
# BACKEND_BIND_HOST: Address to listen on (default: 0.0.0.0 for network access)
BACKEND_HOST = os.getenv("BACKEND_HOST", os.getenv("WEB_UI_HOST", "127.0.0.1")).strip('"\' ')
BACKEND_PORT = int(os.getenv("BACKEND_PORT", os.getenv("WEB_UI_PORT", "8000")).strip('"\' '))
BACKEND_BIND_HOST = os.getenv("BACKEND_BIND_HOST", "0.0.0.0" if BACKEND_HOST != "127.0.0.1" and BACKEND_HOST != "localhost" else BACKEND_HOST).strip('"\' ')

# Frontend Configuration
# FRONTEND_HOST: External hostname/IP for URLs (default: 127.0.0.1)
# FRONTEND_BIND_HOST: Address to listen on (default: 0.0.0.0 for network access)
FRONTEND_HOST = os.getenv("FRONTEND_HOST", "127.0.0.1").strip('"\' ')
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "3000").strip('"\' '))
FRONTEND_BIND_HOST = os.getenv("FRONTEND_BIND_HOST", "0.0.0.0" if FRONTEND_HOST != "127.0.0.1" and FRONTEND_HOST != "localhost" else FRONTEND_HOST).strip('"\' ')

# Base URLs
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
FRONTEND_URL = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"

# Backward Compatibility
WEB_UI_HOST = BACKEND_HOST
WEB_UI_PORT = BACKEND_PORT

# CORS origins (comma-separated list of allowed origins for API)
# Dynamically include the configured frontend URLs and common loopbacks
_default_cors = [
    f"http://localhost:{FRONTEND_PORT}",
    f"http://127.0.0.1:{FRONTEND_PORT}",
    f"http://[::1]:{FRONTEND_PORT}",  # IPv6 loopback
    f"http://{FRONTEND_HOST}:{FRONTEND_PORT}",
    FRONTEND_URL
]
_env_cors = os.getenv("WEB_UI_CORS_ORIGINS", "").strip('"\' ')
if _env_cors:
    WEB_UI_CORS_ORIGINS = [c.strip() for c in _env_cors.split(",")]
else:
    # Use unique origins sorted
    WEB_UI_CORS_ORIGINS = sorted(list(set(_default_cors)))
