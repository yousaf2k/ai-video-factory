/**
 * Type definitions for AI Video Factory Web UI
 */

export enum ProjectType {
  Documentary = 1,
  ThenVsNow = 2
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
}

export interface SessionStep {
  story: boolean;
  scene_graph: boolean;
  shots: boolean;
  images: boolean;
  videos: boolean;
  narration: boolean;
}

export interface SessionStats {
  total_shots: number;
  images_generated: number;
  videos_rendered: number;
  narration_generated: boolean;
}

export interface Session {
  session_id: string;
  timestamp: string;
  idea: string;
  story_agent?: string;
  shots_agent?: string;
  started_at: string;
  completed: boolean;
  completed_at?: string;
  steps: SessionStep;
  stats: SessionStats;
  thumbnail_url?: string;
  thumbnail_url_9_16?: string;
  aspect_ratio?: string;
  story?: Story;
  shots?: Shot[];
}

export interface SessionListItem {
  session_id: string;
  timestamp: string;
  idea: string;
  started_at: string;
  completed: boolean;
  total_shots: number;
  images_generated: number;
  videos_rendered: number;
  thumbnail_url?: string;
  thumbnail_url_9_16?: string;
  aspect_ratio?: string;
  story?: Story;
}

export interface Story {
  title: string;
  description?: string;
  tags?: string[];
  thumbnail_prompt_16_9?: string;
  thumbnail_prompt_9_16?: string;
  style: string;
  master_script?: string;
  total_duration?: number;
  scenes: Scene[];
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
}
export interface CreateSessionRequest {
  idea: string;
  session_id?: string;
  story_agent?: string;
  shots_agent?: string;
  total_duration?: number;
  prompts_file?: string;
  aspect_ratio?: "16:9" | "9:16";
}

export interface UpdateSessionRequest {
  idea?: string;
  completed?: boolean;
  story_agent?: string;
  shots_agent?: string;
  aspect_ratio?: "16:9" | "9:16";
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
}

export interface UpdateGlobalConfigRequest {
  llm_provider?: string;
  image_generation_mode?: string;
  video_generation_mode?: string;
  video_workflow?: string;
  image_workflow?: string;
  comfy_url?: string;
  target_video_length?: number;
  gemini_api_key?: string;
  openai_api_key?: string;
  elevenlabs_api_key?: string;
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
  BACKGROUND = "background"
}

export enum QueueItemStatus {
  QUEUED = "queued",
  ACTIVE = "active",
  COMPLETED = "completed",
  CANCELLED = "cancelled",
  FAILED = "failed"
}

export interface QueueItem {
  item_id: string;
  session_id: string;
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
  session_title?: string;
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
  images: number;
  videos: number;
  flfi2v: number;
  narrations: number;
  backgrounds: number;
  total_sessions: number;
}

export type ViewMode = 'flat' | 'grouped';
