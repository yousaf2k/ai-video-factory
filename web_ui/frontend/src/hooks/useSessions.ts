/**
 * React hooks for session management
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import type { SessionListItem, Session, CreateSessionRequest, UpdateSessionRequest } from '@/types';

// Hook to list all sessions
export function useSessions() {
  return useQuery({
    queryKey: ['sessions'],
    queryFn: () => api.listSessions(),
    staleTime: 5000, // 5 seconds
  });
}

// Hook to get a single session
export function useSession(sessionId: string) {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => api.getSession(sessionId),
    enabled: !!sessionId,
    staleTime: 10000, // 10 seconds
    refetchInterval: (data) => {
      // Auto-refetch if session is not completed
      return data && !data.completed ? 5000 : false;
    },
  });
}

// Hook to create a session
export function useCreateSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateSessionRequest) => api.createSession(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
}

// Hook to update a session
export function useUpdateSession(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: UpdateSessionRequest) => api.updateSession(sessionId, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
}

// Hook to delete a session
export function useDeleteSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sessionId: string) => api.deleteSession(sessionId),
    onSuccess: (_, sessionId) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      queryClient.removeQueries({ queryKey: ['session', sessionId] });
    },
  });
}

// Hook to duplicate a session
export function useDuplicateSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ sessionId, newSessionId }: { sessionId: string; newSessionId?: string }) =>
      api.duplicateSession(sessionId, newSessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
}
