/**
 * React hooks for story management
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import type { Story, UpdateStoryRequest, Scene } from '@/types';

// Hook to update story
export function useUpdateStory(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (story: Story) => {
      const request: UpdateStoryRequest = { story };
      return api.updateStory(sessionId, request);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}

// Hook to regenerate story
export function useRegenerateStory(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (agent: string = 'default') => api.regenerateStory(sessionId, agent),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    },
  });
}
