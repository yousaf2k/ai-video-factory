/**
 * React hooks for shot management
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import type { Shot, UpdateShotRequest } from '@/types';

// Hook to get shots
export function useShots(projectId: string) {
  return useQuery({
    queryKey: ['shots', projectId],
    queryFn: () => api.getShots(projectId),
    enabled: !!projectId,
  });
}

// Hook to update a shot
export function useUpdateShot(projectId: string, shotIdOrIndex: string | number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: UpdateShotRequest) => api.updateShot(projectId, shotIdOrIndex, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook to bulk update/reorder all shots
export function useUpdateShots(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (shots: Shot[]) => api.updateShots(projectId, shots),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook to generate shot image
export function useGenerateImage(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIdOrIndex, force, imageMode, imageWorkflow, seed, promptOverride, imageVariant, geminiMode }: { shotIdOrIndex: string | number; force?: boolean; imageMode?: string; imageWorkflow?: string; seed?: number; promptOverride?: string; imageVariant?: string; geminiMode?: string }) =>
      api.generateShotImage(projectId, shotIdOrIndex, force, imageMode, imageWorkflow, seed, promptOverride, imageVariant, geminiMode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook to generate shot video
export function useGenerateVideo(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIdOrIndex, force, videoMode, videoWorkflow, videoVariant, appendImagePrompt, generateSoundFX, draftLowResVideo, promptOverride, resolution, geminiMode }: { shotIdOrIndex: string | number; force?: boolean; videoMode?: string; videoWorkflow?: string; videoVariant?: string; appendImagePrompt?: string; generateSoundFX?: boolean; draftLowResVideo?: boolean; promptOverride?: string; resolution?: string; geminiMode?: string }) =>
      api.generateShotVideo(projectId, shotIdOrIndex, force, videoMode, videoWorkflow, videoVariant, appendImagePrompt, generateSoundFX, draftLowResVideo, promptOverride, resolution, geminiMode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook to generate sound FX for a shot
export function useGenerateSoundFX(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIdOrIndex, force }: { shotIdOrIndex: string | number; force?: boolean }) =>
      api.generateSoundFX(projectId, shotIdOrIndex, force),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook for batch generation
export function useBatchGenerate(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      shot_indices: number[];
      regenerate_images: boolean;
      regenerate_videos: boolean;
      force?: boolean;
      image_mode?: string;
      image_workflow?: string;
      video_workflow?: string;
      draft_low_res_video?: boolean;
      append_image_prompt?: string;
      generate_soundfx?: boolean;
      departure_prompt_override?: string;
      then_prompt_override?: string;
      resolution?: string;
      gemini_mode?: string;
    }) => api.batchGenerate(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook to select a specific image as the active one
export function useSelectImage(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIdOrIndex, imagePath, variant }: { shotIdOrIndex: string | number; imagePath: string; variant?: string }) =>
      api.selectShotImage(projectId, shotIdOrIndex, imagePath, variant),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook to replan shots
export function useReplanShots(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { max_shots?: number; shots_agent: string; }) =>
      api.replanShots(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook to remove watermark from a shot
export function useRemoveWatermark(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIdOrIndex, variant, type }: { shotIdOrIndex: string | number; variant?: string; type?: string }) =>
      api.removeWatermark(projectId, shotIdOrIndex, variant, type),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook to upload a custom image from disk for a shot
export function useUploadShotImage(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIdOrIndex, file, variant }: { shotIdOrIndex: string | number; file: File; variant?: string }) =>
      api.uploadShotImage(projectId, shotIdOrIndex, file, variant),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook to upload a custom video from disk for a shot
export function useUploadShotVideo(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIdOrIndex, file, variant }: { shotIdOrIndex: string | number; file: File; variant?: string }) =>
      api.uploadShotVideo(projectId, shotIdOrIndex, file, variant),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook to delete a specific image variation for a shot
export function useDeleteVariationImage(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIdOrIndex, imagePath }: { shotIdOrIndex: string | number; imagePath: string }) =>
      api.deleteVariationImage(projectId, shotIdOrIndex, imagePath),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook to select a specific video variation for a shot
export function useSelectVideo(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIdOrIndex, videoPath, variant }: { shotIdOrIndex: string | number; videoPath: string; variant?: string }) =>
      api.selectShotVideo(projectId, shotIdOrIndex, videoPath, variant),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook to delete a specific video variation for a shot
export function useDeleteVariationVideo(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIdOrIndex, videoPath }: { shotIdOrIndex: string | number; videoPath: string }) =>
      api.deleteVariationVideo(projectId, shotIdOrIndex, videoPath),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Narration Hooks
export function useGenerateSceneNarration(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sceneIndex, config }: { sceneIndex: number; config: { tts_method?: string, tts_workflow?: string, voice?: string } }) =>
      api.generateSceneNarration(projectId, sceneIndex, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

export function useCancelSceneNarration(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sceneIndex: number) => api.cancelSceneNarration(projectId, sceneIndex),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

export function useBatchGenerateNarration(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sceneIndices, config }: { sceneIndices: number[]; config?: { tts_method?: string, tts_workflow?: string, voice?: string } }) =>
      api.batchGenerateNarration(projectId, sceneIndices, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

export function useSelectSceneNarration(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sceneIndex, narrationPath }: { sceneIndex: number; narrationPath: string }) =>
      api.selectSceneNarration(projectId, sceneIndex, narrationPath),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}
