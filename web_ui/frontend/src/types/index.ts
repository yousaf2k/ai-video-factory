/**
 * Type definitions for AI Video Factory Web UI
 */

export enum ProjectType {
  Documentary = 1,
  ThenVsNow = 2,
  Movie = 3,
  AsmrGlassCutting = 4
}

export interface MovieMetadata {
  year?: number;
  cast: string[];
  director?: string;
  genre?: string;
}

export interface YouTubeMetadata {
  title_options: string[];
  seo_keywords: string[];
  chapters: Array<{ timestamp: string; title: string }>;
  description_preview?: string;
}

export interface Character {
  name: string;
  scene_id?: number;
  then_prompt?: string;
  now_prompt?: string;
  meeting_prompt?: string;
  departure_prompt?: string;
  then_reference_image_path?: string;
  now_reference_image_path?: string;
  then_age?: number;
  now_age?: number;
  // Non ThenVsNow fields
  image_prompt?: string;
  character_reference_image_path?: string;
  voice_type?: string;
  personality?: string;
  attire?: string;
}

export interface ProjectStep {
  story: boolean;
  scene_graph: boolean;
  shots: boolean;
  images: boolean;
  videos: boolean;
  narration: boolean;
}

export interface ProjectStats {
  total_shots: number;
  images_generated: number;
  videos_rendered: number;
  narration_generated: boolean;
}

export interface Project {
  project_id: string;
  timestamp: string;
  idea: string;
  story_agent?: string;
  shots_agent?: string;
  prompt_mode?: "video" | "motion";
  started_at: string;
  completed: boolean;
  completed_at?: string;
  steps: ProjectStep;
  stats: ProjectStats;
  thumbnail_url?: string;
  thumbnail_url_9_16?: string;
  thumbnail_url_21_8?: string;
  poster_thumbnail_url?: string;
  poster_thumbnail_url_9_16?: string;
  poster_thumbnail_url_21_8?: string;
  aspect_ratio?: string;
  story?: Story;
  shots?: Shot[];
}

export interface ProjectListItem {
  project_id: string;
  timestamp: string;
  idea: string;
  started_at: string;
  completed: boolean;
  total_shots: number;
  images_generated: number;
  videos_rendered: number;
  thumbnail_url?: string;
  thumbnail_url_9_16?: string;
  thumbnail_url_21_8?: string;
  poster_thumbnail_url?: string;
  poster_thumbnail_url_9_16?: string;
  poster_thumbnail_url_21_8?: string;
  aspect_ratio?: string;
  story?: Story;
}

export interface Story {
  title: string;
  description?: string;
  tags?: string[];
  thumbnail_prompt_16_9?: string;
  thumbnail_prompt_9_16?: string;
  thumbnail_prompt_21_8?: string;
  poster_thumbnail_prompt_16_9?: string;
  poster_thumbnail_prompt_9_16?: string;
  poster_thumbnail_prompt_21_8?: string;
  style: string;
  master_script?: string;
  total_duration?: number;
  scenes?: Scene[];  // Optional for ASMR and ThenVsNow projects
  shots?: Shot[];     // Direct shots for ASMR and ThenVsNow projects
  expanded_objects?: string[];  // For ASMR projects
  user_input?: string;  // For ASMR projects
  aspect_ratio?: string;  // For ASMR projects
  project_type: ProjectType;
  characters?: Character[];
  youtube_metadata?: YouTubeMetadata;
  movie_metadata?: MovieMetadata;
}

export interface Scene {
  scene_id?: number;
  scene_name?: string;
  location: string;
  characters: string;
  action: string;
  emotion: string;
  narration: string;
  scene_duration?: number;
  narration_path?: string;
  narration_paths?: string[];
  set_prompt?: string;
  scene_image_path?: string;
  background_image_path?: string;
  background_generated?: boolean;
  background_is_generated?: boolean;
}

