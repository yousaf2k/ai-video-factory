/**
 * React hooks for shot management
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import type { Shot, UpdateShotRequest } from '@/types';

// Hook to get shots
export function useShots(sessionId: string) {
  return useQuery({
    queryKey: ['shots', sessionId],
    queryFn: () => api.getShots(sessionId),
    enabled: !!sessionId,
  });
}

// Hook to update a shot
export function useUpdateShot(sessionId: string, shotIndex: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: UpdateShotRequest) => api.updateShot(sessionId, shotIndex, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

// Hook to bulk update/reorder all shots
export function useUpdateShots(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (shots: Shot[]) => api.updateShots(sessionId, shots),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

// Hook to regenerate shot image
export function useRegenerateImage(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIndex, force, imageMode, imageWorkflow, seed, promptOverride }: { shotIndex: number; force?: boolean; imageMode?: string; imageWorkflow?: string; seed?: number; promptOverride?: string }) =>
      api.regenerateShotImage(sessionId, shotIndex, force, imageMode, imageWorkflow, seed, promptOverride),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

// Hook to regenerate shot video
export function useRegenerateVideo(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIndex, force, videoMode, videoWorkflow }: { shotIndex: number; force?: boolean; videoMode?: string; videoWorkflow?: string }) =>
      api.regenerateShotVideo(sessionId, shotIndex, force, videoMode, videoWorkflow),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

// Hook for batch regeneration
export function useBatchRegenerate(sessionId: string) {
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
    }) => api.batchRegenerate(sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

// Hook to select a specific image as the active one
export function useSelectImage(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIndex, imagePath }: { shotIndex: number; imagePath: string }) =>
      api.selectShotImage(sessionId, shotIndex, imagePath),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

// Hook to replan shots
export function useReplanShots(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { max_shots?: number; shots_agent: string; }) =>
      api.replanShots(sessionId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

// Hook to remove watermark from a shot
export function useRemoveWatermark(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (shotIndex: number) => api.removeWatermark(sessionId, shotIndex),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

// Hook to upload a custom image from disk for a shot
export function useUploadShotImage(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIndex, file }: { shotIndex: number; file: File }) =>
      api.uploadShotImage(sessionId, shotIndex, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

// Hook to upload a custom video from disk for a shot
export function useUploadShotVideo(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIndex, file }: { shotIndex: number; file: File }) =>
      api.uploadShotVideo(sessionId, shotIndex, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

// Hook to delete a specific image variation for a shot
export function useDeleteVariationImage(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIndex, imagePath }: { shotIndex: number; imagePath: string }) =>
      api.deleteVariationImage(sessionId, shotIndex, imagePath),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

// Hook to select a specific video variation for a shot
export function useSelectVideo(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIndex, videoPath }: { shotIndex: number; videoPath: string }) =>
      api.selectShotVideo(sessionId, shotIndex, videoPath),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

// Hook to delete a specific video variation for a shot
export function useDeleteVariationVideo(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIndex, videoPath }: { shotIndex: number; videoPath: string }) =>
      api.deleteVariationVideo(sessionId, shotIndex, videoPath),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

// Narration Hooks
export function useGenerateSceneNarration(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sceneIndex, config }: { sceneIndex: number; config: { tts_method?: string, tts_workflow?: string, voice?: string } }) =>
      api.generateSceneNarration(sessionId, sceneIndex, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

export function useCancelSceneNarration(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sceneIndex: number) => api.cancelSceneNarration(sessionId, sceneIndex),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

export function useBatchGenerateNarration(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sceneIndices, config }: { sceneIndices: number[]; config?: { tts_method?: string, tts_workflow?: string, voice?: string } }) =>
      api.batchGenerateNarration(sessionId, sceneIndices, config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

export function useSelectSceneNarration(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sceneIndex, narrationPath }: { sceneIndex: number; narrationPath: string }) =>
      api.selectSceneNarration(sessionId, sceneIndex, narrationPath),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}
