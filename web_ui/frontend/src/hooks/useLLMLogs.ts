/**
 * useLLMLogs hook - LLM call log list + per-entry detail for the Logs page
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { toast } from 'sonner';

const LIST_KEY = ['llm-logs'];

export function useLLMLogs(options: { refetchIntervalMs?: number } = {}) {
  const queryClient = useQueryClient();

  const listQuery = useQuery({
    queryKey: LIST_KEY,
    queryFn: () => api.listLLMLogs(500),
    refetchInterval: options.refetchIntervalMs ?? 10000,
  });

  const clearMutation = useMutation({
    mutationFn: () => api.clearLLMLogs(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LIST_KEY });
      toast.success('LLM call log cleared');
    },
    onError: () => {
      toast.error('Failed to clear LLM call log');
    },
  });

  return {
    entries: listQuery.data?.entries ?? [],
    total: listQuery.data?.total ?? 0,
    isLoading: listQuery.isLoading,
    error: listQuery.error as Error | null,
    refetch: listQuery.refetch,
    clearLogs: clearMutation.mutate,
    isClearing: clearMutation.isPending,
  };
}

export function useLLMLogDetail(entryId: string | null) {
  return useQuery({
    queryKey: ['llm-logs', 'detail', entryId],
    queryFn: () => api.getLLMLog(entryId!),
    enabled: !!entryId,
  });
}
