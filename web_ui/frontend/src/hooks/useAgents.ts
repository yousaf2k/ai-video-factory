/**
 * React hooks for agent management
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import type { UpdateGlobalConfigRequest } from '@/types';

// Hook to get available agents
export function useAgents() {
  return useQuery({
    queryKey: ['agents'],
    queryFn: () => api.getAgents(),
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

// Hook to get content of an agent file
export function useAgentContent(agentType: string | null, agentId: string | null) {
  return useQuery({
    queryKey: ['agent-content', agentType, agentId],
    queryFn: () => agentType && agentId ? api.getAgentContent(agentType, agentId) : Promise.resolve(''),
    enabled: !!agentType && !!agentId,
  });
}

// Hook to update content of an agent file
export function useUpdateAgentContent(agentType: string, agentId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (content: string) => api.updateAgentContent(agentType, agentId, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-content', agentType, agentId] });
    },
  });
}