export interface Shot {
  id?: string;
  index: number;
  duration?: number | null;
  image_prompt: string;
  motion_prompt: string;
  video_prompt?: string | null;
  prompt_type?: "motion" | "video" | null;
  camera: string;
  narration: string;
  batch_number: number;
  image_generated: boolean;
  image_path: string | null;
  image_paths: string[];
  video_rendered: boolean;
  video_path: string | null;
  video_paths?: string[];
  scene_id?: number | null;
  character_name?: string;
  scene_name?: string;
  order_in_scene?: number;
  // FLFI2V mode fields
  is_flfi2v?: boolean;
  character_id?: string;
  then_image_prompt?: string;
  then_image_path?: string;
  then_image_generated?: boolean;
  now_image_prompt?: string;
  now_image_path?: string;
  now_image_generated?: boolean;
  meeting_video_prompt?: string;
  meeting_video_path?: string;
  meeting_video_rendered?: boolean;
  departure_video_prompt?: string;
  departure_video_path?: string;
  departure_video_rendered?: boolean;
  // Sound FX fields
  soundfx_path?: string;
  soundfx_generated?: boolean;
  soundfx_prompt?: string;
  // Asset references (asset library feature) — ordered, first = primary.
  // Shapes: "i/{id}" (library), "{library}/i/{id}" (non-default library),
  // "p/{project_id}/{media_dir}/{filename}" (other projects' media).
  reference_asset_ids?: string[] | null;
}
export interface CreateProjectRequest {
  idea: string;
  project_id?: string;
  project_type: ProjectType;
  story_agent?: string;
  shots_agent?: string;
  prompt_mode?: "video" | "motion";
  total_duration?: number;
  prompts_file?: string;
  aspect_ratio?: "16:9" | "9:16" | "21:8";
}

export interface UpdateProjectRequest {
  idea?: string;
  completed?: boolean;
  story_agent?: string;
  shots_agent?: string;
  prompt_mode?: "video" | "motion";
  aspect_ratio?: "16:9" | "9:16" | "21:8";
}

export interface GlobalConfig {
  llm_provider: string;
  image_generation_mode: string;
  video_generation_mode: string;
  video_workflow: string;
  default_story_agent: string;
  default_shots_agent: string;
  comfy_url: string;
  target_video_length?: number;
  default_max_shots?: number;
  image_workflow?: string;
  available_video_workflows?: string[];
  available_image_workflows?: string[];
  available_soundfx_workflows?: string[];
  playwright_browser?: string;
  gemini_watermark_tool_image?: string;
  gemini_watermark_tool_video?: string;
  watermark_removal_method?: string;
  geminiweb_default_mode?: string;
}

export interface UpdateGlobalConfigRequest {
  llm_provider?: string;
  image_generation_mode?: string;
  video_generation_mode?: string;
  video_workflow?: string;
  image_workflow?: string;
  soundfx_workflow?: string;
  comfy_url?: string;
  target_video_length?: number;
  gemini_api_key?: string;
  openai_api_key?: string;
  deepseek_api_key?: string;
  elevenlabs_api_key?: string;
  playwright_browser?: string;
  gemini_watermark_tool_image?: string;
  gemini_watermark_tool_video?: string;
  watermark_removal_method?: string;
  geminiweb_default_mode?: string;
}

export interface UpdateStoryRequest {
  story: Story;
}

export interface UpdateShotRequest {
  duration?: number | null;
  image_prompt?: string;
  motion_prompt?: string;
  video_prompt?: string;
  prompt_type?: "motion" | "video" | null;
  camera?: string;
  narration?: string;
  scene_id?: number | null;
  // FLFI2V fields
  then_image_prompt?: string;
  now_image_prompt?: string;
  meeting_video_prompt?: string;
  departure_video_prompt?: string;
  soundfx_prompt?: string;
}

export interface ProgressEvent {
  type: 'progress' | 'shot_completed' | 'generation_complete' | 'error';
  step?: string;
  current?: number;
  total?: number;
  shot_index?: number;
  image_path?: string;
  video_path?: string;
  message?: string;
  duration_seconds?: number;
}

export interface GenerationStatus {
  is_running: boolean;
  current_step: string;
  progress: number;
  total: number;
  eta?: number;
}

export interface Agent {
  id: string;
  name: string;
  type: string;
}

export interface AgentsByType {
  story: Agent[];
  shots: Agent[];
  narration: Agent[];
}

// Queue types
export enum GenerationType {
  IMAGE = "image",
  VIDEO = "video",
  THEN_IMAGE = "then_image",
  NOW_IMAGE = "now_image",
  MEETING_VIDEO = "meeting_video",
  DEPARTURE_VIDEO = "departure_video",
  NARRATION = "narration",
  BACKGROUND = "background",
  SOUNDFX = "soundfx"
}

