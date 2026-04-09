import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';

export type MediaType = 'video' | 'audio' | 'image' | 'text';
export type TrackType = 'video' | 'audio';
export type DragMode = 'ripple' | 'overwrite' | 'insert' | 'replace';

export interface Clip {
  id: string;
  trackId: string;
  type: MediaType;
  name: string;
  url: string; // the source media url
  startAt: number; // position on timeline in seconds
  duration: number; // length on timeline in seconds
  sourceStart: number; // offset within the source media in seconds
  sourceDuration: number; // total duration of the original media
  hidden?: boolean;
}

export interface Track {
  id: string;
  name: string;
  type: TrackType;
  order: number;
  isVisible?: boolean; // For video tracks - controls visibility in preview and export
  isMuted?: boolean; // For audio tracks - controls mute state for preview and export
}

export interface TimelineExport {
  version: string;
  duration: number;
  tracks: Track[];
  clips: Clip[];
  exportedAt: string;
}

interface EditorState {
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  zoom: number; // pixels per second
  tracks: Track[];
  clips: Clip[];
  selectedClipId: string | null;
  dragMode: DragMode; // Professional NLE drag mode
  aspectRatio: string; // Project aspect ratio (e.g., '16:9' or '9:16')

  // Actions
  setCurrentTime: (time: number | ((prev: number) => number)) => void;
  setDuration: (duration: number) => void;
  setIsPlaying: (isPlaying: boolean | ((prev: boolean) => boolean)) => void;
  setZoom: (zoom: number) => void;
  setDragMode: (mode: DragMode) => void;
  setAspectRatio: (ratio: string) => void;

  addTrack: (track: Track) => void;
  setTracks: (tracks: Track[]) => void;
  toggleTrackVisibility: (trackId: string) => void;
  toggleTrackMute: (trackId: string) => void;
  addClip: (clip: Clip) => void;
  setClips: (clips: Clip[]) => void;
  updateClip: (id: string, updates: Partial<Clip>) => void;
  deleteClip: (id: string) => void;
  setSelectedClipId: (id: string | null) => void;
  splitClip: (clipId: string, splitTime: number) => void;
  closeGapsOnMainVideoTrack: () => void;
  exportTimeline: () => TimelineExport;
  importTimeline: (timelineData: TimelineExport) => void;
  clear: () => void;
}



