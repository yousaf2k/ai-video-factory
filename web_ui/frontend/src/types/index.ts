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
  started_at: string;
  completed: boolean;
  completed_at?: string;
  steps: SessionStep;
  stats: SessionStats;
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
}

export interface Story {
  title: string;
  style: string;
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
  agent?: string;
  session_id?: string;
}

export interface UpdateSessionRequest {
  idea?: string;
  completed?: boolean;
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
