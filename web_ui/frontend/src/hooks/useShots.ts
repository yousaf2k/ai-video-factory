/**
 * React hooks for shot management
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
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

// Hook to regenerate shot image
export function useRegenerateImage(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ shotIndex, force }: { shotIndex: number; force?: boolean }) =>
      api.regenerateShotImage(sessionId, shotIndex, force),
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
    mutationFn: ({ shotIndex, force }: { shotIndex: number; force?: boolean }) =>
      api.regenerateShotVideo(sessionId, shotIndex, force),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}
