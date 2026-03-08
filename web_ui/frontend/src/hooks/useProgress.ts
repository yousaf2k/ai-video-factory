import { useState, useEffect, useCallback } from 'react';

interface ProgressMessage {
    type: string;
    session_id: string;
    shot_index?: number;
    shot_id?: string;
    scene_index?: number;
    step?: string;
    progress?: number;
}

export const useProgress = (sessionId: string | undefined, onCompleted?: (id: string | number, type: 'shot' | 'scene') => void) => {
    // We now map progress by stable UUID strings rather than index integers, to survive insertion/deletion reindexes
    const [shotProgress, setShotProgress] = useState<Record<string, number>>({});
    const [sceneProgress, setSceneProgress] = useState<Record<number, number>>({});

    useEffect(() => {
        if (!sessionId) return;

        // Determine WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        // For development, we might need to point to the backend port (e.g., 8000)
        // In production, the backend and frontend are likely on the same host/port
        const backendHost = process.env.NEXT_PUBLIC_API_URL
            ? process.env.NEXT_PUBLIC_API_URL.replace(/^https?:\/\//, '')
            : '127.0.0.1:8000';

        const wsUrl = `${protocol}//${backendHost}/api/ws/progress/${sessionId}`;

        console.log(`Connecting to progress WebSocket: ${wsUrl}`);
        let socket: WebSocket | null = null;
        let reconnectTimeout: NodeJS.Timeout;
        let intentionallyClosed = false;

        const connect = () => {
            if (intentionallyClosed) return;
            socket = new WebSocket(wsUrl);

            socket.onmessage = (event) => {
                try {
                    const data: ProgressMessage = JSON.parse(event.data);

                    // Handle Shot Progress
                    const shotKey = data.shot_id || (data.shot_index !== undefined ? data.shot_index.toString() : null);

                    // Handle Scene Progress
                    const sceneKey = data.scene_index !== undefined ? data.scene_index : null;

                    if (data.type === 'progress') {
                        if (shotKey && data.progress !== undefined) {
                            setShotProgress((prev) => ({
                                ...prev,
                                [shotKey]: data.progress!,
                            }));
                        } else if (sceneKey !== null && data.progress !== undefined) {
                            setSceneProgress((prev) => ({
                                ...prev,
                                [sceneKey]: data.progress!,
                            }));
                        }
                    } else if (data.type === 'completed') {
                        if (shotKey) {
                            setShotProgress((prev) => {
                                const next = { ...prev };
                                delete next[shotKey];
                                return next;
                            });
                            if (onCompleted) {
                                onCompleted(shotKey, 'shot');
                            }
                        } else if (sceneKey !== null) {
                            setSceneProgress((prev) => {
                                const next = { ...prev };
                                delete next[sceneKey];
                                return next;
                            });
                            if (onCompleted) {
                                onCompleted(sceneKey, 'scene');
                            }
                        }
                    } else if (data.type === 'cancelled') {
                        if (shotKey) {
                            setShotProgress((prev) => {
                                const next = { ...prev };
                                delete next[shotKey];
                                return next;
                            });
                        } else if (sceneKey !== null) {
                            setSceneProgress((prev) => {
                                const next = { ...prev };
                                delete next[sceneKey];
                                return next;
                            });
                        } else {
                            setShotProgress({});
                            setSceneProgress({});
                        }
                    }
                } catch (err) {
                    console.error('Error parsing progress message:', err);
                }
            };

            socket.onclose = () => {
                // If connection drops unexpectedly (e.g. backend crash), clear active states
                // so the user isn't stuck with frozen spinners and can restart or refresh
                setShotProgress({});

                if (!intentionallyClosed) {
                    console.log('Progress WebSocket disconnected. Reconnecting in 3s...');
                    reconnectTimeout = setTimeout(connect, 3000);
                }
            };

            socket.onerror = () => {
                if (!intentionallyClosed) {
                    console.warn('Progress WebSocket connection error, will retry...');
                }
                socket?.close();
            };
        };

        connect();

        return () => {
            intentionallyClosed = true;
            if (socket) {
                socket.onclose = null;
                socket.close();
            }
            clearTimeout(reconnectTimeout);
        };
    }, [sessionId]);

    const clearProgress = useCallback((shotIndex: number) => {
        setShotProgress((prev) => {
            const next = { ...prev };
            delete next[shotIndex];
            return next;
        });
    }, []);

    return { shotProgress, sceneProgress, clearProgress };
};
