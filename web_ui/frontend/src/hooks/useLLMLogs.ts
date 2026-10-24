/**
 * useLLMLogs hook - LLM call log list + per-entry detail for the Logs page
 */
import { keepPreviousData, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { toast } from 'sonner';

const LIST_KEY_BASE = ['llm-logs'];

export function useLLMLogs(
  options: { refetchIntervalMs?: number; order?: 'asc' | 'desc' } = {}
) {
  const queryClient = useQueryClient();
  const order = options.order ?? 'desc';

  const listQuery = useQuery({
    queryKey: [...LIST_KEY_BASE, order],
    queryFn: () => api.listLLMLogs(500, order),
    refetchInterval: options.refetchIntervalMs ?? 10000,
    placeholderData: keepPreviousData, // keep the list visible while the other order loads
  });

  const clearMutation = useMutation({
    mutationFn: () => api.clearLLMLogs(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LIST_KEY_BASE });
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
