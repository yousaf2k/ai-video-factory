/**
 * useQueue hook - Hybrid polling + WebSocket for optimal performance
 * - Polling every 5s for general queue state
 * - WebSocket for real-time progress on active items
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { QueueItem, QueueStatistics, QueueItemStatus, GenerationType } from '../types';
import { api } from '../services/api';
import { toast } from 'sonner';

interface QueueData {
  items: QueueItem[];
  statistics: QueueStatistics;
  isPaused: boolean;
}

interface UseQueueOptions {
  sessionId?: string;
  enabled?: boolean;
}

export function useQueue({ sessionId, enabled = true }: UseQueueOptions = {}) {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const [wsConnected, setWsConnected] = useState(false);

  // Initial data fetch with 5-second polling
  const { data, isLoading, error, refetch } = useQuery<QueueData>({
    queryKey: ['queue', sessionId],
    queryFn: async () => {
      console.log('[useQueue] Fetching queue data...');
      try {
        const [itemsRes, statsRes, pausedRes] = await Promise.all([
          api.get(`/api/queue/items${sessionId ? `?session_id=${sessionId}` : ''}`),
          api.get('/api/queue/statistics'),
          api.get('/api/queue/paused')
        ]);

        console.log('[useQueue] Got items:', itemsRes.data.length);
        console.log('[useQueue] Got stats:', statsRes.data);

        return {
          items: itemsRes.data,
          statistics: statsRes.data,
          isPaused: pausedRes.data.is_paused
        };
      } catch (err) {
        console.error('[useQueue] Error fetching data:', err);
        throw err;
      }
    },
    enabled,
    refetchInterval: 5000 // Poll every 5 seconds for general state
  });

  // WebSocket for real-time active item updates
  useEffect(() => {
    if (!enabled) return;

    const connectWebSocket = () => {
      try {
        // Get backend URL from API base URL
        const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
        const wsProtocol = apiBaseUrl.startsWith('https') ? 'wss:' : 'ws:';
        // Replace http(s) with ws(s) protocol
        const wsUrl = apiBaseUrl.replace(/^https?:/, wsProtocol) + '/api/ws/progress/global';

        console.log('[useQueue] Connecting WebSocket to:', wsUrl);
        wsRef.current = new WebSocket(wsUrl);

        wsRef.current.onopen = () => {
          console.log('[useQueue] WebSocket connected');
          setWsConnected(true);
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
          }
        };

        wsRef.current.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            handleWebSocketMessage(message);
          } catch (e) {
            console.error('[useQueue] Failed to parse WebSocket message:', e);
          }
        };

        wsRef.current.onerror = (error) => {
          console.warn('[useQueue] WebSocket error (falling back to polling):', error);
          setWsConnected(false);
        };

        wsRef.current.onclose = () => {
          console.log('[useQueue] WebSocket disconnected, reconnecting in 5s...');
          setWsConnected(false);
          // Reconnect after 5 seconds
          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket();
          }, 5000);
        };
      } catch (error) {
        console.error('[useQueue] Failed to create WebSocket:', error);
        setWsConnected(false);
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [enabled, sessionId]);

  const handleWebSocketMessage = useCallback((message: any) => {
    // Only handle queue-related messages
    if (!message.type.startsWith('queue.')) return;

    console.log('[useQueue] WebSocket message:', message.type);

    // Invalidate queries for major state changes
    if (['queue.item_added', 'queue.item_removed', 'queue.item_cancelled',
         'queue.reordered', 'queue.paused', 'queue.resumed',
         'queue.cleared_completed', 'queue.statistics_updated'].includes(message.type)) {
      queryClient.invalidateQueries({ queryKey: ['queue', sessionId] });
    }

    // Update individual items for progress updates (more efficient)
    if (message.type === 'queue.item_progress') {
      const { item_id, progress } = message.data;
      queryClient.setQueryData<QueueData>(['queue', sessionId], (old) => {
        if (!old) return old;
        return {
          ...old,
          items: old.items.map(item =>
            item.item_id === item_id
              ? { ...item, progress }
              : item
          )
        };
      });
    }

    // Update item status
    if (['queue.item_started', 'queue.item_completed', 'queue.item_failed'].includes(message.type)) {
      queryClient.invalidateQueries({ queryKey: ['queue', sessionId] });
    }

    // Show toast notifications for important events
    switch (message.type) {
      case 'queue.item_failed':
        toast.error(`Generation failed: ${message.data.error_message || 'Unknown error'}`);
        break;
      case 'queue.paused':
        toast.info('Queue paused');
        break;
      case 'queue.resumed':
        toast.info('Queue resumed');
        break;
    }
  }, [queryClient, sessionId]);

  // Mutations
  const pauseQueue = useMutation({
    mutationFn: async () => {
      const response = await api.post('/api/queue/pause');
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue', sessionId] });
      toast.success('Queue paused');
    },
    onError: (error: any) => {
      toast.error(`Failed to pause queue: ${error.message}`);
    }
  });

  const resumeQueue = useMutation({
    mutationFn: async () => {
      const response = await api.post('/api/queue/resume');
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue', sessionId] });
      toast.success('Queue resumed');
    },
    onError: (error: any) => {
      toast.error(`Failed to resume queue: ${error.message}`);
    }
  });

  const cancelItem = useMutation({
    mutationFn: async (itemId: string) => {
      const response = await api.post(`/api/queue/items/${itemId}/cancel`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue', sessionId] });
      toast.success('Item cancelled');
    },
    onError: (error: any) => {
      toast.error(`Failed to cancel item: ${error.message}`);
    }
  });

  const cancelMultipleItems = useMutation({
    mutationFn: async (itemsToCancel: string[]) => {
      await Promise.all(
        itemsToCancel.map(id => api.post(`/api/queue/items/${id}/cancel`))
      );
      return itemsToCancel;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['queue', sessionId] });
      toast.success(`${data.length} item(s) cancelled`);
    },
    onError: (error: any) => {
      toast.error(`Failed to cancel items: ${error.message}`);
    }
  });

  const clearCompleted = useMutation({
    mutationFn: async () => {
      const response = await api.delete('/api/queue/completed');
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['queue', sessionId] });
      toast.success(`Cleared ${data.count} completed items`);
    },
    onError: (error: any) => {
      toast.error(`Failed to clear completed: ${error.message}`);
    }
  });

  const clearFailed = useMutation({
    mutationFn: async () => {
      const response = await api.delete('/api/queue/failed');
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['queue', sessionId] });
      toast.success(`Cleared ${data.count} failed items`);
    },
    onError: (error: any) => {
      toast.error(`Failed to clear failed: ${error.message}`);
    }
  });

  const clearCancelled = useMutation({
    mutationFn: async () => {
      const response = await api.delete('/api/queue/cancelled');
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['queue', sessionId] });
      toast.success(`Cleared ${data.count} cancelled items`);
    },
    onError: (error: any) => {
      toast.error(`Failed to clear cancelled: ${error.message}`);
    }
  });

  const reorderItems = useMutation({
    mutationFn: async (itemIds: string[]) => {
      const response = await api.put('/api/queue/items/reorder', { item_ids: itemIds });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue', sessionId] });
    },
    onError: (error: any) => {
      toast.error(`Failed to reorder: ${error.message}`);
    }
  });

  const updatePriority = useMutation({
    mutationFn: async ({ itemId, priority }: { itemId: string; priority: number }) => {
      const response = await api.put(`/api/queue/items/${itemId}/priority`, { priority });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue', sessionId] });
    },
    onError: (error: any) => {
      toast.error(`Failed to update priority: ${error.message}`);
    }
  });

  return {
    // Data
    items: data?.items || [],
    statistics: data?.statistics || {
      total: 0,
      queued: 0,
      active: 0,
      completed: 0,
      cancelled: 0,
      failed: 0,
      images: 0,
      videos: 0,
      flfi2v: 0,
      narrations: 0,
      backgrounds: 0,
      total_sessions: 0
    },
    isPaused: data?.isPaused || false,
    isLoading,
    error,
    wsConnected, // WebSocket connection status

    // Actions
    pauseQueue: pauseQueue.mutate,
    resumeQueue: resumeQueue.mutate,
    cancelItem: cancelItem.mutate,
    cancelMultipleItems: cancelMultipleItems.mutate,
    clearCompleted: clearCompleted.mutate,
    clearFailed: clearFailed.mutate,
    clearCancelled: clearCancelled.mutate,
    reorderItems: reorderItems.mutate,
    updatePriority: updatePriority.mutate,
    refetch
  };
}

export default useQueue;
