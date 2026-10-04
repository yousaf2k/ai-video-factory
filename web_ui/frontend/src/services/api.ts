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
  AssetLibraryInfo,
  AssetTreeNode,
  AssetEntry,
  AssetUploadResult,
  ResolvedAssetRef,
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
    seed?: number,
    isPoster?: boolean
  ): Promise<string> {
    const response = await this.client.post<{ status: string, thumbnail_url: string }>(
      `/api/projects/${projectId}/thumbnail`,
      {
        aspect_ratio: aspectRatio,
        force,
        image_mode: imageMode,
        image_workflow: imageWorkflow,
        seed,
        is_poster: isPoster || false
      }
    );
    return response.data.thumbnail_url;
  }

  async uploadThumbnail(
    projectId: string,
    file: File,
    aspectRatio: string = '16:9',
    isPoster: boolean = false
  ): Promise<string> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('aspect_ratio', aspectRatio);
    formData.append('is_poster', isPoster ? 'true' : 'false');
    
    const response = await this.client.post<{ status: string, thumbnail_url: string }>(
      `/api/projects/${projectId}/thumbnail/upload`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' }
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

  async generateStory(projectId: string, agent: string = 'default'): Promise<Story> {
    const response = await this.client.post<Story>(`/api/projects/${projectId}/story/generate`, {
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

  async updateShot(projectId: string, shotIdOrIndex: string | number, request: UpdateShotRequest): Promise<Shot> {
    const response = await this.client.put<Shot>(
      `/api/projects/${projectId}/shots/${shotIdOrIndex}`,
      request
    );
    return response.data;
  }

  async generateCharacterReferenceImage(
    projectId: string,
    characterIndex: number,
    request: {
      variant: string;
      prompt_override?: string;
      image_mode?: string;
      image_workflow?: string;
      seed?: number;
      gemini_mode?: string;
    }
  ): Promise<any> {
    const response = await this.client.post(
      `/api/projects/${projectId}/story/characters/${characterIndex}/generate-reference`,
      request
    );
    return response.data;
  }

  async generateShotImage(
    projectId: string,
    shotIdOrIndex: string | number,
    force: boolean = false,
    imageMode?: string,
    imageWorkflow?: string,
    seed?: number,
    promptOverride?: string,
    imageVariant?: string,
    geminiMode?: string
  ): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/shots/${shotIdOrIndex}/generate-image`, {
      force,
      image_mode: imageMode,
      image_workflow: imageWorkflow,
      seed,
      prompt_override: promptOverride || undefined,
      image_variant: imageVariant || undefined,
      gemini_mode: geminiMode || undefined,
    });
  }

  async generateShotVideo(
    projectId: string,
    shotIdOrIndex: string | number,
    force: boolean = false,
    videoMode?: string,
    videoWorkflow?: string,
    videoVariant?: string,
    appendImagePrompt?: string,
    generateSoundFX?: boolean,
    draftLowResVideo?: boolean,
    promptOverride?: string,
    resolution?: string,
    geminiMode?: string,
    soundfxWorkflow?: string,
    soundfxPrompt?: string
  ): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/shots/${shotIdOrIndex}/generate-video`, {
      force,
      video_mode: videoMode,
      video_workflow: videoWorkflow,
      video_variant: videoVariant || undefined,
      append_image_prompt: appendImagePrompt,
      generate_soundfx: generateSoundFX || false,
      draft_low_res_video: draftLowResVideo || false,
      prompt_override: promptOverride || undefined,
      resolution: resolution || undefined,
      gemini_mode: geminiMode || undefined,
      soundfx_workflow: soundfxWorkflow || undefined,
      soundfx_prompt: soundfxPrompt || undefined,
    });
  }

  async generateSoundFX(
    projectId: string,
    shotIdOrIndex: string | number,
    force: boolean = false,
    workflow?: string,
    promptOverride?: string
  ): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/shots/${shotIdOrIndex}/generate-soundfx`, {
      force,
      workflow,
      prompt_override: promptOverride
    });
  }



  async cancelGeneration(projectId: string): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/shots/cancel-generation`);
  }

  async cancelShotGeneration(projectId: string, shotIdOrIndex: string | number): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/shots/${shotIdOrIndex}/cancel-generation`);
  }

  async removeWatermark(projectId: string, shotIdOrIndex: string | number, variant?: string, type: string = "image"): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/shots/${shotIdOrIndex}/remove-watermark`, {
      variant: variant || null,
      type: type
    });
  }

  async getQueueStatus(projectId: string): Promise<any> {
    const response = await this.client.get<any>(`/api/projects/${projectId}/shots/queue-status`);
    return response.data;
  }

  async selectShotImage(
    projectId: string,
    shotIdOrIndex: string | number,
    imagePath: string,
    variant?: string
  ): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/shots/${shotIdOrIndex}/select-image`, {
      image_path: imagePath,
      variant: variant || undefined,
    });
  }

  async deleteVariationImage(
    projectId: string,
    shotIdOrIndex: string | number,
    imagePath: string
  ): Promise<{ remaining: number; active_image_path: string | null }> {
    const response = await this.client.delete<{ status: string; remaining: number; active_image_path: string | null }>(
      `/api/projects/${projectId}/shots/${shotIdOrIndex}/images`,
      { params: { image_path: imagePath } }
    );
    return response.data;
  }

  async selectShotVideo(
    projectId: string,
    shotIdOrIndex: string | number,
    videoPath: string,
    variant?: string
  ): Promise<void> {
    await this.client.post(`/api/projects/${projectId}/shots/${shotIdOrIndex}/select-video`, {
      video_path: videoPath,
      variant: variant || undefined,
    });
  }

  async deleteVariationVideo(
    projectId: string,
    shotIdOrIndex: string | number,
    videoPath: string
  ): Promise<{ remaining: number; active_video_path: string | null }> {
    const response = await this.client.delete<{ status: string; remaining: number; active_video_path: string | null }>(
      `/api/projects/${projectId}/shots/${shotIdOrIndex}/videos`,
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

  async deleteSceneNarration(projectId: string, sceneIndex: number): Promise<{ deleted: string[] }> {
    const response = await this.client.delete(`/api/projects/${projectId}/story/scenes/${sceneIndex}/narration`);
    return response.data;
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
    shotIdOrIndex: string | number,
    file: File,
    variant?: string
  ): Promise<{ image_path: string; filename: string }> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await this.client.post<{ status: string; image_path: string; filename: string }>(
      `/api/projects/${projectId}/shots/${shotIdOrIndex}/upload-image`,
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
    shotIdOrIndex: string | number,
    file: File,
    variant?: string
  ): Promise<{ video_path: string; filename: string }> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await this.client.post<{ status: string; video_path: string; filename: string }>(
      `/api/projects/${projectId}/shots/${shotIdOrIndex}/upload-video`,
      formData,
      { 
        params: { variant },
        headers: { 'Content-Type': 'multipart/form-data' } 
      }
    );
    return response.data;
  }

  async batchGenerate(
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
      generate_soundfx?: boolean;
      draft_low_res_video?: boolean;
      departure_prompt_override?: string;
      then_prompt_override?: string;
      resolution?: string;
      gemini_mode?: string;
      soundfx_workflow?: string;
      soundfx_prompt?: string;
    }
  ): Promise<any> {
    const response = await this.client.post(`/api/projects/${projectId}/shots/batch-generate`, data);
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

  // Asset library
  async listAssetLibraries(): Promise<AssetLibraryInfo[]> {
    const response = await this.client.get<AssetLibraryInfo[]>('/api/assets/libraries');
    return response.data;
  }

  async updateAssetLibraries(paths: string[]): Promise<AssetLibraryInfo[]> {
    const response = await this.client.post<AssetLibraryInfo[]>('/api/assets/libraries', { paths });
    return response.data;
  }

  async getAssetTree(library?: string): Promise<AssetTreeNode[]> {
    const response = await this.client.get<AssetTreeNode[]>('/api/assets/tree', {
      params: { library },
    });
    return response.data;
  }

  async listAssets(cat: string, library?: string): Promise<AssetEntry[]> {
    const response = await this.client.get<AssetEntry[]>('/api/assets/list', {
      params: { cat, library },
    });
    return response.data;
  }

  async searchAssets(q: string, library?: string, type?: string): Promise<AssetEntry[]> {
    const response = await this.client.get<AssetEntry[]>('/api/assets/search', {
      params: { q, library, type },
    });
    return response.data;
  }

  async getAssetEntry(ref: string, probe: boolean = false): Promise<AssetEntry | ResolvedAssetRef> {
    const response = await this.client.get<AssetEntry | ResolvedAssetRef>('/api/assets/entry', {
      params: { ref, probe },
    });
    return response.data;
  }

  async uploadAssets(cat: string, files: File[], library?: string): Promise<AssetUploadResult> {
    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));
    formData.append('cat', cat);
    if (library) formData.append('library', library);
    const response = await this.client.post<AssetUploadResult>('/api/assets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  async importAsset(ref: string, cat: string, title?: string, library?: string): Promise<AssetUploadResult> {
    const response = await this.client.post<AssetUploadResult>('/api/assets/import', {
      ref, cat, title, library,
    });
    return response.data;
  }

  async renameAsset(ref: string, title: string): Promise<AssetEntry> {
    const response = await this.client.put<AssetEntry>('/api/assets/rename', { ref, title });
    return response.data;
  }

  async moveAsset(ref: string, toCat: string): Promise<AssetEntry> {
    const response = await this.client.put<AssetEntry>('/api/assets/move', { ref, to_cat: toCat });
    return response.data;
  }

  async deleteAsset(ref: string, force: boolean = false): Promise<{ deleted: boolean }> {
    const response = await this.client.delete<{ deleted: boolean }>('/api/assets/delete', {
      params: { ref, force },
    });
    return response.data;
  }

  async createAssetCategory(cat: string, name: string, library?: string): Promise<{ cat: string }> {
    const response = await this.client.post<{ cat: string }>('/api/assets/categories', {
      cat,
      name,
      library,
    });
    return response.data;
  }

  async deleteAssetCategory(cat: string, force: boolean = false, library?: string): Promise<{ deleted: boolean }> {
    const response = await this.client.delete<{ deleted: boolean }>('/api/assets/categories', {
      params: { cat, force, library },
    });
    return response.data;
  }

  async moveAssetCategory(cat: string, toParent: string, library?: string): Promise<{ cat: string; new_cat: string }> {
    const response = await this.client.put<{ cat: string; new_cat: string }>(
      '/api/assets/categories/move',
      { cat, to_parent: toParent, library }
    );
    return response.data;
  }

  async renameAssetCategory(cat: string, name: string, library?: string): Promise<{ cat: string; new_cat: string }> {
    const response = await this.client.put<{ cat: string; new_cat: string }>(
      '/api/assets/categories/rename',
      { cat, name, library }
    );
    return response.data;
  }

  // Project asset pool + shot references
  async getProjectAssets(projectId: string): Promise<ResolvedAssetRef[]> {
    const response = await this.client.get<ResolvedAssetRef[]>(`/api/projects/${projectId}/assets`);
    return response.data;
  }

  async addProjectAssets(projectId: string, refs: string[]): Promise<ResolvedAssetRef[]> {
    const response = await this.client.post<ResolvedAssetRef[]>(`/api/projects/${projectId}/assets`, { refs });
    return response.data;
  }

  async removeProjectAsset(projectId: string, ref: string, strip: boolean = true): Promise<{ removed: string; pool_size: number }> {
    const path = ref.split('/').map(encodeURIComponent).join('/');
    const response = await this.client.delete<{ removed: string; pool_size: number }>(
      `/api/projects/${projectId}/assets/${path}`,
      { params: { strip } }
    );
    return response.data;
  }

  async getShotReferences(projectId: string, shotId: string | number): Promise<ResolvedAssetRef[]> {
    const response = await this.client.get<ResolvedAssetRef[]>(
      `/api/projects/${projectId}/shots/${shotId}/references`
    );
    return response.data;
  }

  async setShotReferences(projectId: string, shotId: string | number, refs: string[]): Promise<ResolvedAssetRef[]> {
    const response = await this.client.put<ResolvedAssetRef[]>(
      `/api/projects/${projectId}/shots/${shotId}/references`,
      { refs }
    );
    return response.data;
  }

  async addShotReferences(projectId: string, shotId: string | number, refs: string[]): Promise<ResolvedAssetRef[]> {
    const response = await this.client.post<ResolvedAssetRef[]>(
      `/api/projects/${projectId}/shots/${shotId}/references`,
      { refs }
    );
    return response.data;
  }

  async removeShotReference(projectId: string, shotId: string | number, ref: string): Promise<ResolvedAssetRef[]> {
    const path = ref.split('/').map(encodeURIComponent).join('/');
    const response = await this.client.delete<ResolvedAssetRef[]>(
      `/api/projects/${projectId}/shots/${shotId}/references/${path}`
    );
    return response.data;
  }

  async useReferenceAsSource(
    projectId: string,
    shotId: string | number,
    ref: string,
    slot: 'then' | 'now'
  ): Promise<{ shot_id: string | number; slot: string; field: string; path: string }> {
    const response = await this.client.post(
      `/api/projects/${projectId}/shots/${shotId}/references/use-as-source`,
      { ref, slot }
    );
    return response.data;
  }

  async getProjectMedia(projectId: string): Promise<ResolvedAssetRef[]> {
    const response = await this.client.get<ResolvedAssetRef[]>(`/api/assets/projects/${projectId}/media`);
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
