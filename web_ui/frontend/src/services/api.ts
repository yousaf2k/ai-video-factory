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
    force: boolean = false
  ): Promise<void> {
    await this.client.post(`/api/sessions/${sessionId}/shots/${shotIndex}/regenerate-image`, {
      force,
    });
  }

  async regenerateShotVideo(
    sessionId: string,
    shotIndex: number,
    force: boolean = false
  ): Promise<void> {
    await this.client.post(`/api/sessions/${sessionId}/shots/${shotIndex}/regenerate-video`, {
      force,
    });
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
}

// Export singleton instance
export const api = new ApiClient();