export const useEditorStore: any = create<EditorState>((set: any) => ({
  currentTime: 0,
  duration: 60, // Default 60 seconds timeline
  isPlaying: false,
  zoom: 10, // 10px per second default
  dragMode: 'ripple', // Default to professional ripple edit mode
  aspectRatio: '16:9', // Default to landscape

  tracks: [
    { id: 'v2', name: 'Video 2', type: 'video', order: 0, isVisible: true },
    { id: 'v1', name: 'Video 1', type: 'video', order: 1, isVisible: true },
    { id: 'a1', name: 'Narration', type: 'audio', order: 2, isMuted: false },
    { id: 'a2', name: 'BGM / SFX', type: 'audio', order: 3, isMuted: false },
  ],
  clips: [],
  selectedClipId: null,


  setCurrentTime: (time) => set((state: any) => ({
    currentTime: typeof time === 'function' ? time(state.currentTime) : time
  })),
  setDuration: (duration) => set({ duration }),
  setIsPlaying: (isPlaying) => set((state: any) => ({
    isPlaying: typeof isPlaying === 'function' ? isPlaying(state.isPlaying) : isPlaying
  })),
  setZoom: (zoom) => set({ zoom }),
  setDragMode: (mode) => set({ dragMode: mode }),
  setAspectRatio: (ratio) => set({ aspectRatio: ratio }),
  
  addTrack: (track) => set((state: any) => ({ tracks: [...state.tracks, track] })),
  setTracks: (tracks) => set({ tracks }),
  toggleTrackVisibility: (trackId) => set((state: any) => ({
    tracks: state.tracks.map((track: any) =>
      track.id === trackId ? { ...track, isVisible: track.isVisible !== undefined ? !track.isVisible : false } : track
    )
  })),
  toggleTrackMute: (trackId) => set((state: any) => ({
    tracks: state.tracks.map((track: any) =>
      track.id === trackId ? { ...track, isMuted: track.isMuted !== undefined ? !track.isMuted : true } : track
    )
  })),
  addClip: (clip) => set((state: any) => ({ clips: [...state.clips, clip] })),
  setClips: (clips) => {
    console.log('📦 setClips called with', clips.length, 'clips');
    console.log('📦 V2 clips:', clips.filter((c: any) => c.trackId === 'v2').map((c: any) => ({ id: c.id, startAt: c.startAt })));
    return set({ clips });
  },
  updateClip: (id, updates) => set((state: any) => ({
    clips: state.clips.map((clip: any) => clip.id === id ? { ...clip, ...updates } : clip)
  })),
  deleteClip: (id) => set((state: any) => {
    // Find the clip being deleted
    const clipToDelete = state.clips.find((c: any) => c.id === id);
    if (!clipToDelete) return state;

    // Delete the clip
    const clipsAfterDelete = state.clips.filter((clip: any) => clip.id !== id);

    // If deleting from main video track (v1), close the gap
    if (clipToDelete.trackId === 'v1') {
      const deleteTime = clipToDelete.startAt;
      const deleteDuration = clipToDelete.duration;

      // Shift all subsequent clips on v1 track to fill the gap
      const updatedClips = clipsAfterDelete.map((clip: any) => {
        if (clip.trackId === 'v1' && clip.startAt > deleteTime) {
          return {
            ...clip,
            startAt: clip.startAt - deleteDuration
          };
        }
        return clip;
      });

      return {
        clips: updatedClips,
        selectedClipId: null
      };
    }

    // For other tracks, just delete the clip
    return {
      clips: clipsAfterDelete,
      selectedClipId: null
    };
  }),
  setSelectedClipId: (id) => set({ selectedClipId: id }),
  splitClip: (clipId, splitTime) => set((state: any) => {
    const clipIndex = state.clips.findIndex((c: any) => c.id === clipId);
    if (clipIndex === -1) return state;

    const clip = state.clips[clipIndex];

    // Validate split time is within clip bounds
    if (splitTime <= clip.startAt || splitTime >= clip.startAt + clip.duration) {
      return state;
    }

    const splitPointRelative = splitTime - clip.startAt;

    // Create split clips with proper UUIDs
    const leftClip = {
      ...clip,
      id: uuidv4(),  // Unique ID to prevent collisions
      duration: splitPointRelative,
      sourceDuration: splitPointRelative
    };

    const rightClip = {
      ...clip,
      id: uuidv4(),  // Unique ID to prevent collisions
      startAt: splitTime,
      duration: clip.duration - splitPointRelative,
      sourceStart: clip.sourceStart + splitPointRelative,
      sourceDuration: clip.duration - splitPointRelative
    };

    // Replace original with two new clips
    const newClips = [...state.clips];
    newClips.splice(clipIndex, 1, leftClip, rightClip);

    return { clips: newClips, selectedClipId: leftClip.id };
  }),

  // Helper function to close gaps on main video track
  closeGapsOnMainVideoTrack: () => set((state: any) => {
    const v1Clips = state.clips
      .filter((c: any) => c.trackId === 'v1')
      .sort((a: any, b: any) => a.startAt - b.startAt);

    if (v1Clips.length === 0) return state;

    // Ensure clips are contiguous with no gaps
    let currentTime = 0;
    const updatedClips = state.clips.map((clip: any) => {
      if (clip.trackId === 'v1') {
        const newStartAt = currentTime;
        currentTime += clip.duration;
        return {
          ...clip,
          startAt: newStartAt
        };
      }
      return clip;
    });

    return { clips: updatedClips };
  }),

  exportTimeline: () => {
    const state = useEditorStore.getState();
    return {
      version: '1.0',
      duration: state.duration,
      tracks: state.tracks,
      clips: state.clips,
      exportedAt: new Date().toISOString()
    };
  },
  importTimeline: (timelineData) => set(() => ({
    duration: timelineData.duration,
    tracks: timelineData.tracks,
    clips: timelineData.clips,
    selectedClipId: null,
    currentTime: 0,
    isPlaying: false
  })),
  clear: () => set({
    clips: [],
    selectedClipId: null,
    currentTime: 0,
    isPlaying: false
  })
}));


