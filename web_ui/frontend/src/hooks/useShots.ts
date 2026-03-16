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
export function useUpdateShot(projectId: string, shotIndex: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: UpdateShotRequest) => api.updateShot(projectId, shotIndex, request),
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

// Hook to regenerate shot image
export function useRegenerateImage(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIndex, force, imageMode, imageWorkflow, seed, promptOverride, imageVariant }: { shotIndex: number; force?: boolean; imageMode?: string; imageWorkflow?: string; seed?: number; promptOverride?: string; imageVariant?: string }) =>
      api.regenerateShotImage(projectId, shotIndex, force, imageMode, imageWorkflow, seed, promptOverride, imageVariant),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook to regenerate shot video
export function useRegenerateVideo(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIndex, force, videoMode, videoWorkflow, videoVariant, appendImagePrompt }: { shotIndex: number; force?: boolean; videoMode?: string; videoWorkflow?: string; videoVariant?: string; appendImagePrompt?: string }) =>
      api.regenerateShotVideo(projectId, shotIndex, force, videoMode, videoWorkflow, videoVariant, appendImagePrompt),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', projectId] });
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook for batch regeneration
export function useBatchRegenerate(projectId: string) {
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
    }) => api.batchRegenerate(projectId, data),
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
    mutationFn: ({ shotIndex, imagePath }: { shotIndex: number; imagePath: string }) =>
      api.selectShotImage(projectId, shotIndex, imagePath),
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
    mutationFn: ({ shotIndex, variant }: { shotIndex: number; variant?: string }) =>
      api.removeWatermark(projectId, shotIndex, variant),
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
    mutationFn: ({ shotIndex, file, variant }: { shotIndex: number; file: File; variant?: string }) =>
      api.uploadShotImage(projectId, shotIndex, file, variant),
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
    mutationFn: ({ shotIndex, file, variant }: { shotIndex: number; file: File; variant?: string }) =>
      api.uploadShotVideo(projectId, shotIndex, file, variant),
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
    mutationFn: ({ shotIndex, imagePath }: { shotIndex: number; imagePath: string }) =>
      api.deleteVariationImage(projectId, shotIndex, imagePath),
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
    mutationFn: ({ shotIndex, videoPath }: { shotIndex: number; videoPath: string }) =>
      api.selectShotVideo(projectId, shotIndex, videoPath),
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
    mutationFn: ({ shotIndex, videoPath }: { shotIndex: number; videoPath: string }) =>
      api.deleteVariationVideo(projectId, shotIndex, videoPath),
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
