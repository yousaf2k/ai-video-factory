/**
 * API client for AI Video Factory
 */
import axios, { AxiosInstance } from 'axios';
import type {
  Session,
  SessionListItem,
  CreateSessionRequest,
  UpdateSessionRequest,
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

  // Sessions
  async listSessions(): Promise<SessionListItem[]> {
    const response = await this.client.get<SessionListItem[]>('/api/sessions');
    return response.data;
  }

  async createSession(request: CreateSessionRequest): Promise<Session> {
    const response = await this.client.post<Session>('/api/sessions', request);
    return response.data;
  }

  async getSession(sessionId: string): Promise<Session> {
    const response = await this.client.get<Session>(`/api/sessions/${sessionId}`);
    return response.data;
  }

  async updateSession(sessionId: string, request: UpdateSessionRequest): Promise<Session> {
    const response = await this.client.put<Session>(`/api/sessions/${sessionId}`, request);
    return response.data;
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.client.delete(`/api/sessions/${sessionId}`);
  }

  async duplicateSession(sessionId: string, newSessionId?: string): Promise<Session> {
    const response = await this.client.post<Session>(
      `/api/sessions/${sessionId}/duplicate`,
      newSessionId ? { new_session_id: newSessionId } : {}
    );
    return response.data;
  }

  async generateThumbnail(
    sessionId: string,
    aspectRatio: string = '16:9',
    force: boolean = false,
    imageMode?: string,
    imageWorkflow?: string,
    seed?: number
  ): Promise<string> {
    const response = await this.client.post<{ status: string, thumbnail_url: string }>(
      `/api/sessions/${sessionId}/thumbnail`,
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
  async getStory(sessionId: string): Promise<Story> {
    const session = await this.getSession(sessionId);
    if (!session.story) {
      throw new Error('Story not found');
    }
    return session.story;
  }

  async updateStory(sessionId: string, request: UpdateStoryRequest): Promise<Story> {
    const response = await this.client.put<Story>(`/api/sessions/${sessionId}/story`, request);
    return response.data;
  }

  async regenerateStory(sessionId: string, agent: string = 'default'): Promise<Story> {
    const response = await this.client.post<Story>(`/api/sessions/${sessionId}/story/regenerate`, {
      agent,
    });
    return response.data;
  }

  // Shots
  async getShots(sessionId: string): Promise<Shot[]> {
    const session = await this.getSession(sessionId);
    return session.shots || [];
  }

  async updateShots(sessionId: string, shots: Shot[]): Promise<Shot[]> {
    const response = await this.client.put<Shot[]>(`/api/sessions/${sessionId}/shots`, {
      shots,
    });
    return response.data;
  }

  async updateShot(sessionId: string, shotIndex: number, request: UpdateShotRequest): Promise<Shot> {
    const response = await this.client.put<Shot>(
      `/api/sessions/${sessionId}/shots/${shotIndex}`,
      request
    );
    return response.data;
  }

  async regenerateShotImage(
    sessionId: string,
    shotIndex: number,
    force: boolean = false,
    imageMode?: string,
    imageWorkflow?: string,
    seed?: number,
    promptOverride?: string
  ): Promise<void> {
    await this.client.post(`/api/sessions/${sessionId}/shots/${shotIndex}/regenerate-image`, {
      force,
      image_mode: imageMode,
      image_workflow: imageWorkflow,
      seed,
      prompt_override: promptOverride || undefined,
    });
  }

  async regenerateShotVideo(
    sessionId: string,
    shotIndex: number,
    force: boolean = false,
    videoWorkflow?: string
  ): Promise<void> {
    await this.client.post(`/api/sessions/${sessionId}/shots/${shotIndex}/regenerate-video`, {
      force,
      video_workflow: videoWorkflow,
    });
  }



  async cancelGeneration(sessionId: string): Promise<void> {
    await this.client.post(`/api/sessions/${sessionId}/shots/cancel-generation`);
  }

  async cancelShotGeneration(sessionId: string, shotIndex: number): Promise<void> {
    await this.client.post(`/api/sessions/${sessionId}/shots/${shotIndex}/cancel-generation`);
  }

  async removeWatermark(sessionId: string, shotIndex: number): Promise<void> {
    await this.client.post(`/api/sessions/${sessionId}/shots/${shotIndex}/remove-watermark`);
  }

  async getQueueStatus(sessionId: string): Promise<{ queued_indices: number[] }> {
    const response = await this.client.get<{ queued_indices: number[] }>(`/api/sessions/${sessionId}/shots/queue-status`);
    return response.data;
  }

  async selectShotImage(
    sessionId: string,
    shotIndex: number,
    imagePath: string
  ): Promise<void> {
    await this.client.post(`/api/sessions/${sessionId}/shots/${shotIndex}/select-image`, {
      image_path: imagePath,
    });
  }

  async deleteVariationImage(
    sessionId: string,
    shotIndex: number,
    imagePath: string
  ): Promise<{ remaining: number; active_image_path: string | null }> {
    const response = await this.client.delete<{ status: string; remaining: number; active_image_path: string | null }>(
      `/api/sessions/${sessionId}/shots/${shotIndex}/images`,
      { params: { image_path: imagePath } }
    );
    return response.data;
  }

  async uploadShotImage(
    sessionId: string,
    shotIndex: number,
    file: File
  ): Promise<{ image_path: string; filename: string }> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await this.client.post<{ status: string; image_path: string; filename: string }>(
      `/api/sessions/${sessionId}/shots/${shotIndex}/upload-image`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  }

  async batchRegenerate(
    sessionId: string,
    data: {
      shot_indices: number[];
      regenerate_images: boolean;
      regenerate_videos: boolean;
      force?: boolean;
      image_mode?: string;
      image_workflow?: string;
      video_workflow?: string;
    }
  ): Promise<any> {
    const response = await this.client.post(`/api/sessions/${sessionId}/shots/batch-regenerate`, data);
    return response.data;
  }

  async replanShots(
    sessionId: string,
    data: {
      max_shots?: number;
      shots_agent: string;
    }
  ): Promise<any> {
    const response = await this.client.post(`/api/sessions/${sessionId}/shots/replan`, data);
    return response.data;
  }

  // Generation
  async startGeneration(sessionId: string): Promise<void> {
    await this.client.post(`/api/sessions/${sessionId}/generation/start`);
  }

  async stopGeneration(sessionId: string): Promise<void> {
    await this.client.post(`/api/sessions/${sessionId}/generation/stop`);
  }

  async getGenerationStatus(sessionId: string): Promise<any> {
    const response = await this.client.get(`/api/sessions/${sessionId}/generation/status`);
    return response.data;
  }

  // Assets
  getAssetUrl(sessionId: string, assetType: 'images' | 'videos', filename: string): string {
    return `${API_BASE_URL}/api/sessions/${sessionId}/${assetType}/${filename}`;
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
}

// Export singleton instance
export const api = new ApiClient();
