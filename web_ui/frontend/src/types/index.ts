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
  image_prompt: string;
  motion_prompt: string;
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
}
export interface CreateProjectRequest {
  idea: string;
  project_id?: string;
  project_type: ProjectType;
  story_agent?: string;
  shots_agent?: string;
  total_duration?: number;
  prompts_file?: string;
  aspect_ratio?: "16:9" | "9:16" | "21:8";
}

export interface UpdateProjectRequest {
  idea?: string;
  completed?: boolean;
  story_agent?: string;
  shots_agent?: string;
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
  image_prompt?: string;
  motion_prompt?: string;
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
