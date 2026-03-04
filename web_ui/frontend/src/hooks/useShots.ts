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
    mutationFn: ({ shotIndex, force, imageMode, imageWorkflow, seed }: { shotIndex: number; force?: boolean; imageMode?: string; imageWorkflow?: string; seed?: number }) =>
      api.regenerateShotImage(sessionId, shotIndex, force, imageMode, imageWorkflow, seed),
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
    mutationFn: ({ shotIndex, force, videoWorkflow }: { shotIndex: number; force?: boolean; videoWorkflow?: string }) =>
      api.regenerateShotVideo(sessionId, shotIndex, force, videoWorkflow),
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