export enum QueueItemStatus {
  QUEUED = "queued",
  ACTIVE = "active",
  COMPLETED = "completed",
  CANCELLED = "cancelled",
  PAUSED = "paused",
  FAILED = "failed"
}

export interface QueueItem {
  item_id: string;
  project_id: string;
  shot_index?: number;
  scene_id?: number;
  generation_type: GenerationType;
  status: QueueItemStatus;
  progress: number;
  priority: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  is_flfi2v: boolean;
  character_name?: string;
  project_title?: string;
  scene_name?: string;
  shot_id?: string;
}

export interface QueueStatistics {
  total: number;
  queued: number;
  active: number;
  completed: number;
  cancelled: number;
  failed: number;
  paused: number;
  images: number;
  videos: number;
  flfi2v: number;
  narrations: number;
  backgrounds: number;
  total_projects: number;
}

export type ViewMode = 'flat' | 'grouped';

// ==========================================
// Asset Library
// ==========================================

export type AssetType = 'image' | 'video' | 'audio' | 'music' | 'text';

// One library root folder (multiple folders supported via ASSET_LIBRARY_DIRS)
export interface AssetLibraryInfo {
  slug: string;
  name: string;
  path: string;
  is_default: boolean;
  exists: boolean;
}

// A single asset — the filename "{id}-{Title}.{ext}" is the metadata
export interface AssetEntry {
  ref: string; // "i/9f3ab21c" — stable id + type letter
  library?: string | null;
  id: string;
  title: string;
  type: AssetType;
  letter: string; // i | v | a | m | g
  cat: string; // "i/Characters/City"
  category: string; // "Images/Characters/City" (display form)
  filename: string;
  ext: string;
  url: string;
  thumb_url?: string | null;
  size_bytes: number;
  modified_at?: string | null;
  media?: { width?: number; height?: number; duration_sec?: number } | null;
}

export interface AssetTreeNode {
  name: string;
  letter: string;
  path: string; // "i/Characters/City"
  count: number;
  children: AssetTreeNode[];
}

export interface AssetUploadResult {
  saved: AssetEntry[];
  skipped: { filename: string; reason: string }[];
  rerouted: { filename: string; to: string }[];
}

// Full text of a Guides (text-type) asset
export interface AssetTextContent {
  ref: string;
  id: string;
  title: string;
  filename: string;
  ext: string;
  content: string;
}

// One generation run into the library (image / video / sound)
export interface AssetGenerationStatus {
  id: string;
  kind: 'image' | 'video' | 'audio';
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  message?: string | null;
  prompt: string;
  cat: string;
  title?: string | null;
  library?: string | null;
  workflow?: string | null;
  aspect_ratio?: string | null;
  seed?: number | null;
  duration?: number | null;
  image_ref?: string | null;
  video_ref?: string | null;
  reference_refs: string[];
  ref?: string | null; // asset ref once completed
  url?: string | null;
  thumb_url?: string | null;
  error?: string | null;
  created_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface GenerateAssetRequest {
  kind: 'image' | 'video' | 'audio';
  prompt: string;
  cat?: string;
  title?: string;
  library?: string;
  workflow?: string;
  aspect_ratio?: string;
  seed?: number;
  duration?: number;
  image_ref?: string;
  video_ref?: string;
  reference_refs?: string[];
}

export interface GenerateWorkflowOption {
  key: string;
  description: string;
}

export interface GenerateOptions {
  image_workflows: GenerateWorkflowOption[];
  video_workflows: GenerateWorkflowOption[];
  soundfx_workflows: GenerateWorkflowOption[];
  video_mode: string;
  aspect_ratios: string[];
}

// A reference resolved to a concrete file — from the asset library
// (kind='library') or another project's media (kind='project').
export interface ResolvedAssetRef {
  ref: string;
  kind: 'library' | 'project';
  title: string;
  type: AssetType;
  letter?: string | null;
  url: string;
  thumb_url?: string | null;
  source?: string | null;
  exists: boolean;
  size_bytes?: number;
  modified_at?: string | null;
  added_at?: string | null;
  media?: { width?: number; height?: number; duration_sec?: number } | null;
}
