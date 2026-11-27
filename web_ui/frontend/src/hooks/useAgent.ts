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
  AgentLiveTurn,
  AgentStreamEvent,
  ContextUsage,
  McpServerConfig,
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

export type AgentRunState = 'idle' | 'running' | 'stopping';

/** How long Stop waits for the backend to finish cancelling before the UI moves on. */
const STOP_TIMEOUT_MS = 8000;

/**
 * Streaming agent chat over WebSocket.
 * Manages the socket lifecycle, exposes send/stop and the turn that is
 * streaming right now (`live`).
 */
export function useAgentChatStream(options?: {
  /** The backend bound the outgoing message to a conversation. */
  onConversation?: (conversationId: string) => void;
}) {
  const queryClient = useQueryClient();
  const [connected, setConnected] = useState(false);
  const [runState, setRunState] = useState<AgentRunState>('idle');
  const [live, setLive] = useState<AgentLiveTurn | null>(null);
  /** Latest context-window usage reported by the engine. */
  const [contextUsage, setContextUsage] = useState<ContextUsage | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const conversationIdRef = useRef<string | null>(null);
  // The same state as mirrors, for use inside the socket handlers.
  const runStateRef = useRef<AgentRunState>('idle');
  const liveRef = useRef<AgentLiveTurn | null>(null);
  const stopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const setRun = useCallback((state: AgentRunState) => {
    if (stopTimerRef.current) {
      clearTimeout(stopTimerRef.current);
      stopTimerRef.current = null;
    }
    runStateRef.current = state;
    setRunState(state);
  }, []);

  const updateLive = useCallback((update: (turn: AgentLiveTurn | null) => AgentLiveTurn | null) => {
    liveRef.current = update(liveRef.current);
    setLive(liveRef.current);
  }, []);

  /** A turn is only saved once it has ended — pick up the saved copy then. */
  const refetchSaved = useCallback((conversationId: string | null) => {
    queryClient.invalidateQueries({ queryKey: ['agent-config'] });
    if (conversationId) {
      queryClient.invalidateQueries({ queryKey: ['agent-conversation', conversationId] });
    }
  }, [queryClient]);

  const connect = useCallback(() => {
    if (socketRef.current && socketRef.current.readyState <= WebSocket.OPEN) return;
    let socket: WebSocket;
    try {
      socket = new WebSocket(api.getAgentWsUrl());
    } catch {
      setConnected(false);
      return;
    }
    socketRef.current = socket;
    socket.onopen = () => setConnected(true);
    socket.onclose = () => {
      setConnected(false);
      // A run cannot outlive its socket: the backend cancels it.
      if (runStateRef.current !== 'idle') {
        updateLive((turn) => turn && {
          ...turn,
          events: [...turn.events, {
            type: 'error', message: 'Connection to the agent was lost.', ts: Date.now(),
          }],
        });
        setRun('idle');
        refetchSaved(liveRef.current?.conversationId ?? null);
      }
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
        updateLive((turn) => turn && { ...turn, conversationId: data.conversation_id });
        optionsRef.current?.onConversation?.(data.conversation_id);
      } else if (data.type === 'context_usage') {
        setContextUsage({
          prompt_chars: data.prompt_chars,
          est_tokens: data.est_tokens,
          limit_tokens: data.limit_tokens,
          percent: data.percent,
        });
      } else if (data.type === 'pong') {
        return;
      } else {
        if (data.type === 'done') {
          setRun('idle');
          refetchSaved(liveRef.current?.conversationId ?? conversationIdRef.current);
        } else if (data.type === 'error') {
          // An error outside a run (e.g. "Conversation not found") has no turn
          // to surface in, so it becomes a toast instead.
          setRun('idle');
          if (!liveRef.current) toast.error(data.message);
        }
        updateLive((turn) => turn && {
          ...turn, events: [...turn.events, { ...data, ts: Date.now() }],
        });
      }
    };
  }, [refetchSaved, setRun, updateLive]);

  useEffect(() => {
    connect();
    return () => {
      const socket = socketRef.current;
      socketRef.current = null;
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
      if (stopTimerRef.current) clearTimeout(stopTimerRef.current);
    };
  }, [connect]);

  /** Returns false when the socket is down (nothing was sent). */
  const sendMessage = useCallback(
    (message: string, projectId: string | null, baseCount: number): boolean => {
      const socket = socketRef.current;
      if (!socket || socket.readyState !== WebSocket.OPEN) return false;
      updateLive(() => ({
        message, conversationId: conversationIdRef.current, baseCount, events: [],
      }));
      setRun('running');
      socket.send(
        JSON.stringify({
          type: 'chat',
          message,
          project_id: projectId,
          conversation_id: conversationIdRef.current,
        }),
      );
      return true;
    },
    [setRun, updateLive],
  );

  const stop = useCallback(() => {
    const socket = socketRef.current;
    if (runStateRef.current !== 'running' || !socket || socket.readyState !== WebSocket.OPEN) return;
    setRun('stopping');
    // Never hang on "stopping" if the backend does not acknowledge.
    stopTimerRef.current = setTimeout(() => setRun('idle'), STOP_TIMEOUT_MS);
    socket.send(JSON.stringify({ type: 'stop' }));
  }, [setRun]);

  /** Point the next message at a conversation (null = the backend creates one). */
  const setConversation = useCallback((id: string | null) => {
    conversationIdRef.current = id;
  }, []);

  return {
    connected,
    runState,
    live,
    contextUsage,
    sendMessage,
    stop,
    setConversation,
  };
}
