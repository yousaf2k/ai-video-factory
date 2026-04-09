"use client";

import { toast } from 'sonner';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  DndContext,
  DragEndEvent,
  useSensor,
  useSensors,
  PointerSensor
} from '@dnd-kit/core';
import { useEditorStore, Clip } from '@/store/useEditorStore';
import { Timeline } from './Timeline';
import { VideoPreview } from './VideoPreview';
import { AssetBrowser } from './AssetBrowser';
import { api } from '@/services/api';
import { Shot } from '@/types';

interface EditorLayoutProps {
  projectId?: string;
}

export function EditorLayout({ projectId }: EditorLayoutProps) {
  const isPlaying = useEditorStore((state: any) => state.isPlaying);
  const setIsPlaying = useEditorStore((state: any) => state.setIsPlaying);
  const zoom = useEditorStore((state: any) => state.zoom);
  const addClip = useEditorStore((state: any) => state.addClip);
  const updateClip = useEditorStore((state: any) => state.updateClip);
  const setClips = useEditorStore((state: any) => state.setClips);
  const duration = useEditorStore((state: any) => state.duration);
  const tracks = useEditorStore((state: any) => state.tracks);
  const setDuration = useEditorStore((state: any) => state.setDuration);
  const clearStore = useEditorStore((state: any) => state.clear);
  const selectedClipId = useEditorStore((state: any) => state.selectedClipId);
  const clips = useEditorStore((state: any) => state.clips);
  const dragMode = useEditorStore((state: any) => state.dragMode);
  const aspectRatio = useEditorStore((state: any) => state.aspectRatio);
  const setAspectRatio = useEditorStore((state: any) => state.setAspectRatio);

  const [activeDragData, setActiveDragData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'media' | 'stickers' | 'effects' | 'transitions' | 'captions' | 'filters' | 'adjust'>('media');
  const [activeTool, setActiveTool] = useState<'video' | 'speed' | 'animation' | 'adjust' | 'ai-stylize'>('video');
  const [showExportModal, setShowExportModal] = useState(false);
  const [selectedResolution, setSelectedResolution] = useState('720p');
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [exportStatus, setExportStatus] = useState('');
  const [currentExportId, setCurrentExportId] = useState<string | null>(null);
  const mousePosRef = useRef({ x: 0, y: 0, clipOffset: 0 });
  const lastToastedExportIdRef = useRef<string | null>(null);

  const loadProject = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const project = await api.getProject(id);
      clearStore();
      setAspectRatio(project.aspect_ratio || '16:9');

      const newClips: Clip[] = [];
      let currentVideoTime = 0;
      let currentAudioTime = 0;

      if (project.shots) {
        project.shots.forEach((shot: Shot, index: number) => {
          const shotDuration = 5;

          if (shot.video_path) {
            newClips.push({
              id: `v-${shot.index}-${index}`,
              trackId: 'v1',
              type: 'video',
              name: shot.character_name ? `${shot.character_name} - ${shot.index}` : `Shot ${shot.index}`,
              url: api.getAssetUrl(id, 'videos', shot.video_path.split(/[\\/]/).pop() || ''),
              startAt: currentVideoTime,
              duration: shotDuration,
              sourceStart: 0,
              sourceDuration: shotDuration
            });
            currentVideoTime += shotDuration;
          } else if (shot.is_flfi2v) {
             if (shot.meeting_video_path) {
                newClips.push({
                  id: `v-meet-${shot.index}`,
                  trackId: 'v1',
                  type: 'video',
                  name: `Meeting - ${shot.character_name}`,
                  url: api.getAssetUrl(id, 'videos', shot.meeting_video_path.split(/[\\/]/).pop() || ''),
                  startAt: currentVideoTime,
                  duration: shotDuration,
                  sourceStart: 0,
                  sourceDuration: shotDuration
                });
                currentVideoTime += shotDuration;
             }
             if (shot.departure_video_path) {
                newClips.push({
                  id: `v-dep-${shot.index}`,
                  trackId: 'v2',
                  type: 'video',
                  name: `Departure - ${shot.character_name}`,
                  url: api.getAssetUrl(id, 'videos', shot.departure_video_path.split(/[\\/]/).pop() || ''),
                  startAt: currentVideoTime - shotDuration,
                  duration: shotDuration,
                  sourceStart: 0,
                  sourceDuration: shotDuration
                });
             }
          }
        });
      }

      if (project.story && project.story.scenes) {
        project.story.scenes.forEach((scene: any, index: number) => {
          if (scene.narration_path) {
            newClips.push({
              id: `a-scene-${index}`,
              trackId: 'a1',
              type: 'audio',
              name: `Narration Scene ${index + 1}`,
              url: `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/projects/${id}/narration/${scene.narration_path.split(/[\\/]/).pop()}`,
              startAt: currentAudioTime,
              duration: scene.scene_duration || 5,
              sourceStart: 0,
              sourceDuration: scene.scene_duration || 5
            });
            currentAudioTime += (scene.scene_duration || 5);
          }
        });
      }

      setClips(newClips);

      const maxEndTime = newClips.reduce((max, clip) => {
        const endTime = clip.startAt + clip.duration;
        return Math.max(max, endTime);
      }, 0);

      const duration = maxEndTime + 10;
      setDuration(duration);
    } catch (err: any) {
      console.error("Failed to load project:", err);
      setError(err.message || "Failed to load project data");
    } finally {
      setIsLoading(false);
    }
  }, [clearStore, setClips, addClip, setDuration]);

  useEffect(() => {
    if (projectId) {
      loadProject(projectId);
    }
  }, [projectId, loadProject]);

  // WebSocket for real-time export progress
  useEffect(() => {
    if (!projectId || !isExporting) return;

    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connectWS = () => {
      try {
        const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
        const wsProtocol = apiBaseUrl.startsWith('https') ? 'wss:' : 'ws:';
        
        // Ensure wsUrl is clean (no double slashes if apiBaseUrl has one)
        const base = apiBaseUrl.replace(/^https?:/, wsProtocol).replace(/\/$/, '');
        const wsUrl = `${base}/api/ws/progress/${projectId}`;

        console.log('[Editor] 📡 Connecting WebSocket:', wsUrl);
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log('[Editor] ✅ WebSocket Connected');
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            if (message.type === 'editor_export' && message.data.export_id === currentExportId) {
              const { status, progress, message: statusMsg, filename } = message.data;
              
              setExportProgress(progress);
              setExportStatus(statusMsg || status);

              if (status === 'completed') {
                setExportStatus('Export complete!');
                
                // Only toast once per export
                if (lastToastedExportIdRef.current !== currentExportId) {
                  lastToastedExportIdRef.current = currentExportId;
                  toast.success('Video Exported Successfully!', {
                    description: `File: ${filename || 'export.mp4'}`,
                    duration: 5000,
                  });
                }

                // Auto-download
                setTimeout(() => {
                   window.open(`${apiBaseUrl}/api/editor/export/${projectId}/download/${currentExportId}`, '_blank');
                }, 1000);
                
                setIsExporting(false);
              } else if (status === 'failed') {
                setExportStatus('Export failed: ' + (message.data.error || 'Unknown error'));
                setIsExporting(false);
              }
            }
          } catch (e) {
            console.error('[Editor] ❌ WS parse error:', e);
          }
        };

        ws.onclose = (event) => {
          console.log(`[Editor] 🔌 WS closed (Code: ${event.code}).`);
          
          // Fallback to localhost if first attempt with hostname failed
          if (isExporting && !apiBaseUrl.includes('127.0.0.1') && !apiBaseUrl.includes('localhost')) {
            console.log('[Editor] 🔄 Retrying with localhost fallback...');
            const fallbackBase = apiBaseUrl.replace(window.location.hostname, '127.0.0.1')
                                        .replace(/^https?:/, wsProtocol)
                                        .replace(/\/$/, '');
            const fallbackUrl = `${fallbackBase}/api/ws/progress/${projectId}`;
            
            // This is a one-time attempt to switch to localhost
            ws = new WebSocket(fallbackUrl);
            // ... setup similar handlers or just let it fail to polling
          }

          if (isExporting) {
            reconnectTimeout = setTimeout(connectWS, 3000);
          }
        };

        ws.onerror = (err: any) => {
          console.error('[Editor] 🚨 WS error:', err.message || 'Connection refused or closed by server');
        };
      } catch (e) {
        console.error('[Editor] 🚨 WS initialization failed:', e);
      }
    };

    connectWS();

    return () => {
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [projectId, isExporting, currentExportId]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 1, // Reduced from 8 to allow 1-pixel drags
      },
    })
  );

  const handleDragStart = (event: any) => {
    setActiveDragData(event.active.data.current);

    // Track the offset between mouse position and clip position for precise dragging
    const dragData = event.active.data.current;
    if (dragData && dragData.startAt !== undefined) {
      const timelineContent = document.querySelector('.timeline-content-area');
      if (timelineContent) {
        const timelineRect = timelineContent.getBoundingClientRect();
        const activatorEvent = event.activatorEvent as PointerEvent;
        const mouseClickX = activatorEvent.clientX;

        // Calculate where the mouse clicked relative to the clip's start position
        const clipStartPixel = dragData.startAt * zoom;
        const mouseRelativeX = mouseClickX - timelineRect.left;
        const offset = mouseRelativeX - clipStartPixel;

        console.log('🎯 DRAG START - Mouse offset from clip start:', offset, 'pixels');
        console.log('   Clip startAt:', dragData.startAt, '=', clipStartPixel, 'px');
        console.log('   Mouse at:', mouseRelativeX, 'px from timeline left');

        // Store the offset for use in handleDragEnd
        mousePosRef.current = {
          x: mouseClickX,
          y: activatorEvent.clientY,
          clipOffset: offset
        };
      }
    }
  };

  const handleDragMove = (event: any) => {
    // Track CURRENT mouse position during drag, not drag start position
    if (event.activatorEvent) {
      const pointerEvent = event.activatorEvent as PointerEvent;
      mousePosRef.current = {
        x: pointerEvent.clientX,
        y: pointerEvent.clientY,
        clipOffset: mousePosRef.current.clipOffset || 0
      };
    }
    // Also try to get current position from event
    if (event.delta) {
      // Update based on delta movement
      mousePosRef.current = {
        x: mousePosRef.current.x + event.delta.x,
        y: mousePosRef.current.y + event.delta.y,
        clipOffset: mousePosRef.current.clipOffset || 0
      };
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    // Clear drag data immediately
    setActiveDragData(null);

    if (over && over.id.toString().startsWith('track-')) {
      const trackId = over.data.current?.trackId as string;
      const dragData = active.data.current;

      if (!trackId || !dragData) return;

      // Skip ghost clips
      if (dragData.id && dragData.id.startsWith('ghost-')) return;

      // Get timeline content area
      const timelineContent = document.querySelector('.timeline-content-area');
      if (!timelineContent) {
        console.error('Timeline content area not found');
        return;
      }

      const timelineRect = timelineContent.getBoundingClientRect();
      const scrollContainer = timelineContent as HTMLElement;
      const scrollLeft = scrollContainer.scrollLeft || 0;

      // Get current mouse position from drag tracking, NOT drag start position
      // The tracked ref has the correct current position, activatorEvent has drag start position
      const currentMouseX = mousePosRef.current.x;
      const currentMouseY = mousePosRef.current.y;
      const activatorEvent = event.activatorEvent as PointerEvent;

      // Calculate position within timeline - using CURRENT mouse position
      const relativeX = currentMouseX - timelineRect.left;

      // Get the offset from where we clicked on the clip to the clip's left edge
      const clipOffset = mousePosRef.current.clipOffset || 0;

      console.log('🖱️ MOUSE POSITION DEBUG:');
      console.log('   Activator (drag start) X:', activatorEvent?.clientX);
      console.log('   Current (drag end) X:', currentMouseX);
      console.log('   Tracked ref X:', mousePosRef.current.x);
      console.log('   Clip offset:', clipOffset, 'pixels');
      console.log('   Using X:', currentMouseX, 'for calculations');

      // Calculate drop time, accounting for where we clicked on the clip
      let dropTime = (relativeX - clipOffset) / zoom;
      if (dropTime < 0) dropTime = 0;
      // Only snap to grid for Track 1 (V1) - Track 2 allows exact pixel positioning
      if (trackId === 'v1') {
        dropTime = Math.round(dropTime * 10) / 10; // Snap to 0.1s grid for Track 1
      }
      // Track 2: no snapping - exact pixel positioning

      console.log('   Calculated drop time (before offset correction):', relativeX / zoom);
      console.log('   Calculated drop time (after offset correction):', dropTime);

      // Debug: Show where each clip is visually and which clip we're dropping on
      const trackClips = clips.filter((c: any) => c.trackId === trackId).sort((a: any, b: any) => a.startAt - b.startAt);

      console.log('=== DRAG END ===');
      console.log('Clip being dragged:', dragData.id, dragData.name);
      console.log('Target track:', trackId);
      console.log('Mouse X (drag start):', activatorEvent?.clientX);
      console.log('Mouse X (drag end):', currentMouseX);
      console.log('Timeline left:', timelineRect.left);
      console.log('Timeline width:', timelineRect.width);
      console.log('Timeline right:', timelineRect.right);
      console.log('Relative X:', relativeX, 'pixels from timeline left');
      console.log('Zoom:', zoom);
      console.log('Calculated drop time:', dropTime, 'seconds');

      // Check if timeline is being clipped or has scroll issues
      console.log('Timeline bounds:', {
        left: timelineRect.left,
        top: timelineRect.top,
        right: timelineRect.right,
        bottom: timelineRect.bottom,
        width: timelineRect.width,
        height: timelineRect.height
      });

      console.log('Clip positions on timeline:');
      let dropClip: any = null;
      trackClips.forEach((clip: any) => {
        const pixelStart = clip.startAt * zoom;
        const pixelEnd = (clip.startAt + clip.duration) * zoom;
        const isOverClip = relativeX >= pixelStart && relativeX < pixelEnd;
        // Don't detect dropping on the clip being dragged
        const showHere = isOverClip && clip.id !== dragData.id ? '← YOU ARE HERE' : '';
        const isDraggedClip = clip.id === dragData.id ? '(being dragged)' : '';
        console.log(`  ${clip.name}: ${clip.startAt}s (${pixelStart}px) to ${clip.startAt + clip.duration}s (${pixelEnd}px) ${showHere} ${isDraggedClip}`);
        if (isOverClip && clip.id !== dragData.id) dropClip = clip;
      });

      // Visual test - show where mouse actually is
      console.log('🎯 MOUSE POSITION DEBUG:');
      console.log(`   You clicked at pixel ${relativeX} on the timeline`);
      console.log(`   This should be around ${relativeX / zoom} seconds`);
      const estimatedClip = Math.floor(relativeX / 50); // 50px per clip
      console.log(`   Estimated clip position: ${estimatedClip + 1} (out of ${trackClips.length} clips)`);

      if (dropClip) {
        console.log(`You dropped on top of: ${dropClip.name} at ${dropClip.startAt}s`);
        dropTime = dropClip.startAt; // Use the clip's start time instead of mouse position
      } else {
        console.log('You dropped in empty space or between clips');

        // For Track 1 (V1): Find closest clip for queue reordering
        // For Track 2 (V2): Use exact mouse position
        if (trackId === 'v1') {
          // Use actual pixel position to find which clip area you're closest to
          console.log('Finding closest clip to drop position (Track 1 queue mode)...');

          let closestClip: any = null;
          let closestDistance = Infinity;

          trackClips.forEach((clip: any) => {
            const clipCenter = (clip.startAt * zoom) + ((clip.duration * zoom) / 2);
            const distance = Math.abs(relativeX - clipCenter);
            if (distance < closestDistance && clip.id !== dragData.id) {
              closestDistance = distance;
              closestClip = clip;
            }
          });

          if (closestClip) {
            console.log(`Closest clip is: ${closestClip.name} at ${closestClip.startAt}s (distance: ${closestDistance.toFixed(0)}px)`);
            dropTime = closestClip.startAt;
          } else {
            console.log('No valid target clip found');
          }
        } else {
          console.log('Using exact mouse position for Track 2');
        }
        console.log('Final drop time:', dropTime);
      }

      if (dragData.isExistingClip) {
        // Verify clip exists before trying to move it
        const clipExists = clips.some((c: any) => c.id === dragData.id);
        if (!clipExists) {
          console.error('Clip not found in store:', dragData.id);
          return;
        }

        // Different drag behavior for main video track vs other tracks
        const clipToMove = clips.find((c: any) => c.id === dragData.id);
        const originalTrackId = clipToMove?.trackId;

        console.log('🎯 DRAG ROUTING DEBUG:');
        console.log('   Clip to move:', clipToMove?.name, 'type:', clipToMove?.type);
        console.log('   Original track:', originalTrackId);
        console.log('   Target track:', trackId);

        // Prevent mixing video and audio clips
        const isVideoClip = clipToMove?.type === 'video';
        const isAudioClip = clipToMove?.type === 'audio';
        const isVideoTrack = trackId === 'v1' || trackId === 'v2';
        const isAudioTrack = trackId === 'a1' || trackId === 'a2';

        if (isVideoClip && isAudioTrack) {
          console.log('❌ CANNOT DROP: Video clips cannot be placed on audio tracks');
          return;
        }

        if (isAudioClip && isVideoTrack) {
          console.log('❌ CANNOT DROP: Audio clips cannot be placed on video tracks');
          return;
        }

        if (trackId === 'v1') {
          // Moving TO main video track: Always use queue reordering
          console.log('✅ Using queue reordering for main video track (TO V1)');
          reorderClipsWithSpace(dragData.id, trackId, dropTime);
        } else if (originalTrackId === 'v1') {
          // Moving FROM main video track to other track: Remove from V1 with gap closing, add to target with free positioning
          console.log('✅ Moving from V1 to other track - gap closing + free positioning');
          reorderClipsFromV1ToOther(dragData.id, trackId, dropTime);
        } else {
          // Moving between non-main tracks (V2, A1, A2): Precise positioning with overlap prevention
          console.log('✅ Using precise positioning for non-main track (V2/A1/A2)');
          reorderClipsWithOverlapPreventionPrecise(dragData.id, trackId, dropTime);
        }
      } else {
        // Add new clip from asset browser
        // Prevent mixing video and audio clips
        const isVideoClip = dragData.type === 'video';
        const isAudioClip = dragData.type === 'audio';
        const isVideoTrack = trackId === 'v1' || trackId === 'v2';
        const isAudioTrack = trackId === 'a1' || trackId === 'a2';

        if (isVideoClip && isAudioTrack) {
          console.log('❌ CANNOT DROP: Video clips cannot be placed on audio tracks');
          return;
        }

        if (isAudioClip && isVideoTrack) {
          console.log('❌ CANNOT DROP: Audio clips cannot be placed on video tracks');
          return;
        }

        const newClip: Clip = {
          id: `clip-${Date.now()}`, // Use timestamp for unique ID
          trackId: trackId,
          type: dragData.type,
          name: dragData.name,
          url: dragData.url,
          startAt: dropTime,
          duration: dragData.duration || 5,
          sourceStart: 0,
          sourceDuration: dragData.duration || 5
        };

        console.log('✅ Adding new clip to', trackId, ':', newClip.name);
        addClip(newClip);
        reorderClipsWithSpace(newClip.id, trackId, dropTime);
      }
    }
  };

  // Professional drag and drop - proper queue reordering
  const reorderClipsWithSpace = (clipId: string, targetTrackId: string, dropTime: number) => {
    const clipToMove = clips.find((c: any) => c.id === clipId);
    if (!clipToMove) {
      console.error('Clip to move not found:', clipId);
      return;
    }

    const clipDuration = clipToMove.duration;
    const originalTrackId = clipToMove.trackId;
    const originalStartTime = clipToMove.startAt;

    console.log('=== REORDER CLIPS (QUEUE MODE) ===');
    console.log('Clip to move:', { id: clipToMove.id, name: clipToMove.name, startAt: originalStartTime, duration: clipDuration });
    console.log('Target:', { trackId: targetTrackId, dropTime });

    // For different tracks, use queue reordering logic
    if (targetTrackId !== originalTrackId) {
      console.log('Moving to different track - using queue reordering');

      // Remove clip from original track and insert into target track at proper queue position
      const originalTrackClips = clips.filter((c: any) => c.trackId === originalTrackId).sort((a: any, b: any) => a.startAt - b.startAt);
      const targetTrackClips = clips.filter((c: any) => c.trackId === targetTrackId && c.id !== clipId).sort((a: any, b: any) => a.startAt - b.startAt);

      console.log('Original track clips:', originalTrackClips.map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt })));
      console.log('Target track clips:', targetTrackClips.map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt })));

      // Find insertion position in target track based on drop time
      let insertIndex = targetTrackClips.length;
      for (let i = 0; i < targetTrackClips.length; i++) {
        if (dropTime < targetTrackClips[i].startAt) {
          insertIndex = i;
          break;
        }
      }

      console.log('Insert index:', insertIndex);

      // Remove clip from original track (for gap closing)
      let clipsWithoutMoved = clips.filter((c: any) => c.id !== clipId);

      // Close gaps on original track if it's V1
      if (originalTrackId === 'v1') {
        clipsWithoutMoved = closeGapsOnV1Track(clipsWithoutMoved);
      }

      // Insert clip at target track position
      let newStartTime = insertIndex === 0 ? 0 : targetTrackClips[insertIndex - 1]?.startAt + targetTrackClips[insertIndex - 1]?.duration || 0;
      newStartTime = Math.round(newStartTime * 2) / 2; // Snap to grid

      console.log('New start time on target track:', newStartTime);

      // Create the moved clip with new position
      const movedClip = { ...clipToMove, trackId: targetTrackId, startAt: newStartTime };
      console.log('Moved clip:', { id: movedClip.id, name: movedClip.name, trackId: movedClip.trackId, startAt: movedClip.startAt });

      // Add the moved clip to the array
      const finalClips = [...clipsWithoutMoved, movedClip];

      // Close gaps on V1 if target is V1
      if (targetTrackId === 'v1') {
        console.log('Closing gaps on V1 track');
        const v1ClipsAfter = finalClips.filter((c: any) => c.trackId === 'v1').sort((a: any, b: any) => a.startAt - b.startAt);
        console.log('V1 clips before final gap closing:', v1ClipsAfter.map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt })));
        const finalWithGapsClosed = closeGapsOnV1Track(finalClips);
        const v1ClipsFinal = finalWithGapsClosed.filter((c: any) => c.trackId === 'v1').sort((a: any, b: any) => a.startAt - b.startAt);
        console.log('V1 clips after final gap closing:', v1ClipsFinal.map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt })));
        console.log('✅ FINAL STATE - Track 1 clips should now be:', v1ClipsFinal.map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt })));
        console.log('✅ FINAL STATE - Track 2 clips should now be:', finalWithGapsClosed.filter((c: any) => c.trackId === 'v2').map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt })));
        setClips(finalWithGapsClosed);
      } else {
        console.log('✅ FINAL STATE - Setting clips (non-V1 target)');
        const v1ClipsFinal = finalClips.filter((c: any) => c.trackId === 'v1').sort((a: any, b: any) => a.startAt - b.startAt);
        console.log('✅ FINAL STATE - Track 1 clips should now be:', v1ClipsFinal.map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt })));
        console.log('✅ FINAL STATE - Track 2 clips should now be:', finalClips.filter((c: any) => c.trackId === 'v2').map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt })));
        setClips(finalClips);
      }

      return;
    }

    // Get clips in target track, sorted by position
    const targetTrackClips = clips
      .filter((c: any) => c.trackId === targetTrackId)
      .sort((a: any, b: any) => a.startAt - b.startAt);

    console.log('Current track clips:', targetTrackClips.map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt })));

    // Find current position of clip being moved
    const currentIndex = targetTrackClips.findIndex((c: any) => c.id === clipId);
    if (currentIndex === -1) {
      console.error('Clip not found in target track');
      return;
    }

    console.log('Current position:', currentIndex);

    // Find insertion point based on drop time
    // If dropping in first half of a clip, insert before that clip
    // If dropping in second half of a clip, insert after that clip
    let insertIndex = targetTrackClips.length; // Default to end
    for (let i = 0; i < targetTrackClips.length; i++) {
      const clipStart = targetTrackClips[i].startAt;
      const clipEnd = targetTrackClips[i].startAt + targetTrackClips[i].duration;
      const clipMiddle = clipStart + (targetTrackClips[i].duration / 2);

      if (dropTime >= clipStart && dropTime < clipMiddle) {
        // Drop in first half of clip, insert before this clip
        insertIndex = i;
        break;
      } else if (dropTime >= clipMiddle && dropTime < clipEnd) {
        // Drop in second half of clip, insert after this clip
        insertIndex = i + 1;
        break;
      } else if (dropTime >= clipEnd && i === targetTrackClips.length - 1) {
        // Drop after last clip
        insertIndex = targetTrackClips.length;
        break;
      }
    }

    console.log('Insert index:', insertIndex);

    // If dropping in same position, do nothing
    if (insertIndex === currentIndex) {
      console.log('Same position - skipping');
      return;
    }

    // Remove clip from current position and insert at new position
    const newTrackClips = [...targetTrackClips];
    newTrackClips.splice(currentIndex, 1); // Remove from current position
    newTrackClips.splice(insertIndex, 0, clipToMove); // Insert at new position

    console.log('New track order:', newTrackClips.map((c: any) => ({ id: c.id, name: c.name })));

    // Recalculate start times based on new order
    let currentTime = 0;
    const reorderedClips = newTrackClips.map((clip: any) => {
      const updatedClip = {
        ...clip,
        startAt: currentTime
      };
      currentTime += clip.duration;
      return updatedClip;
    });

    // Update all clips in the store
    const updatedClips = clips.map((clip: any) => {
      if (clip.trackId === targetTrackId) {
        const reorderedClip = reorderedClips.find((c: any) => c.id === clip.id);
        if (reorderedClip) {
          return reorderedClip;
        }
      }
      return clip;
    });

    console.log('Final clips:', updatedClips
      .filter((c: any) => c.trackId === targetTrackId)
      .map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt }))
      .sort((a: any, b: any) => a.startAt - b.startAt)
    );

    setClips(updatedClips);
  };

  // Free positioning with overlap prevention for non-main tracks
  const reorderClipsWithOverlapPrevention = (clipId: string, targetTrackId: string, dropTime: number) => {
    const clipToMove = clips.find((c: any) => c.id === clipId);
    if (!clipToMove) {
      console.error('Clip to move not found:', clipId);
      return;
    }

    const clipDuration = clipToMove.duration;
    const originalTrackId = clipToMove.trackId;
    const originalStartTime = clipToMove.startAt;

    console.log('=== FREE POSITIONING WITH OVERLAP PREVENTION ===');
    console.log('Clip to move:', { id: clipToMove.id, name: clipToMove.name, startAt: originalStartTime, duration: clipDuration });
    console.log('Target:', { trackId: targetTrackId, dropTime });

    // Skip if dropping in essentially the same position (less than 0.05s movement)
    if (targetTrackId === originalTrackId && Math.abs(dropTime - originalStartTime) < 0.05) {
      console.log('Same position - skipping');
      return;
    }

    // Get clips in target track (excluding the one being moved)
    const targetTrackClips = clips
      .filter((c: any) => c.trackId === targetTrackId && c.id !== clipId)
      .sort((a: any, b: any) => a.startAt - b.startAt);

    console.log('Target track clips:', targetTrackClips.map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt })));

    // Check if dropping would cause overlap
    const dropEnd = dropTime + clipDuration;
    let overlappingClip = targetTrackClips.find((c: any) => {
      const existingEnd = c.startAt + c.duration;
      return dropTime < existingEnd && dropEnd > c.startAt;
    });

    if (overlappingClip) {
      console.log('Would overlap with:', overlappingClip.name, 'at', overlappingClip.startAt);

      // Determine if we should insert before or after the overlapping clip
      const overlapCenter = overlappingClip.startAt + (overlappingClip.duration / 2);

      if (dropTime < overlapCenter) {
        // Drop on left side - insert before the overlapping clip
        console.log('Dropping on left side - inserting before overlapping clip');
        const newStartTime = Math.max(0, overlappingClip.startAt - clipDuration);
        console.log('New position:', newStartTime);

        const updatedClips = clips.map((clip: any) => {
          if (clip.id === clipId) {
            return { ...clip, trackId: targetTrackId, startAt: newStartTime };
          }
          return clip;
        });
        setClips(updatedClips);
      } else {
        // Drop on right side - insert after the overlapping clip
        console.log('Dropping on right side - inserting after overlapping clip');
        const newStartTime = overlappingClip.startAt + overlappingClip.duration;
        console.log('New position:', newStartTime);

        const updatedClips = clips.map((clip: any) => {
          if (clip.id === clipId) {
            return { ...clip, trackId: targetTrackId, startAt: newStartTime };
          }
          return clip;
        });
        setClips(updatedClips);
      }
    } else {
      // No overlap - place clip at drop time
      console.log('No overlap - placing at drop time');
      const updatedClips = clips.map((clip: any) => {
        if (clip.id === clipId) {
          return { ...clip, trackId: targetTrackId, startAt: dropTime };
        }
        return clip;
      });
      setClips(updatedClips);
    }
  };

  // Complete free positioning for Track 2 - NO overlap prevention, allows any placement
  const reorderClipsFreePosition = (clipId: string, targetTrackId: string, dropTime: number) => {
    const clipToMove = clips.find((c: any) => c.id === clipId);
    if (!clipToMove) {
      console.error('Clip to move not found:', clipId);
      return;
    }

    console.log('=== FREE POSITIONING (TRACK 2 - NO OVERLAP PREVENTION) ===');
    console.log('Clip to move:', { id: clipToMove.id, name: clipToMove.name, startAt: clipToMove.startAt });
    console.log('Target:', { trackId: targetTrackId, dropTime });

    // Simply update the clip position - NO overlap checking
    const updatedClips = clips.map((clip: any) => {
      if (clip.id === clipId) {
        return { ...clip, trackId: targetTrackId, startAt: dropTime };
      }
      return clip;
    });

    console.log('Clip positioned at:', dropTime, 'seconds');
    setClips(updatedClips);
  };

  // Precise positioning for Track 2 with overlap prevention - uses 0.1s snap
  const reorderClipsWithOverlapPreventionPrecise = (clipId: string, targetTrackId: string, dropTime: number) => {
    const clipToMove = clips.find((c: any) => c.id === clipId);
    if (!clipToMove) {
      console.error('Clip to move not found:', clipId);
      return;
    }

    console.log('=== PRECISE POSITIONING WITH OVERLAP PREVENTION (TRACK 2) ===');
    console.log('Clip to move:', { id: clipToMove.id, name: clipToMove.name, startAt: clipToMove.startAt, duration: clipToMove.duration });
    console.log('Target:', { trackId: targetTrackId, dropTime });

    // Get clips in target track (excluding the one being moved)
    const targetTrackClips = clips
      .filter((c: any) => c.trackId === targetTrackId && c.id !== clipId)
      .sort((a: any, b: any) => a.startAt - b.startAt);

    console.log('Target track clips:', targetTrackClips.map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt, duration: c.duration })));

    // Check if dropping would cause overlap
    const clipDuration = clipToMove.duration;
    const dropEnd = dropTime + clipDuration;

    // Find all clips that would overlap
    // Use <= and >= to allow clips to touch at edges without being considered overlapping
    const overlappingClips = targetTrackClips.filter((c: any) => {
      const existingEnd = c.startAt + c.duration;
      // Overlap only if ranges truly intersect, not just touching
      return dropTime < existingEnd && dropEnd > c.startAt;
    });

    // Filter out clips that are just touching at the edges
    const trulyOverlappingClips = overlappingClips.filter((c: any) => {
      const existingEnd = c.startAt + c.duration;
      // If they're exactly adjacent (dropEnd == c.startAt or dropTime == existingEnd), allow it
      const isTouching = Math.abs(dropEnd - c.startAt) < 0.01 || Math.abs(dropTime - existingEnd) < 0.01;
      if (isTouching) {
        console.log('Clip is just touching, not overlapping:', c.name);
        return false;
      }
      return true;
    });

    if (trulyOverlappingClips.length > 0) {
      console.log('Would overlap with', trulyOverlappingClips.length, 'clip(s):', trulyOverlappingClips.map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt })));

      // Find the nearest non-overlapping position
      // Try moving left first (before the earliest overlapping clip)
      const earliestOverlap = trulyOverlappingClips[0];
      const leftPosition = Math.max(0, earliestOverlap.startAt - clipDuration);

      // Try moving right (after the latest overlapping clip)
      const latestOverlap = trulyOverlappingClips[trulyOverlappingClips.length - 1];
      const rightPosition = latestOverlap.startAt + latestOverlap.duration;

      // Choose the closest position to the drop time
      const distanceToLeft = Math.abs(dropTime - leftPosition);
      const distanceToRight = Math.abs(dropTime - rightPosition);

      const adjustedTime = distanceToLeft < distanceToRight ? leftPosition : rightPosition;
      console.log('Adjusted position:', adjustedTime, 'seconds (was', dropTime, ')');

      const updatedClips = clips.map((clip: any) => {
        if (clip.id === clipId) {
          return { ...clip, trackId: targetTrackId, startAt: adjustedTime };
        }
        return clip;
      });
      setClips(updatedClips);
    } else {
      // No overlap - place clip at exact drop time
      console.log('No overlap - placing at exact drop time:', dropTime);

      const beforeUpdate = clips.find((c: any) => c.id === clipId);
      console.log('Before setClips - clip position:', beforeUpdate?.startAt);

      const updatedClips = clips.map((clip: any) => {
        if (clip.id === clipId) {
          const updated = { ...clip, trackId: targetTrackId, startAt: dropTime };
          console.log('✅ Updating clip:', { id: updated.id, oldStartAt: clip.startAt, newStartAt: updated.startAt });
          return updated;
        }
        return clip;
      });

      const afterUpdate = updatedClips.find((c: any) => c.id === clipId);
      console.log('After setClips - clip position:', afterUpdate?.startAt);

      console.log('✅ Calling setClips()');
      setClips(updatedClips);

      // Verify the state was actually updated
      setTimeout(() => {
        const currentClips = useEditorStore.getState().clips;
        const currentClip = currentClips.find((c: any) => c.id === clipId);
        console.log('⏱️ 100ms after setClips - clip position:', currentClip?.startAt, '(expected:', dropTime, ')');

        if (Math.abs((currentClip?.startAt || 0) - dropTime) > 0.01) {
          console.error('❌ STATE WAS RESET! Something overwrote our update!');
          console.error('   Expected:', dropTime);
          console.error('   Got:', currentClip?.startAt);
          console.error('   All V2 clips:', currentClips.filter((c: any) => c.trackId === 'v2').map((c: any) => ({ id: c.id, startAt: c.startAt })));
        } else {
          console.log('✅ State successfully updated and persisted!');
        }
      }, 100);
    }
  };

  // Precise positioning for Track 2 - allows overlaps, exact placement
  const reorderClipsWithPrecisePositioning = (clipId: string, targetTrackId: string, dropTime: number) => {
    const clipToMove = clips.find((c: any) => c.id === clipId);
    if (!clipToMove) {
      console.error('Clip to move not found:', clipId);
      return;
    }

    console.log('=== PRECISE POSITIONING (TRACK 2) ===');
    console.log('Clip to move:', { id: clipToMove.id, name: clipToMove.name, startAt: clipToMove.startAt });
    console.log('Target:', { trackId: targetTrackId, dropTime });

    // Simply update clip position - allow overlaps
    const updatedClips = clips.map((clip: any) => {
      if (clip.id === clipId) {
        return { ...clip, trackId: targetTrackId, startAt: dropTime };
      }
      return clip;
    });

    console.log('Clip positioned at:', dropTime, 'seconds');
    console.log('Track 2 clips after positioning:', updatedClips
      .filter((c: any) => c.trackId === targetTrackId)
      .map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt }))
      .sort((a: any, b: any) => a.startAt - b.startAt)
    );

    setClips(updatedClips);
  };

  // Helper function to close gaps on V1 track
  const closeGapsOnV1Track = (currentClips: Clip[]): Clip[] => {
    console.log('🔧 closeGapsOnV1Track called');

    const v1Clips = currentClips
      .filter((c: any) => c.trackId === 'v1')
      .sort((a: any, b: any) => a.startAt - b.startAt);

    console.log('  Found V1 clips:', v1Clips.length);
    console.log('  V1 clips:', v1Clips.map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt })));

    if (v1Clips.length === 0) {
      console.log('  No V1 clips found, returning unchanged');
      return currentClips;
    }

    // Reposition V1 clips to be contiguous
    let currentTime = 0;
    const updatedClips = currentClips.map((clip: any) => {
      if (clip.trackId === 'v1') {
        const newStartAt = currentTime;
        currentTime += clip.duration;
        console.log(`  Repositioning ${clip.name}: ${clip.startAt}s → ${newStartAt}s`);
        return { ...clip, startAt: newStartAt };
      }
      return clip;
    });

    console.log('  Gap closing complete');
    return updatedClips;
  };

  // Move clip from V1 to other track with gap closing
  const reorderClipsFromV1ToOther = (clipId: string, targetTrackId: string, dropTime: number) => {
    const clipToMove = clips.find((c: any) => c.id === clipId);
    if (!clipToMove) {
      console.error('Clip to move not found:', clipId);
      return;
    }

    console.log('=== MOVING FROM V1 TO OTHER TRACK ===');
    console.log('Clip to move:', { id: clipToMove.id, name: clipToMove.name, startAt: clipToMove.startAt });
    console.log('Target:', { trackId: targetTrackId, dropTime });

    // Remove clip from all clips
    let clipsWithoutClip = clips.filter((c: any) => c.id !== clipId);
    console.log('Clips without moved clip:', clipsWithoutClip.length);

    // Close gaps on V1
    console.log('Closing gaps on V1...');
    clipsWithoutClip = closeGapsOnV1Track(clipsWithoutClip);

    const v1ClipsAfter = clipsWithoutClip.filter((c: any) => c.trackId === 'v1').sort((a: any, b: any) => a.startAt - b.startAt);
    console.log('V1 after gap closing:', v1ClipsAfter.map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt })));

    // For Track 2, check for overlaps and adjust position if needed
    let finalPosition = dropTime;

    if (targetTrackId === 'v2') {
      // Get existing clips on Track 2 (these are already on Track 2, not including the one we're moving)
      const existingTrack2Clips = clipsWithoutClip.filter((c: any) => c.trackId === 'v2');
      console.log('Existing Track 2 clips (before adding new clip):', existingTrack2Clips.map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt, duration: c.duration })));

      const clipDuration = clipToMove.duration;
      const dropEnd = finalPosition + clipDuration;

      console.log('🔍 OVERLAP CHECK DEBUG:');
      console.log('   Drop position:', finalPosition, 'to', dropEnd);
      console.log('   Checking against', existingTrack2Clips.length, 'existing clips');

      // Check if drop position would overlap with any existing Track 2 clips
      const wouldOverlap = existingTrack2Clips.some((c: any) => {
        const existingEnd = c.startAt + c.duration;
        console.log(`   Checking ${c.name}: ${c.startAt}s to ${existingEnd}s`);
        console.log(`      Condition: ${finalPosition} < ${existingEnd} && ${dropEnd} > ${c.startAt}`);
        console.log(`      Result: ${finalPosition < existingEnd} && ${dropEnd > c.startAt} = ${finalPosition < existingEnd && dropEnd > c.startAt}`);

        // Check for true overlap (not just touching)
        const isTouching = Math.abs(dropEnd - c.startAt) < 0.01 || Math.abs(finalPosition - existingEnd) < 0.01;
        console.log(`      Touching check: |${dropEnd} - ${c.startAt}| < 0.01 = ${Math.abs(dropEnd - c.startAt) < 0.01}`);
        console.log(`                    |${finalPosition} - ${existingEnd}| < 0.01 = ${Math.abs(finalPosition - existingEnd) < 0.01}`);
        console.log(`      Is touching: ${isTouching}`);

        if (isTouching) {
          console.log(`   ✅ Clip is just touching, not overlapping: ${c.name}`);
          return false;
        }
        const overlaps = finalPosition < existingEnd && dropEnd > c.startAt;
        if (overlaps) {
          console.log(`   ❌ Would overlap with: ${c.name} at ${c.startAt}`);
        } else {
          console.log(`   ✅ No overlap with: ${c.name}`);
        }
        return overlaps;
      });

      console.log('   Final wouldOverlap result:', wouldOverlap);

      if (wouldOverlap) {
        console.log('Overlap detected - finding NEAREST valid position to drop time:', dropTime);

        // Collect all possible valid positions
        const validPositions: Array<{ position: number; label: string }> = [];

        if (existingTrack2Clips.length === 0) {
          // Track is empty - use drop position
          validPositions.push({ position: dropTime, label: 'Empty track' });
        } else {
          // Sort clips by position
          const sortedClips = [...existingTrack2Clips].sort((a, b) => a.startAt - b.startAt);

          // Option 1: Before first clip (if there's space)
          if (sortedClips[0].startAt >= clipDuration) {
            validPositions.push({ position: 0, label: 'Before first clip' });
          }

          // Option 2: After each clip (always valid as long as we're not overlapping)
          for (let i = 0; i < sortedClips.length; i++) {
            const clipEnd = sortedClips[i].startAt + sortedClips[i].duration;

            // Check if placing here would overlap with the next clip
            let wouldOverlapNext = false;
            if (i < sortedClips.length - 1) {
              const nextClip = sortedClips[i + 1];
              const newClipEnd = clipEnd + clipDuration;
              wouldOverlapNext = newClipEnd > nextClip.startAt && Math.abs(newClipEnd - nextClip.startAt) >= 0.01;
            }

            if (!wouldOverlapNext) {
              validPositions.push({ position: clipEnd, label: `After clip ${sortedClips[i].name}` });
            }
          }

          // Option 3: Gaps between clips (if they exist)
          for (let i = 0; i < sortedClips.length - 1; i++) {
            const currentEnd = sortedClips[i].startAt + sortedClips[i].duration;
            const nextStart = sortedClips[i + 1].startAt;
            const gapSize = nextStart - currentEnd;

            if (gapSize >= clipDuration) {
              // Check if this gap is different from the positions we already added
              const alreadyHasPosition = validPositions.some(p => Math.abs(p.position - currentEnd) < 0.01);
              if (!alreadyHasPosition) {
                validPositions.push({ position: currentEnd, label: `Gap between ${sortedClips[i].name} and ${sortedClips[i + 1].name}` });
              }
            }
          }
        }

        console.log('Found', validPositions.length, 'valid positions:');
        validPositions.forEach(p => {
          const distance = Math.abs(dropTime - p.position);
          console.log(`  ${p.label}: ${p.position}s (distance: ${distance}s from drop)`);
        });

        if (validPositions.length === 0) {
          console.warn('No valid positions found! Using drop position anyway.');
          finalPosition = dropTime;
        } else {
          // Find the position closest to the drop time
          let closestPosition = validPositions[0];
          let closestDistance = Math.abs(dropTime - closestPosition.position);

          for (const pos of validPositions) {
            const distance = Math.abs(dropTime - pos.position);
            if (distance < closestDistance) {
              closestDistance = distance;
              closestPosition = pos;
            }
          }

          finalPosition = closestPosition.position;
          console.log('Chose closest position:', closestPosition.label, 'at', finalPosition, '(distance:', closestDistance, 's)');
        }
      } else {
        console.log('No overlap - using drop position:', finalPosition);
      }
    }

    // Add clip to target track at calculated position
    const movedClip = { ...clipToMove, trackId: targetTrackId, startAt: finalPosition };
    console.log('Adding clip to', targetTrackId, 'at', finalPosition);
    clipsWithoutClip.push(movedClip);

    console.log('✅ FINAL STATE - Track 1 clips:', clipsWithoutClip.filter((c: any) => c.trackId === 'v1').map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt })));
    console.log('✅ FINAL STATE - Target track clips:', clipsWithoutClip.filter((c: any) => c.trackId === targetTrackId).map((c: any) => ({ id: c.id, name: c.name, startAt: c.startAt })));

    setClips(clipsWithoutClip);
  };

  const getSelectedClipData = () => {
    if (!selectedClipId) return null;
    return clips.find((c: any) => c.id === selectedClipId);
  };

  const handleExport = async () => {
    if (!projectId) {
      alert('No project ID available');
      return;
    }

    setShowExportModal(false);
    setIsExporting(true);
    setExportProgress(0);
    setExportStatus('Initializing...');

    // Calculate resolution string based on aspect ratio
    const isPortrait = aspectRatio === '9:16';
    let resString = '1280x720';
    if (selectedResolution === '480p') resString = isPortrait ? '480x854' : '854x480';
    if (selectedResolution === '720p') resString = isPortrait ? '720x1280' : '1280x720';
    if (selectedResolution === '1080p') resString = isPortrait ? '1080x1920' : '1920x1080';
    if (selectedResolution === '4k') resString = isPortrait ? '2160x3840' : '3840x2160';

    console.log('[DEBUG] Exporting with:', {
      aspectRatio,
      selectedResolution,
      resString,
      isPortrait
    });

    try {
      const timelineData = {
        version: '1.0',
        duration: duration,
        tracks: tracks,
        clips: clips,
        exportedAt: new Date().toISOString()
      };

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/editor/export/${projectId}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            timeline: timelineData,
            settings: {
              resolution: resString,
              aspect_ratio: aspectRatio,
              fps: 30,
              codec: 'libx264',
              bitrate: '5M',
              audio_bitrate: '192k'
            }
          })
        }
      );

      if (!response.ok) throw new Error('Export failed');

      const data = await response.json();
      setCurrentExportId(data.export_id);

      // Poll for progress
      pollExportProgress(data.export_id);

    } catch (error) {
      console.error('Export error:', error);
      setExportStatus('Export failed: ' + (error instanceof Error ? error.message : 'Unknown error'));
      setIsExporting(false);
    }
  };

  const pollExportProgress = async (exportId: string) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/editor/export/${projectId}/status/${exportId}`
        );

        if (!response.ok) throw new Error('Status check failed');

        const data = await response.json();

        setExportProgress(data.progress || 0);
        setExportStatus(data.message || data.status || 'Processing...');

        if (data.status === 'completed') {
          clearInterval(interval);
          setIsExporting(false);
          setExportStatus('Export complete!');
          
          // Only toast once per export
          if (lastToastedExportIdRef.current !== exportId) {
            lastToastedExportIdRef.current = exportId;
            toast.success('Video Exported Successfully!', {
              description: `File: ${data.filename || 'export.mp4'}`,
              duration: 5000,
            });
          }

          // Auto-download or show download button
          setTimeout(() => {
            window.open(
              `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/editor/export/${projectId}/download/${exportId}`,
              '_blank'
            );
          }, 1000);
        } else if (data.status === 'failed') {
          clearInterval(interval);
          setIsExporting(false);
          setExportStatus('Export failed: ' + (data.error || 'Unknown error'));
        }

      } catch (error) {
        console.error('Progress polling error:', error);
        clearInterval(interval);
        setIsExporting(false);
        setExportStatus('Export failed');
      }
    }, 1000); // Poll every 1 second as fallback (was 5s)
  };

  return (
    <DndContext
      sensors={sensors}
      onDragStart={handleDragStart}
      onDragMove={handleDragMove}
      onDragEnd={handleDragEnd}
    >
      <div className="flex flex-col h-screen bg-[#0a0a0a] text-white overflow-hidden relative font-sans">

        {/* Loading Overlay */}
        {isLoading && (
          <div className="absolute inset-0 z-50 bg-[#0a0a0a]/90 backdrop-blur-md flex flex-col items-center justify-center">
            <div className="w-16 h-16 border-4 border-teal-500 border-t-transparent rounded-full animate-spin mb-4"></div>
            <p className="text-teal-400 font-medium animate-pulse">Loading Project...</p>
          </div>
        )}

        {/* Error Overlay */}
        {error && (
          <div className="absolute inset-0 z-50 bg-[#0a0a0a]/95 flex flex-col items-center justify-center p-8 text-center">
            <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mb-4 ring-2 ring-red-500/50">
               <svg className="w-8 h-8 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
            </div>
            <h2 className="text-xl font-bold text-white mb-2">Error Loading Project</h2>
            <p className="text-slate-400 max-w-md mb-6">{error}</p>
            <button
              onClick={() => projectId && loadProject(projectId)}
              className="px-6 py-2 bg-teal-600 hover:bg-teal-500 rounded-lg transition font-medium"
            >
              Retry
            </button>
          </div>
        )}

        {/* TOP TOOLBAR */}
        <div className="h-12 bg-[#121212] border-b border-slate-800 flex items-center px-4 shrink-0">
          {/* Left: Logo and Tabs */}
          <div className="flex items-center space-x-6">
            {/* Logo */}
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-br from-teal-500 to-teal-600 rounded-lg flex items-center justify-center font-bold text-white">
                C
              </div>
              <span className="text-sm font-semibold">AI Video Factory</span>
            </div>

            {/* Tabs */}
            <div className="flex items-center space-x-1">
              {['Media', 'Stickers', 'Effects', 'Transitions', 'Captions', 'Filters', 'Adjust'].map((tab) => (
                <button
                  key={tab}
                  className={`px-3 py-2 text-xs font-medium rounded-t transition-colors ${
                    activeTab.toLowerCase() === tab.toLowerCase()
                      ? 'text-teal-400 border-b-2 border-teal-400'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                  onClick={() => setActiveTab(tab.toLowerCase() as any)}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Center: Project Name */}
          <div className="flex-1 text-center">
            <span className="text-sm font-medium">{projectId || 'Untitled Project'}</span>
          </div>

          {/* Right: Action Buttons */}
          <div className="flex items-center space-x-2">
            <button className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-xs rounded-lg transition">
              Pro
            </button>
            <button className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs rounded-lg transition">
              Share
            </button>
            <button
              className="px-4 py-1.5 bg-teal-600 hover:bg-teal-500 text-white text-xs rounded-lg transition font-medium"
              onClick={() => setShowExportModal(true)}
              disabled={isExporting}
            >
              {isExporting ? (
                <span className="flex items-center space-x-2">
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>{exportProgress.toFixed(0)}%</span>
                </span>
              ) : (
                'Export'
              )}
            </button>
          </div>
        </div>

        {/* MAIN CONTENT AREA - TOP SECTION: 3 COLUMNS */}
        <div className="flex-1 flex overflow-hidden" style={{ minHeight: '60%' }}>

          {/* LEFT SECTION - Media Browser */}
          <div className="w-80 bg-[#121212] border-r border-slate-800 flex flex-col shrink-0">
            {/* Import Header */}
            <div className="h-12 border-b border-slate-800 flex items-center justify-between px-4">
              <div className="flex items-center space-x-2">
                <span className="text-sm font-semibold">Import</span>
                <button className="text-slate-400 hover:text-teal-400">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              </div>
              <div className="flex items-center space-x-2">
                <button className="px-3 py-1 bg-teal-600 hover:bg-teal-500 text-white text-xs rounded transition">
                  Import
                </button>
                <button className="px-3 py-1 bg-slate-700 hover:bg-slate-600 text-white text-xs rounded transition">
                  Record
                </button>
              </div>
            </div>

            {/* Media Content */}
            <div className="flex-1 overflow-y-auto">
              <AssetBrowser projectId={projectId} />
            </div>
          </div>

          {/* MIDDLE SECTION - Video Player */}
          <div className="flex-1 flex flex-col bg-[#0a0a0a] overflow-hidden">
            {/* Preview Header */}
            <div className="h-12 border-b border-slate-800 flex items-center justify-between px-4">
              <div className="flex items-center space-x-2">
                <span className="text-sm font-semibold">Preview</span>
                <div className="flex items-center space-x-1 ml-4">
                  <button className="p-1 bg-slate-700 hover:bg-slate-600 rounded text-xs text-slate-300">
                    Fit
                  </button>
                  <button className="p-1 bg-slate-800 hover:bg-slate-700 rounded text-xs text-slate-400">
                    100%
                  </button>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <button className="p-1 text-slate-400 hover:text-white">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Video Preview Area */}
            <div className="flex-1 flex items-center justify-center p-6 bg-[#0a0a0a]">
              <div className="w-full max-w-4xl aspect-video bg-black rounded-lg overflow-hidden shadow-2xl relative">
                <VideoPreview />
              </div>
            </div>
          </div>

          {/* RIGHT SECTION - Properties Panel */}
          <div className="w-80 bg-[#121212] border-l border-slate-800 flex flex-col shrink-0">
            {/* Properties Header */}
            <div className="h-12 border-b border-slate-800 flex items-center px-2 space-x-1">
              {['Video', 'Speed', 'Animation', 'Adjust', 'AI'].map((tool) => (
                <button
                  key={tool}
                  className={`px-3 py-2 text-xs font-medium rounded transition-colors ${
                    activeTool.toLowerCase() === tool.toLowerCase()
                      ? 'text-teal-400 bg-teal-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                  }`}
                  onClick={() => setActiveTool(tool.toLowerCase() as any)}
                >
                  {tool}
                </button>
              ))}
            </div>

            {/* Properties Content */}
            <div className="flex-1 overflow-y-auto p-4">
              {getSelectedClipData() ? (
                <div className="space-y-6">
                  {/* Selected Clip Info */}
                  <div>
                    <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                      Selected Clip
                    </h3>
                    <div className="bg-slate-800 rounded-lg p-3">
                      <div className="text-sm font-medium text-white mb-1">
                        {getSelectedClipData()?.name}
                      </div>
                      <div className="text-xs text-slate-400">
                        Type: {getSelectedClipData()?.type} • Duration: {getSelectedClipData()?.duration?.toFixed(1) || 'N/A'}s
                      </div>
                    </div>
                  </div>

                  {activeTool === 'video' && (
                    <div className="space-y-4">
                      {/* Transform */}
                      <div>
                        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                          Transform
                        </h3>
                        <div className="space-y-3">
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-slate-300">Scale</span>
                              <span className="text-slate-500">100%</span>
                            </div>
                            <input
                              type="range"
                              min="0"
                              max="200"
                              defaultValue="100"
                              className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                            />
                          </div>
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-slate-300">Position X</span>
                              <span className="text-slate-500">0</span>
                            </div>
                            <input
                              type="range"
                              min="-100"
                              max="100"
                              defaultValue="0"
                              className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                            />
                          </div>
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-slate-300">Position Y</span>
                              <span className="text-slate-500">0</span>
                            </div>
                            <input
                              type="range"
                              min="-100"
                              max="100"
                              defaultValue="0"
                              className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {activeTool === 'speed' && (
                    <div className="space-y-4">
                      <div>
                        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                          Speed
                        </h3>
                        <div className="space-y-3">
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-slate-300">Speed</span>
                              <span className="text-slate-500">1x</span>
                            </div>
                            <input
                              type="range"
                              min="0.1"
                              max="4"
                              step="0.1"
                              defaultValue="1"
                              className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {activeTool === 'adjust' && (
                    <div className="space-y-4">
                      <div>
                        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                          Adjust
                        </h3>
                        <div className="space-y-3">
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-slate-300">Brightness</span>
                              <span className="text-slate-500">0</span>
                            </div>
                            <input
                              type="range"
                              min="-100"
                              max="100"
                              defaultValue="0"
                              className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                            />
                          </div>
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-slate-300">Contrast</span>
                              <span className="text-slate-500">0</span>
                            </div>
                            <input
                              type="range"
                              min="-100"
                              max="100"
                              defaultValue="0"
                              className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                            />
                          </div>
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-slate-300">Saturation</span>
                              <span className="text-slate-500">0</span>
                            </div>
                            <input
                              type="range"
                              min="-100"
                              max="100"
                              defaultValue="0"
                              className="w-full h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mb-4">
                    <svg className="w-8 h-8 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                    </svg>
                  </div>
                  <h3 className="text-sm font-medium text-slate-400 mb-1">No Clip Selected</h3>
                  <p className="text-xs text-slate-500">Select a clip to edit its properties</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* BOTTOM SECTION - FULL WIDTH TIMELINE */}
        <div className="h-80 bg-[#121212] border-t border-slate-800 flex flex-col shrink-0">
          <Timeline />
        </div>

        {/* EXPORT SETTINGS MODAL */}
        {showExportModal && (
          <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center">
            <div className="bg-[#121212] border border-slate-700 rounded-xl p-8 w-[400px] shadow-2xl">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white">Export Project</h2>
                <button
                  onClick={() => setShowExportModal(false)}
                  className="text-slate-400 hover:text-white transition"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-4 mb-8">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-2">
                    Resolution
                  </label>
                  <select
                    value={selectedResolution}
                    onChange={(e) => setSelectedResolution(e.target.value)}
                    className="w-full bg-[#0a0a0a] border border-slate-700 text-white text-sm rounded-lg focus:ring-teal-500 focus:border-teal-500 block p-2.5 outline-none"
                  >
                    <option value="480p">480p (SD)</option>
                    <option value="720p">720p (HD)</option>
                    <option value="1080p">1080p (FHD)</option>
                    <option value="4k">4K (UHD)</option>
                  </select>
                  <p className="text-xs text-slate-500 mt-2">
                    Output will be automatically tailored to the project's aspect ratio ({aspectRatio}).
                  </p>
                </div>
              </div>

              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setShowExportModal(false)}
                  className="px-4 py-2 text-sm text-slate-300 hover:text-white transition font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleExport()}
                  disabled={isExporting}
                  className="px-6 py-2 bg-teal-600 hover:bg-teal-500 text-white text-sm rounded-lg transition font-medium"
                >
                  Start Export
                </button>
              </div>
            </div>
          </div>
        )}

        {/* EXPORT PROGRESS MODAL */}
        {isExporting && (
          <div className="fixed inset-0 bg-black/90 backdrop-blur-sm z-50 flex items-center justify-center">
            <div className="bg-[#121212] border border-slate-700 rounded-xl p-8 w-[500px] shadow-2xl">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white">Exporting Video</h2>
                <div className="text-teal-400 text-sm font-medium">
                  {exportProgress.toFixed(0)}%
                </div>
              </div>

              <div className="mb-6">
                <div className="flex justify-between text-xs text-slate-400 mb-2">
                  <span>{exportStatus}</span>
                  <span>{exportProgress.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-4 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-teal-500 to-teal-400 h-full rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${exportProgress}%` }}
                  ></div>
                </div>
              </div>

              <div className="bg-slate-800/50 rounded-lg p-4 mb-6">
                <div className="text-xs text-slate-400 space-y-1">
                  <div className="flex justify-between">
                    <span>Status:</span>
                    <span className="text-white font-medium ml-2">{exportStatus}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Progress:</span>
                    <span className="text-white font-medium ml-2">{exportProgress.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Duration:</span>
                    <span className="text-white font-medium ml-2">{duration.toFixed(1)}s</span>
                  </div>
                </div>
              </div>

              <div className="text-xs text-slate-500 text-center">
                This may take several minutes depending on video length...
                <br />
                You'll be able to download the video automatically when complete.
              </div>
            </div>
          </div>
        )}

        {/* Removed DragOverlay to prevent ghosting issues - ghost clips are handled in Track.tsx */}
      </div>
    </DndContext>
  );
}
