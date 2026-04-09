"use client";

import React, { useRef, useEffect, useState } from 'react';
import { useEditorStore } from '@/store/useEditorStore';
import { TrackView } from './Track';

export function Timeline() {
  const tracks = useEditorStore((state: any) => state.tracks);
  const clips = useEditorStore((state: any) => state.clips);
  const currentTime = useEditorStore((state: any) => state.currentTime);
  const duration = useEditorStore((state: any) => state.duration);
  const zoom = useEditorStore((state: any) => state.zoom);
  const setCurrentTime = useEditorStore((state: any) => state.setCurrentTime);
  const setIsPlaying = useEditorStore((state: any) => state.setIsPlaying);
  const exportTimeline = useEditorStore((state: any) => state.exportTimeline);
  const importTimeline = useEditorStore((state: any) => state.importTimeline);
  const selectedClipId = useEditorStore((state: any) => state.selectedClipId);
  const splitClip = useEditorStore((state: any) => state.splitClip);
  const dragMode = useEditorStore((state: any) => state.dragMode);
  const setDragMode = useEditorStore((state: any) => state.setDragMode);

  const timelineRef = useRef<HTMLDivElement>(null);
  const [isDraggingPlayhead, setIsDraggingPlayhead] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [showLoadDialog, setShowLoadDialog] = useState(false);
  const [savedTimelines, setSavedTimelines] = useState<any[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Get projectId from URL or props
  const [projectId, setProjectId] = useState<string | null>(null);

  // Check if playhead is within the selected clip
  const canSplitSelectedClip = () => {
    if (!selectedClipId) return false;
    const selectedClip = clips.find((c: any) => c.id === selectedClipId);
    if (!selectedClip) return false;

    // Check if playhead is within clip bounds
    return currentTime > selectedClip.startAt && currentTime < selectedClip.startAt + selectedClip.duration;
  };

  // Get status message for the user
  const getEditorStatus = () => {
    if (!selectedClipId) {
      return 'Select a clip to edit';
    }
    const selectedClip = clips.find((c: any) => c.id === selectedClipId);
    if (!selectedClip) {
      return 'No clip selected';
    }
    if (canSplitSelectedClip()) {
      return `Ready to split "${selectedClip.name}" at ${currentTime.toFixed(2)}s`;
    }
    return `Move playhead inside "${selectedClip.name}" to split`;
  };

  const handleSplitSelectedClip = () => {
    if (!selectedClipId || !canSplitSelectedClip()) {
      alert('Please select a clip and position the playhead within it to split');
      return;
    }
    splitClip(selectedClipId, currentTime);
  };

  const handleDeleteSelectedClip = () => {
    if (!selectedClipId) {
      alert('Please select a clip to delete');
      return;
    }
    if (confirm('Delete this clip?')) {
      useEditorStore.getState().deleteClip(selectedClipId);
    }
  };

  useEffect(() => {
    // Extract project ID from URL
    const pathParts = window.location.pathname.split('/');
    const projectIndex = pathParts.indexOf('projects');
    if (projectIndex !== -1 && pathParts[projectIndex + 1]) {
      const extractedProjectId = pathParts[projectIndex + 1];
      setProjectId(extractedProjectId);
      console.log('Editor loaded for project:', extractedProjectId);
      console.log('Current URL:', window.location.pathname);
    } else {
      console.warn('No project ID found in URL:', window.location.pathname);
    }
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Split shortcut: S key
      if (e.key === 's' || e.key === 'S') {
        e.preventDefault();
        handleSplitSelectedClip();
      }
      // Delete shortcut: Delete or Backspace key
      if (e.key === 'Delete' || e.key === 'Backspace') {
        e.preventDefault();
        handleDeleteSelectedClip();
      }
      // Deselect shortcut: Escape key
      if (e.key === 'Escape') {
        useEditorStore.getState().setSelectedClipId(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedClipId, currentTime, clips]);

  // Playhead drag handlers
  const handlePlayheadMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDraggingPlayhead(true);

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!timelineRef.current) return;

      const timelineRect = timelineRef.current.getBoundingClientRect();
      const scrollContainer = timelineRef.current.querySelector('.timeline-content-area') as HTMLElement;
      const scrollLeft = scrollContainer?.scrollLeft || 0;

      const mouseX = moveEvent.clientX;
      const relativeX = mouseX - timelineRect.left + scrollLeft;
      let newTime = relativeX / zoom;

      // Clamp to valid range
      newTime = Math.max(0, Math.min(newTime, duration));

      setCurrentTime(newTime);
    };

    const handleMouseUp = () => {
      setIsDraggingPlayhead(false);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  const handleSaveTimeline = async () => {
    if (!projectId) {
      alert('No project ID available - cannot save timeline');
      return;
    }

    setIsSaving(true);
    try {
      const timelineData = exportTimeline();
      console.log('Saving timeline:', timelineData);

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/editor/timeline/${projectId}/save`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(timelineData)
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Save failed');
      }

      const result = await response.json();
      console.log('Save result:', result);

      setShowSaveDialog(false);
      alert('Timeline saved successfully!');
    } catch (error) {
      console.error('Save error:', error);
      alert(`Save failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleLoadTimeline = async (filename: string) => {
    if (!projectId) {
      alert('No project ID available - cannot load timeline');
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/projects/${projectId}/editor/${filename}`
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Load failed');
      }

      const timelineData = await response.json();
      console.log('Loading timeline:', timelineData);
      importTimeline(timelineData);

      setShowLoadDialog(false);
      alert('Timeline loaded successfully!');
    } catch (error) {
      console.error('Load error:', error);
      alert(`Load failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleListTimelines = async () => {
    if (!projectId) {
      alert('No project ID available - cannot list timelines');
      return;
    }

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/editor/timeline/${projectId}/list`
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to list timelines');
      }

      const data = await response.json();
      setSavedTimelines(data.timelines || []);
      setShowLoadDialog(true);
    } catch (error) {
      console.error('List timelines error:', error);
      alert(`Failed to list timelines: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  // Handle clicking on the ruler or timeline to seek
  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!timelineRef.current) return;
    const rect = timelineRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left + timelineRef.current.scrollLeft;

    // x = time * zoom
    // time = x / zoom
    let newTime = x / zoom;
    if (newTime < 0) newTime = 0;
    if (newTime > duration) newTime = duration;

    setCurrentTime(newTime);
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-slate-900 select-none">
      {/* Editing Tools Toolbar */}
      <div className="h-16 bg-slate-950 border-b border-slate-800 flex flex-col justify-center px-4 space-y-2">
        {/* Top Row: Main Tools */}
        <div className="flex items-center justify-between">
          {/* Section 1: Editing Tools */}
          <div className="flex items-center space-x-2">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-2">
              Tools
            </div>
            <div className="w-px h-6 bg-slate-700"></div>

          <button
            className={`px-3 py-2 text-white text-xs rounded-lg transition-colors flex items-center space-x-2 ${
              canSplitSelectedClip()
                ? 'bg-amber-600 hover:bg-amber-500'
                : 'bg-slate-700 hover:bg-slate-600 cursor-not-allowed opacity-50'
            }`}
            onClick={handleSplitSelectedClip}
            disabled={!canSplitSelectedClip()}
            title="Split selected clip at playhead (S)"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path d="M14.121 14.121L19 19m-7-7l7-7m-7 7l-2.879 2.879M12 12L9.121 9.121m0 5.758a3 3 0 10-4.243 4.243 3 3 0 004.243-4.243zm0-5.758a3 3 0 10-4.243-4.243 3 3 0 004.243 4.243z"/>
            </svg>
            <span>Split</span>
          </button>

          <button
            className={`px-3 py-2 text-white text-xs rounded-lg transition-colors flex items-center space-x-2 ${
              selectedClipId
                ? 'bg-red-600 hover:bg-red-500'
                : 'bg-slate-700 hover:bg-slate-600 cursor-not-allowed opacity-50'
            }`}
            onClick={handleDeleteSelectedClip}
            disabled={!selectedClipId}
            title="Delete selected clip (Delete)"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
            <span>Delete</span>
          </button>
        </div>

        {/* Section 2: Timeline Actions */}
        <div className="flex items-center space-x-2">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-2">
            Timeline
          </div>
          <div className="w-px h-6 bg-slate-700"></div>

          <button
            className="px-3 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs rounded-lg transition-colors"
            onClick={() => setShowSaveDialog(true)}
            title="Save timeline"
          >
            💾 Save
          </button>
          <button
            className="px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-lg transition-colors"
            onClick={handleListTimelines}
            title="Load timeline"
          >
            📂 Load
          </button>
          <button
            className="px-3 py-2 bg-slate-700 hover:bg-slate-600 text-white text-xs rounded-lg transition-colors"
            onClick={() => {
              if (confirm('Are you sure you want to reset the timeline? This will remove all clips.')) {
                useEditorStore.getState().clear();
                useEditorStore.getState().setDuration(60);
              }
            }}
            title="Reset timeline"
          >
            🔄 Reset
          </button>
        </div>

        {/* Section 3: Drag Mode - Professional NLE Behavior */}
        <div className="flex items-center space-x-2">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-2">
            Drag Mode
          </div>
          <div className="w-px h-6 bg-slate-700"></div>

          <div className="flex items-center space-x-1 bg-slate-800 rounded-lg p-1">
            <button
              className={`px-3 py-1.5 text-xs rounded transition-colors ${
                dragMode === 'ripple'
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
              onClick={() => setDragMode('ripple')}
              title="Ripple Edit: Shifts subsequent clips to make space"
            >
              Ripple
            </button>
            <button
              className={`px-3 py-1.5 text-xs rounded transition-colors ${
                dragMode === 'overwrite'
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
              onClick={() => setDragMode('overwrite')}
              title="Overwrite: Replaces existing clips at drop position"
            >
              Overwrite
            </button>
            <button
              className={`px-3 py-1.5 text-xs rounded transition-colors ${
                dragMode === 'insert'
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
              onClick={() => setDragMode('insert')}
              title="Insert: Creates space for new clip without shifting"
            >
              Insert
            </button>
            <button
              className={`px-3 py-1.5 text-xs rounded transition-colors ${
                dragMode === 'replace'
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
              onClick={() => setDragMode('replace')}
              title="Replace: Swaps clip positions"
            >
              Replace
            </button>
          </div>
        </div>

        {/* Section 3: Time Display */}
        <div className="ml-auto flex items-center space-x-4">
          <div className="text-sm font-mono text-slate-300 bg-slate-800 px-3 py-2 rounded-lg">
            {currentTime.toFixed(2)}s / {duration}s
          </div>

          {/* Zoom Controls */}
          <div className="flex items-center space-x-2">
            <div className="w-px h-6 bg-slate-700"></div>
            <button
              className="text-slate-400 hover:text-white p-1"
              onClick={() => useEditorStore.getState().setZoom(Math.max(2, zoom - 5))}
              title="Zoom out"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7"/>
              </svg>
            </button>
            <input
              type="range"
              min="2"
              max="100"
              value={zoom}
              onChange={(e) => useEditorStore.getState().setZoom(Number(e.target.value))}
              className="w-24 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer"
              title="Zoom level"
            />
            <button
              className="text-slate-400 hover:text-white p-1"
              onClick={() => useEditorStore.getState().setZoom(Math.min(100, zoom + 5))}
              title="Zoom in"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7"/>
              </svg>
            </button>
          </div>
        </div>
        </div>  {/* Close top row container */}

        {/* Bottom Row: Help Text */}
        <div className="flex items-center justify-between text-xs">
          <div className="text-slate-500">
            {getEditorStatus()}
          </div>
          <div className="text-slate-600">
            Shortcuts: <span className="text-slate-400">S</span> to split •
            <span className="text-slate-400"> Delete</span> to remove •
            <span className="text-slate-400"> Click</span> clips to select •
            <span className="text-slate-400"> Drag</span> playhead to seek
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Track Headers (Left sidebar of timeline) */}
        <div className="w-48 bg-slate-950 border-r border-slate-800 flex flex-col overflow-hidden shrink-0 z-10">
          <div className="h-8 border-b border-slate-800"></div> {/* Ruler spacer */}
          <div className="flex-1 overflow-y-auto hidden-scrollbar">
            {tracks.map((track: any) => {
              const isVideoTrack = track.type === 'video';
              return (
                <div key={track.id} className="h-12 border-b border-slate-800 flex items-center px-4 font-medium text-xs text-slate-300 gap-2">
                  {isVideoTrack ? (
                    // Video icon
                    <svg className="w-4 h-4 text-indigo-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  ) : (
                    // Audio/Music icon
                    <svg className="w-4 h-4 text-emerald-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                    </svg>
                  )}
                  <span>{track.name}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Tracks Content Area */}
        <div 
          className="flex-1 overflow-auto relative timeline-content-area" 
          ref={timelineRef}
        >
          <div 
            className="relative" 
            style={{ width: `${duration * zoom}px`, minWidth: '100%' }}
            onClick={handleTimelineClick}
          >
            {/* Time Ruler */}
            <div className="h-8 border-b border-slate-800 sticky top-0 bg-slate-900/90 z-20 backdrop-blur-sm relative">
              {(() => {
                // Calculate the actual timeline duration based on clips or default duration
                const maxClipEnd = clips.reduce((max: number, clip: any) => {
                  const clipEnd = clip.startAt + clip.duration;
                  return Math.max(max, clipEnd);
                }, 0);

                // Add 10 seconds of padding after the last clip
                const actualDuration = Math.max(duration, maxClipEnd + 10);
                const markerCount = Math.ceil(actualDuration) + 1;

                return Array.from({ length: markerCount }).map((_, i) => {
                  const markerPosition = i * zoom;
                  const isMajor = i % 5 === 0;

                  return (
                    <div
                      key={i}
                      className="absolute bottom-0 flex flex-col items-center"
                      style={{ left: `${markerPosition}px` }}
                    >
                      {isMajor && (
                        <span className="text-[10px] text-slate-500 mb-1 absolute -top-5 whitespace-nowrap">
                          {i}s
                        </span>
                      )}
                      <div className={`${isMajor ? 'h-3 w-px bg-slate-600' : 'h-1.5 w-px bg-slate-800'}`}></div>
                    </div>
                  );
                });
              })()}
            </div>

            {/* Tracks */}
            <div className="relative">
              {tracks.map((track: any) => (
                <TrackView key={track.id} track={track} />
              ))}
              
              {/* Playhead */}
              <div
                className={`absolute top-0 bottom-0 z-30 ${isDraggingPlayhead ? 'w-0.5 bg-red-400' : 'w-px bg-red-500'}`}
                style={{
                  left: `${currentTime * zoom}px`,
                  cursor: 'ew-resize'
                }}
                onMouseDown={handlePlayheadMouseDown}
                onClick={(e) => e.stopPropagation()}
              >
                <div className={`absolute -top-3 -left-2 w-0 h-0 border-l-[8px] border-r-[8px] border-t-[12px] border-l-transparent border-r-transparent ${isDraggingPlayhead ? 'border-t-red-400' : 'border-t-red-500'}`}></div>
                {/* Invisible grab area - makes it easier to grab the playhead */}
                <div className="absolute top-0 bottom-0 -left-2 w-4 cursor-ew-resize"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Save Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-6 w-96 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Save Timeline</h3>
            <p className="text-slate-400 text-sm mb-2">
              Save the current timeline layout to the project directory.
            </p>
            {projectId && (
              <p className="text-slate-500 text-xs mb-4">
                Project ID: {projectId}
              </p>
            )}
            <button
              className="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition-colors"
              onClick={handleSaveTimeline}
              disabled={isSaving}
            >
              {isSaving ? 'Saving...' : 'Save Timeline'}
            </button>
            <button
              className="w-full px-4 py-2 mt-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
              onClick={() => setShowSaveDialog(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Load Dialog */}
      {showLoadDialog && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-6 w-96 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Load Timeline</h3>
            <div className="max-h-64 overflow-y-auto space-y-2 mb-4">
              {savedTimelines.length === 0 ? (
                <p className="text-slate-500 text-sm text-center py-4">No saved timelines found</p>
              ) : (
                savedTimelines.map(timeline => (
                  <button
                    key={timeline.filename}
                    className="w-full px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-sm rounded-lg transition-colors text-left"
                    onClick={() => handleLoadTimeline(timeline.filename)}
                  >
                    {timeline.filename}
                  </button>
                ))
              )}
            </div>
            <button
              className="w-full px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
              onClick={() => setShowLoadDialog(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
