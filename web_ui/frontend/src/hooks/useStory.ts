/**
 * React hooks for story management
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import type { Story, UpdateStoryRequest, Scene } from '@/types';

// Hook to update story
export function useUpdateStory(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (story: Story) => {
      const request: UpdateStoryRequest = { story };
      return api.updateStory(projectId, request);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook to generate story
export function useGenerateStory(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (agent: string = 'default') => api.generateStory(projectId, agent),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
    },
  });
}
