/**
 * React hooks for director management
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import type { UpdateGlobalConfigRequest } from '@/types';

// Hook to get available directors
export function useDirectors() {
  return useQuery({
    queryKey: ['directors'],
    queryFn: () => api.getDirectors(),
  });
}

// Hook to get the hierarchical director file tree (categories + base files)
export function useDirectorTree() {
  return useQuery({
    queryKey: ['director-tree'],
    queryFn: () => api.getDirectorTree(),
  });
}

// Hook to get global config
export function useConfig() {
  return useQuery({
    queryKey: ['config'],
    queryFn: () => api.getConfig(),
  });
}

// Hook to update global config
export function useUpdateConfig() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: UpdateGlobalConfigRequest) => api.updateConfig(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] });
    },
  });
}

// Hook to get the raw content of an director file (keeps {{include:...}} directives)
export function useDirectorContent(directorType: string | null, directorId: string | null) {
  return useQuery({
    queryKey: ['director-content', directorType, directorId],
    queryFn: () =>
      directorType && directorId
        ? api.getDirectorFileRaw(directorType, directorId)
        : Promise.resolve({ content: '', includes: [] as string[] }),
    enabled: !!directorType && !!directorId,
  });
}

// Hook to get the preview structure of an director file (includes resolved as nested segments)
export function useDirectorPreview(
  directorType: string | null,
  directorId: string | null,
  enabled: boolean
) {
  return useQuery({
    queryKey: ['director-preview', directorType, directorId],
    queryFn: () =>
      directorType && directorId
        ? api.getDirectorPreview(directorType, directorId)
        : Promise.resolve({ content: '', expanded: '', segments: [] }),
    enabled: enabled && !!directorType && !!directorId,
  });
}

// Hook to update content of an director file
export function useUpdateDirectorContent(directorType: string, directorId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (content: string) => api.updateDirectorContent(directorType, directorId, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['director-content', directorType, directorId] });
      queryClient.invalidateQueries({ queryKey: ['director-preview', directorType, directorId] });
    },
  });
}
