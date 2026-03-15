/**
 * React hooks for project management
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import type { ProjectListItem, Project, CreateProjectRequest, UpdateProjectRequest } from '@/types';

// Hook to list all projects
export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: () => api.listProjects(),
    staleTime: 5000, // 5 seconds
  });
}

// Hook to get a single project
export function useProject(projectId: string) {
  return useQuery({
    queryKey: ['project', projectId],
    queryFn: () => api.getProject(projectId),
    enabled: !!projectId,
    refetchInterval: (query) => {
      // Auto-refetch if project is not completed
      return query.state.data && !query.state.data.completed ? 5000 : false;
    },
  });
}

// Hook to create a project
export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateProjectRequest) => api.createProject(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

// Hook to update a project
export function useUpdateProject(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: UpdateProjectRequest) => api.updateProject(projectId, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project', projectId] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

// Hook to delete a project
export function useDeleteProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) => api.deleteProject(projectId),
    onSuccess: (_, projectId) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      queryClient.removeQueries({ queryKey: ['project', projectId] });
    },
  });
}

// Hook to duplicate a project
export function useDuplicateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ projectId, newProjectId }: { projectId: string; newProjectId?: string }) =>
      api.duplicateProject(projectId, newProjectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}
