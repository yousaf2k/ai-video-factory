"use client";

import React, { useRef, useEffect, useMemo, useState } from 'react';
import { useDroppable, useDraggable, useDndContext } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { useEditorStore, Track, Clip } from '@/store/useEditorStore';

interface TrackViewProps {
  track: Track;
}

export function TrackView({ track }: TrackViewProps) {
  // Use refs to prevent unnecessary re-renders
  const clips = useEditorStore((state: any) => state.clips.filter((c: any) => c.trackId === track.id));
  const zoom = useEditorStore((state: any) => state.zoom);
  const clipsRef = useRef(clips);
  const zoomRef = useRef(zoom);

  // Update refs when values change
  useEffect(() => {
    clipsRef.current = clips;
  }, [clips]);

  useEffect(() => {
    zoomRef.current = zoom;
  }, [zoom]);

  const { setNodeRef, isOver } = useDroppable({
    id: `track-${track.id}`,
    data: { trackId: track.id }
  });

  const dndContext = useDndContext();
  const mousePosRef = useRef({ x: 0, y: 0 });

  // DISABLED: Ghost preview system was causing issues
  // The complex ghost preview was interfering with drag operations
  // Professional NLEs show simpler visual feedback during drag

  // useEffect(() => {
  //   // ... ghost preview code removed
  // }, [isOver, dndContext, track.id, setTick]);

  // Memoize clips to prevent unnecessary re-renders
  const memoizedClips = useMemo(() => clips, [clips]);

  // Simplified display logic - always show real clips
  return (
    <div
      ref={setNodeRef}
      data-track-id={track.id}
      className={`h-12 border-b border-slate-800/50 relative bg-slate-900/30 transition-colors ${
        isOver ? 'bg-slate-800/20' : ''
      }`}
    >
      {/* Subtle grid background */}
      <div className="absolute inset-0 pointer-events-none opacity-5">
        <div className="w-full h-full" style={{
          backgroundImage: 'linear-gradient(to right, #64748b 1px, transparent 1px)',
          backgroundSize: `${zoom * 5}px 100%`
        }}></div>
      </div>

      {/* Always show real clips - professional NLE behavior */}
      {memoizedClips.map((clip: any) => (
        <ClipView key={`${clip.id}-${clip.startAt}`} clip={clip} />
      ))}
    </div>
  );
}


interface ClipViewProps {
  clip: Clip;
}

function ClipView({ clip }: ClipViewProps) {
  const zoom = useEditorStore((state: any) => state.zoom);
  const updateClip = useEditorStore((state: any) => state.updateClip);
  const deleteClip = useEditorStore((state: any) => state.deleteClip);
  const selectedClipId = useEditorStore((state: any) => state.selectedClipId);
  const setSelectedClipId = useEditorStore((state: any) => state.setSelectedClipId);

  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `clip-${clip.id}`,
    data: { ...clip, isExistingClip: true }
  });

  const [isTrimming, setIsTrimming] = useState<'left' | 'right' | null>(null);
  const trimStartPos = useRef(0);
  const trimStartVal = useRef({ startAt: 0, duration: 0, sourceStart: 0 });

  const isSelected = selectedClipId === clip.id;

  const style = {
    left: `${clip.startAt * zoom}px`,
    width: `${clip.duration * zoom}px`,
    transform: transform ? CSS.Translate.toString(transform) : undefined,
    zIndex: isDragging ? 50 : isSelected ? 40 : 30,
  };

  const handleTrimStart = (side: 'left' | 'right', e: React.PointerEvent) => {
    e.stopPropagation();
    e.preventDefault();
    setIsTrimming(side);
    trimStartPos.current = e.clientX;
    trimStartVal.current = {
      startAt: clip.startAt,
      duration: clip.duration,
      sourceStart: clip.sourceStart
    };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const handleTrimMove = (e: React.PointerEvent) => {
    if (!isTrimming) return;

    const deltaX = e.clientX - trimStartPos.current;
    const deltaTime = deltaX / zoom;

    if (isTrimming === 'left') {
      const newStartAt = Math.max(0, trimStartVal.current.startAt + deltaTime);
      const newSourceStart = Math.max(0, trimStartVal.current.sourceStart + deltaTime);
      const consumedStart = newStartAt - trimStartVal.current.startAt;
      const newDuration = Math.max(0.1, trimStartVal.current.duration - consumedStart);

      updateClip(clip.id, {
        startAt: newStartAt,
        duration: newDuration,
        sourceStart: newSourceStart
      });
    } else {
      const newDuration = Math.max(0.1, trimStartVal.current.duration + deltaTime);
      updateClip(clip.id, { duration: newDuration });
    }
  };

  const handleTrimEnd = (e: React.PointerEvent) => {
    if (!isTrimming) return;
    setIsTrimming(null);
    (e.target as HTMLElement).releasePointerCapture(e.pointerId);
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={(e) => {
        e.stopPropagation();
        setSelectedClipId(clip.id);
      }}
      className={`absolute top-1 bottom-1 rounded border text-[10px] font-medium overflow-visible group shadow select-none transition-all
        ${clip.type === 'video' ? 'bg-indigo-600/80 border-indigo-400' : ''}
        ${clip.type === 'audio' ? 'bg-emerald-600/80 border-emerald-400' : ''}
        ${isSelected ? 'ring-1 ring-white border-white scale-[1.01]' : 'hover:opacity-90'}
        ${isDragging ? 'opacity-30 cursor-grabbing' : 'cursor-grab'}
      `}
    >
      {/* Clip content */}
      <div className="px-2 py-0.5 truncate text-white drop-shadow-md pointer-events-none h-full relative">
        {clip.name}

        {isSelected && (
           <button
             className="absolute -top-2 -right-2 w-5 h-5 bg-red-500 rounded flex items-center justify-center border border-slate-900 pointer-events-auto hover:bg-red-400 transition shadow"
             onClick={(e) => {
                e.stopPropagation();
                deleteClip(clip.id);
             }}
             title="Delete clip"
           >
              <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3"><path d="M6 18L18 6M6 6l12 12"/></svg>
           </button>
        )}
      </div>

      {/* Trim handles - subtle */}
      <div
        className={`absolute left-0 top-0 bottom-0 w-1.5 opacity-0 group-hover:opacity-60 cursor-ew-resize hover:bg-white/30 z-10 rounded-l pointer-events-auto transition-opacity ${
          isTrimming === 'left' ? 'opacity-100 bg-white/40' : ''
        }`}
        onPointerDown={(e) => handleTrimStart('left', e)}
        onPointerMove={handleTrimMove}
        onPointerUp={handleTrimEnd}
      ></div>

      <div
        className={`absolute right-0 top-0 bottom-0 w-1.5 opacity-0 group-hover:opacity-60 cursor-ew-resize hover:bg-white/30 z-10 rounded-r pointer-events-auto transition-opacity ${
          isTrimming === 'right' ? 'opacity-100 bg-white/40' : ''
        }`}
        onPointerDown={(e) => handleTrimStart('right', e)}
        onPointerMove={handleTrimMove}
        onPointerUp={handleTrimEnd}
      ></div>
    </div>
  );
}

