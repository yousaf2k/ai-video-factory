/**
 * React Query hooks + WebSocket chat for the AI Agent Assistant.
 */
'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { api, getApiErrorMessage } from '@/services/api';
import type {
  AgentConfigResponse,
  AgentConversationDetail,
  AgentStreamEvent,
  ContextUsage,
  McpServerConfig,
  TimedAgentEvent,
} from '@/types/agent';

export function useAgentConfig() {
  return useQuery<AgentConfigResponse>({
    queryKey: ['agent-config'],
    queryFn: () => api.getAgentConfig(),
    staleTime: 10_000,
  });
}

export function useUpdateAgentConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (update: Parameters<typeof api.updateAgentConfig>[0]) => api.updateAgentConfig(update),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-config'] });
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to update agent settings')),
  });
}

export function useAgentConversation(conversationId: string | null) {
  return useQuery<AgentConversationDetail>({
    queryKey: ['agent-conversation', conversationId],
    queryFn: () => api.getAgentConversation(conversationId as string),
    enabled: !!conversationId,
  });
}

export function useDeleteAgentConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteAgentConversation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-config'] });
      queryClient.invalidateQueries({ queryKey: ['agent-conversation'] });
    },
  });
}

export function useAgentSkillActions() {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['agent-config'] });
  const create = useMutation({
    mutationFn: (request: { name: string; description: string; content: string }) =>
      api.createAgentSkill(request),
    onSuccess: () => {
      invalidate();
      toast.success('Skill created');
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to create skill')),
  });
  const remove = useMutation({
    mutationFn: (name: string) => api.deleteAgentSkill(name),
    onSuccess: () => {
      invalidate();
      toast.success('Skill deleted');
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Failed to delete skill')),
  });
  return { create, remove };
}

export function useTestAgentLlm() {
  return useMutation({
    mutationFn: () => api.testAgentLlm(),
  });
}

/**
 * Streaming agent chat over WebSocket.
 * Manages the socket lifecycle, exposes send/stop and the live event stream.
 */
export function useAgentChatStream(options?: {
  onFinal?: (conversationId: string | null, content: string) => void;
  onError?: (message: string) => void;
}) {
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  /** Live event stream for the in-flight message, each stamped with a timestamp. */
  const [liveEvents, setLiveEvents] = useState<TimedAgentEvent[]>([]);
  /** Latest context-window usage reported by the engine. */
  const [contextUsage, setContextUsage] = useState<ContextUsage | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const conversationIdRef = useRef<string | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const connect = useCallback(() => {
    if (socketRef.current && socketRef.current.readyState <= WebSocket.OPEN) return;
    try {
      const socket = new WebSocket(api.getAgentWsUrl());
      socketRef.current = socket;
      socket.onopen = () => setConnected(true);
      socket.onclose = () => {
        setConnected(false);
        setTimeout(() => {
          // Auto-reconnect while the component is still mounted.
          if (socketRef.current === socket) connect();
        }, 3000);
      };
      socket.onmessage = (event) => {
        let data: AgentStreamEvent;
        try {
          data = JSON.parse(event.data);
        } catch {
          return;
        }
        if (data.type === 'conversation') {
          conversationIdRef.current = data.conversation_id;
        } else if (data.type === 'context_usage') {
          setContextUsage({
            prompt_chars: data.prompt_chars,
            est_tokens: data.est_tokens,
            limit_tokens: data.limit_tokens,
            percent: data.percent,
          });
        } else if (data.type === 'done') {
          setBusy(false);
        } else if (data.type === 'error') {
          setBusy(false);
          optionsRef.current?.onError?.(data.message);
        } else if (data.type === 'final') {
          optionsRef.current?.onFinal?.(conversationIdRef.current, data.content);
        }
        if (data.type !== 'pong' && data.type !== 'conversation' && data.type !== 'context_usage') {
          setLiveEvents((prev) => [...prev, { ...data, ts: Date.now() }]);
        }
      };
    } catch {
      setConnected(false);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      const socket = socketRef.current;
      socketRef.current = null;
      socket?.close();
    };
  }, [connect]);

  const sendMessage = useCallback(
    (message: string, projectId?: string | null) => {
      const socket = socketRef.current;
      if (!socket || socket.readyState !== WebSocket.OPEN) {
        optionsRef.current?.onError?.('Agent socket not connected — is the backend running?');
        return;
      }
      setLiveEvents([]);
      setBusy(true);
      socket.send(
        JSON.stringify({
          type: 'chat',
          message,
          project_id: projectId ?? null,
          conversation_id: conversationIdRef.current,
        }),
      );
    },
    [],
  );

  const stop = useCallback(() => {
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'stop' }));
      setBusy(false);
    }
  }, []);

  const resetConversation = useCallback(() => {
    conversationIdRef.current = null;
    setLiveEvents([]);
    setContextUsage(null);
  }, []);

  const setConversation = useCallback((id: string | null) => {
    conversationIdRef.current = id;
    setLiveEvents([]);
    setContextUsage(null);
  }, []);

  return {
    connected,
    busy,
    liveEvents,
    contextUsage,
    sendMessage,
    stop,
    resetConversation,
    setConversation,
    conversationIdRef,
  };
}
