/**
 * Type definitions for AI Video Factory Web UI
 */

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
}

export interface Scene {
  location: string;
  characters: string;
  action: string;
  emotion: string;
  narration: string;
  scene_duration?: number;
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
}
export interface CreateSessionRequest {
  idea: string;
  session_id?: string;
  story_agent?: string;
  shots_agent?: string;
  total_duration?: number;
  prompts_file?: string;
}

export interface UpdateSessionRequest {
  idea?: string;
  completed?: boolean;
  story_agent?: string;
  shots_agent?: string;
}

export interface GlobalConfig {
  llm_provider: string;
  image_generation_mode: string;
  video_generation_mode: string;
  default_story_agent: string;
  default_shots_agent: string;
  comfy_url: string;
  target_video_length?: number;
  default_max_shots?: number;
}

export interface UpdateGlobalConfigRequest {
  llm_provider?: string;
  image_generation_mode?: string;
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
