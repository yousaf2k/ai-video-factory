/**
 * API client for AI Video Factory
 */
import axios, { AxiosInstance } from 'axios';
import type {
  Project,
  ProjectListItem,
  CreateProjectRequest,
  UpdateProjectRequest,
  Story,
  UpdateStoryRequest,
  Shot,
  UpdateShotRequest,
  AgentsByType,
  GlobalConfig,
  UpdateGlobalConfigRequest,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // Projects
  async listProjects(): Promise<ProjectListItem[]> {
    const response = await this.client.get<ProjectListItem[]>('/api/projects');
    return response.data;
  }

  async createProject(request: CreateProjectRequest): Promise<Project> {
    const response = await this.client.post<Project>('/api/projects', request);
    return response.data;
  }

  async getProject(projectId: string): Promise<Project> {
    const response = await this.client.get<Project>(`/api/projects/${projectId}`);
    return response.data;
  }

  async updateProject(projectId: string, request: UpdateProjectRequest): Promise<Project> {
    const response = await this.client.put<Project>(`/api/projects/${projectId}`, request);
    return response.data;
  }

  async deleteProject(projectId: string): Promise<void> {
    await this.client.delete(`/api/projects/${projectId}`);
  }

  async duplicateProject(projectId: string, newProjectId?: string): Promise<Project> {
    const response = await this.client.post<Project>(
      `/api/projects/${projectId}/duplicate`,
      newProjectId ? { new_project_id: newProjectId } : {}
    );
    return response.data;
  }

  async generateThumbnail(
    projectId: string,
    aspectRatio: string = '16:9',
    force: boolean = false,
    imageMode?: string,
    imageWorkflow?: string,
    seed?: number
  ): Promise<string> {
    const response = await this.client.post<{ status: string, thumbnail_url: string }>(
      `/api/projects/${projectId}/thumbnail`,
      {
        aspect_ratio: aspectRatio,
        force,
        image_mode: imageMode,
        image_workflow: imageWorkflow,
        seed
      }
    );
    return response.data.thumbnail_url;
  }

  // Story
  async getStory(projectId: string): Promise<Story> {
    const project = await this.getProject(projectId);
    if (!project.story) {
      throw new Error('Story not found');
    }
    return project.story;
  }

  async updateStory(projectId: string, request: UpdateStoryRequest): Promise<Story> {
    const response = await this.client.put<Story>(`/api/projects/${projectId}/story`, request);
    return response.data;
  }

  async regenerateStory(projectId: string, agent: string = 'default'): Promise<Story> {
    const response = await this.client.post<Story>(`/api/projects/${projectId}/story/regenerate`, {
      agent,
    });
    return response.data;
  }

  // Shots
  async getShots(projectId: string): Promise<Shot[]> {
    const project = await this.getProject(projectId);
    return project.shots || [];
  }

  async updateShots(projectId: string, shots: Shot[]): Promise<Shot[]> {
    const response = await this.client.put<Shot[]>(`/api/projects/${projectId}/shots`, {
      shots,
    });
    return response.data;
  }

  async updateShot(projectId: string, shotIndex: number, request: UpdateShotRequest): Promise<Shot> {
    const response = await this.client.put<Shot>(
      `/api/projects/${projectId}/shots/${shotIndex}`,
      request
    );
    return response.data;
  }

  async regenerateShotImage(
    projectId: string,
    shotIndex: number,
    force: boolean = false,
    imageMode?: string,
    imageWorkflow?: string,
    seed?: number,
    promptOverride?: string,
    imageVariant?: string
  ): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/shots/${shotIndex}/regenerate-image`, {
      force,
      image_mode: imageMode,
      image_workflow: imageWorkflow,
      seed,
      prompt_override: promptOverride || undefined,
      image_variant: imageVariant || undefined,
    });
  }

  async regenerateShotVideo(
    projectId: string,
    shotIndex: number,
    force: boolean = false,
    videoMode?: string,
    videoWorkflow?: string,
    videoVariant?: string,
    appendImagePrompt?: string
  ): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/shots/${shotIndex}/regenerate-video`, {
      force,
      video_mode: videoMode,
      video_workflow: videoWorkflow,
      video_variant: videoVariant || undefined,
      append_image_prompt: appendImagePrompt
    });
  }



  async cancelGeneration(projectId: string): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/shots/cancel-generation`);
  }

  async cancelShotGeneration(projectId: string, shotIndex: number): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/shots/${shotIndex}/cancel-generation`);
  }

  async removeWatermark(projectId: string, shotIndex: number, variant?: string): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/shots/${shotIndex}/remove-watermark`, {
      variant: variant || null,
    });
  }

  async getQueueStatus(projectId: string): Promise<{ queued_indices: number[] }> {
    const response = await this.client.get<{ queued_indices: number[] }>(`/api/projects/${projectId}/shots/queue-status`);
    return response.data;
  }

  async selectShotImage(
    projectId: string,
    shotIndex: number,
    imagePath: string
  ): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/shots/${shotIndex}/select-image`, {
      image_path: imagePath,
    });
  }

  async deleteVariationImage(
    projectId: string,
    shotIndex: number,
    imagePath: string
  ): Promise<{ remaining: number; active_image_path: string | null }> {
    const response = await this.client.delete<{ status: string; remaining: number; active_image_path: string | null }>(
      `/api/projects/${projectId}/shots/${shotIndex}/images`,
      { params: { image_path: imagePath } }
    );
    return response.data;
  }

  async selectShotVideo(
    projectId: string,
    shotIndex: number,
    videoPath: string
  ): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/shots/${shotIndex}/select-video`, {
      video_path: videoPath,
    });
  }

  async deleteVariationVideo(
    projectId: string,
    shotIndex: number,
    videoPath: string
  ): Promise<{ remaining: number; active_video_path: string | null }> {
    const response = await this.client.delete<{ status: string; remaining: number; active_video_path: string | null }>(
      `/api/projects/${projectId}/shots/${shotIndex}/videos`,
      { params: { video_path: videoPath } }
    );
    return response.data;
  }

  // Narration API
  async generateSceneNarration(
    projectId: string,
    sceneIndex: number,
    request: { tts_method?: string, tts_workflow?: string, voice?: string }
  ): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/story/scenes/${sceneIndex}/generate-narration`, request);
  }

  async cancelSceneNarration(projectId: string, sceneIndex: number): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/story/scenes/${sceneIndex}/cancel-narration`);
  }

  async batchGenerateNarration(
    projectId: string,
    sceneIndices: number[],
    config?: { tts_method?: string, tts_workflow?: string, voice?: string }
  ): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/story/batch-generate-narration`, {
      scene_indices: sceneIndices,
      ...config
    });
  }

  async selectSceneNarration(
    projectId: string,
    sceneIndex: number,
    narrationPath: string
  ): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/story/scenes/${sceneIndex}/select-narration`, {
      narration_path: narrationPath
    });
  }

  async uploadShotImage(
    projectId: string,
    shotIndex: number,
    file: File,
    variant?: string
  ): Promise<{ image_path: string; filename: string }> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await this.client.post<{ status: string; image_path: string; filename: string }>(
      `/api/projects/${projectId}/shots/${shotIndex}/upload-image`,
      formData,
      { 
        params: { variant },
        headers: { 'Content-Type': 'multipart/form-data' } 
      }
    );
    return response.data;
  }

  async uploadShotVideo(
    projectId: string,
    shotIndex: number,
    file: File,
    variant?: string
  ): Promise<{ video_path: string; filename: string }> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await this.client.post<{ status: string; video_path: string; filename: string }>(
      `/api/projects/${projectId}/shots/${shotIndex}/upload-video`,
      formData,
      { 
        params: { variant },
        headers: { 'Content-Type': 'multipart/form-data' } 
      }
    );
    return response.data;
  }

  async batchRegenerate(
    projectId: string,
    data: {
      shot_indices: number[];
      regenerate_images: boolean;
      regenerate_videos: boolean;
      force?: boolean;
      force_images?: boolean;
      force_videos?: boolean;
      image_mode?: string;
      image_workflow?: string;
      video_mode?: string;
      video_workflow?: string;
      queue_setting?: string;
      append_image_prompt?: string;
    }
  ): Promise<any> {
    const response = await this.client.post(`/api/projects/${projectId}/shots/batch-regenerate`, data);
    return response.data;
  }

  async replanShots(
    projectId: string,
    data: {
      max_shots?: number;
      shots_agent: string;
    }
  ): Promise<any> {
    const response = await this.client.post(`/api/projects/${projectId}/shots/replan`, data);
    return response.data;
  }

  // Generation
  async startGeneration(projectId: string): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/generation/start`);
  }

  async stopGeneration(projectId: string): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/generation/stop`);
  }

  async getGenerationStatus(projectId: string): Promise<any> {
    const response = await this.client.get(`/api/projects/${projectId}/generation/status`);
    return response.data;
  }

  // Assets
  getAssetUrl(projectId: string, assetType: 'images' | 'videos', filename: string): string {
    return `${API_BASE_URL}/api/projects/${projectId}/${assetType}/${filename}`;
  }

  // Config
  async getAgents(): Promise<AgentsByType> {
    const response = await this.client.get<AgentsByType>('/api/config/agents');
    return response.data;
  }

  async getConfig(): Promise<GlobalConfig> {
    const response = await this.client.get<GlobalConfig>('/api/config');
    return response.data;
  }

  async updateConfig(request: UpdateGlobalConfigRequest): Promise<any> {
    const response = await this.client.post('/api/config', request);
    return response.data;
  }

  async getAgentContent(agentType: string, agentId: string): Promise<string> {
    const response = await this.client.get<{ content: string }>(`/api/config/agents/${agentType}/${agentId}`);
    return response.data.content;
  }

  async updateAgentContent(agentType: string, agentId: string, content: string): Promise<any> {
    const response = await this.client.post(`/api/config/agents/${agentType}/${agentId}`, { content });
    return response.data;
  }

  // Workflows
  async listWorkflows(): Promise<Record<string, any[]>> {
    const response = await this.client.get<Record<string, any[]>>('/api/config/workflows');
    return response.data;
  }

  async getWorkflowContent(category: string, filename: string): Promise<string> {
    const response = await this.client.get<{ content: string }>(`/api/config/workflows/${category}/${filename}`);
    return response.data.content;
  }

  async updateWorkflowContent(category: string, filename: string, content: string): Promise<any> {
    const response = await this.client.post(`/api/config/workflows/${category}/${filename}`, { content });
    return response.data;
  }

  async launchBrowser(): Promise<{ status: string, message: string }> {
    const response = await this.client.post<{ status: string, message: string }>('/api/config/launch-browser');
    return response.data;
  }

  // Generic HTTP methods for queue operations
  async get<T = any>(url: string, params?: any): Promise<{ data: T }> {
    return await this.client.get<T>(url, { params });
  }

  async post<T = any>(url: string, data?: any): Promise<{ data: T }> {
    return await this.client.post<T>(url, data);
  }

  async put<T = any>(url: string, data?: any): Promise<{ data: T }> {
    return await this.client.put<T>(url, data);
  }

  async delete<T = any>(url: string, params?: any): Promise<{ data: T }> {
    return await this.client.delete<T>(url, { params });
  }
}

// Export singleton instance
export const api = new ApiClient();
