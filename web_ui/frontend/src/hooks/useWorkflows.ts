/**
 * React hooks for workflow management
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';

// Hook to get available workflows
export function useWorkflows() {
  return useQuery({
    queryKey: ['workflows'],
    queryFn: () => api.listWorkflows(),
  });
}

// Hook to get content of a workflow file
export function useWorkflowContent(category: string | null, filename: string | null) {
  return useQuery({
    queryKey: ['workflow-content', category, filename],
    queryFn: () => category && filename ? api.getWorkflowContent(category, filename) : Promise.resolve(''),
    enabled: !!category && !!filename,
  });
}

// Hook to update content of a workflow file
export function useUpdateWorkflowContent(category: string, filename: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (content: string) => api.updateWorkflowContent(category, filename, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflow-content', category, filename] });
    },
  });
}
