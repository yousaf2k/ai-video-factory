"use client";

import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { useEditorStore, Clip } from '@/store/useEditorStore';

/**
 * MediaElement handles the synchronization and playback of a single clip.
 */
function MediaElement({
  clip,
  globalTime,
  isPlaying,
  isMuted,
  onReady,
  onError,
  isVisible = false
}: {
  clip: Clip;
  globalTime: number;
  isPlaying: boolean;
  isMuted: boolean;
  onReady: () => void;
  onError: (msg: string) => void;
  isVisible?: boolean;
}) {
  const mediaRef = useRef<HTMLVideoElement | HTMLAudioElement>(null);
  const nativeAudioRef = useRef<HTMLAudioElement | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasLoggedLoad, setHasLoggedLoad] = useState(false);
  const lastPlayCall = useRef<number>(0);

  // Create native audio elements for audio clips
  useEffect(() => {
    if (clip.type !== 'audio') return;

    // Create native audio element outside React's control
    if (!nativeAudioRef.current) {
      const audio = new Audio(clip.url);
      audio.id = `native-audio-${clip.id}`;
      audio.preload = 'auto';

      // Style it to be invisible but functional
      audio.style.cssText = `
        position: fixed !important;
        top: -9999px !important;
        left: -9999px !important;
        width: 1px !important;
        height: 1px !important;
        display: block !important;
        visibility: visible !important;
        z-index: 9999 !important;
      `;

      document.body.appendChild(audio);
      nativeAudioRef.current = audio;

      console.log('[MediaElement] Created native audio:', clip.name);

      // Set up event listeners
      audio.addEventListener('loadedmetadata', () => {
        setIsLoaded(true);
        if (!hasLoggedLoad) {
          console.log(`[MediaElement] Loaded audio: ${clip.name}`, {
            duration: audio.duration
          });
          setHasLoggedLoad(true);
        }
        onReady();
      });

      audio.addEventListener('error', (e) => {
        console.error(`[MediaElement] Audio error: ${clip.name}`, e);
        const error = (e.target as HTMLAudioElement).error;
        let msg = `Failed to load audio`;
        if (error?.code === 4) msg = `File not found`;
        onError(msg);
      });
    }

    return () => {
      if (nativeAudioRef.current) {
        nativeAudioRef.current.pause();
        nativeAudioRef.current.remove();
        nativeAudioRef.current = null;
      }
    };
  }, [clip.id, clip.type, clip.name, clip.url, hasLoggedLoad, onReady, onError]);

  // DEBUG: Log when audio element is created
  useEffect(() => {
    if ((clip.type as any) === 'audio') {
      console.log('[MediaElement] Audio element created for:', clip.name, 'URL:', clip.url);
    }
  }, [clip.id, clip.type, clip.url, clip.name]);

  // Monitor and manage native audio elements
  useEffect(() => {
    if (clip.type !== 'audio') return;

    const audio = nativeAudioRef.current;
    if (!audio) return;

    const interval = setInterval(() => {
      if (audio && !audio.paused && audio.currentTime > 0) {
        // Audio is playing successfully
      }
    }, 10000); // Check every 10 seconds

    return () => clearInterval(interval);
  }, [clip.id, clip.type, clip.name]);

  const localTime = (globalTime - clip.startAt) + clip.sourceStart;

  useEffect(() => {
    // For audio, use native audio element; for video, use React-controlled element
    if ((clip.type as any) === 'audio') {
      const audio = nativeAudioRef.current;
      if (!audio || !isLoaded) return;

      // Check if clip is currently active in timeline
      const clipStart = clip.startAt;
      const clipEnd = clip.startAt + clip.duration;
      const isClipActive = globalTime >= clipStart && globalTime <= clipEnd;

      // Only play if master is playing AND this clip is active
      const shouldPlay = isPlaying && isClipActive;

      if (shouldPlay && audio.paused) {
        // Throttle play calls
        const now = Date.now();
        if (now - lastPlayCall.current < 100) return;
        lastPlayCall.current = now;

        console.log('[MediaElement] ▶️ Playing audio:', clip.name);

        audio.play().catch(e => {
          if (e.name !== 'AbortError') {
            console.error('[MediaElement] Native audio play failed:', e);
            onError(`Autoplay Blocked: ${clip.name}`);
          }
        });
      } else if (!shouldPlay && !audio.paused) {
        audio.pause();
        lastPlayCall.current = 0;
      }

      return;
    }

    // Original video element logic
    const el = mediaRef.current;
    if (!el || !isLoaded) return;

    // Check if clip is currently active in timeline
    const clipStart = clip.startAt;
    const clipEnd = clip.startAt + clip.duration;
    const isClipActive = globalTime >= clipStart && globalTime <= clipEnd;

    // Only play if master is playing AND this clip is active
    const shouldPlay = isPlaying && isClipActive;

    if (shouldPlay) {
      // Only call play() if not already playing (prevents audio glitches)
      if (el.paused) {
        // Throttle play calls to prevent audio stuttering
        const now = Date.now();
        if ((clip.type as any) === 'audio' && now - lastPlayCall.current < 100) {
          return; // Skip if we just called play (within 100ms)
        }
        lastPlayCall.current = now;

        if ((clip.type as any) === 'audio') {
          console.log('[MediaElement] ▶️ Starting audio:', clip.name, {
            currentTime: el.currentTime.toFixed(2),
            duration: el.duration?.toFixed(2),
            clipRange: `${clipStart.toFixed(1)}s-${clipEnd.toFixed(1)}s`,
            globalTime: globalTime.toFixed(1)
          });
        }

        // Check for multiple audio elements playing
        if ((clip.type as any) === 'audio') {
          const allAudio = document.querySelectorAll('audio');
          const playingAudio = Array.from(allAudio).filter(a => !a.paused);
          if (playingAudio.length > 1) {
            console.warn('[MediaElement] ⚠️ MULTIPLE AUDIO PLAYING!', {
              count: playingAudio.length,
              clips: Array.from(playingAudio).map(a => a.src.split('/').pop())
            });
          }
        }

        el.play().catch(e => {
           if (e.name !== 'AbortError') {
              console.error(`[MediaElement] Playback failed:`, e);
              onError(`Autoplay Blocked: ${clip.name}`);
           }
        });

        // Force ensure unmuted for audio
        if ((clip.type as any) === 'audio') {
          el.muted = false;
          console.log('[MediaElement] 🔊 Forced unmuted:', clip.name, {
            elementMuted: el.muted,
            propMuted: isMuted,
            volume: el.volume
          });
        }
      }
    } else {
      if ((clip.type as any) === 'audio' && !el.paused) {
        console.log('[MediaElement] ⏸️ Pausing audio:', clip.name, {
          clipRange: `${clipStart.toFixed(1)}s-${clipEnd.toFixed(1)}s`,
          globalTime: globalTime.toFixed(1),
          reason: isClipActive ? 'master paused' : 'clip not active'
        });
      }
      el.pause();
      lastPlayCall.current = 0; // Reset when paused
    }
  }, [isPlaying, isLoaded, clip.id, clip.type, clip.name, isMuted, onError, globalTime, clip.startAt, clip.duration]);

  useEffect(() => {
    const el = mediaRef.current;
    if (!el || !isLoaded) return;

    // For audio, don't sync at all - let it play smoothly
    if ((clip.type as any) === 'audio') {
      return; // Audio plays naturally without forced sync
    }

    // For video, use the original tighter sync
    const drift = Math.abs(el.currentTime - localTime);
    if (drift > 0.2) {
      el.currentTime = localTime;
    }
  }, [globalTime, isLoaded, localTime, clip.type]);

  const handleLoaded = (e: any) => {
    setIsLoaded(true);
    if (mediaRef.current) {
        mediaRef.current.currentTime = localTime;
        // Ensure volume is at max
        mediaRef.current.volume = 1.0;

        // Only log once per clip
        if (!hasLoggedLoad) {
          const duration = e.target.duration;
          console.log(`[MediaElement] Loaded ${clip.type}: ${clip.name}`, {
            duration: duration ? `${duration.toFixed(1)}s` : 'unknown',
            url: clip.url,
            isMuted: isMuted,
            volume: mediaRef.current.volume
          });
          setHasLoggedLoad(true);
        }
    }
    onReady();
  };

  const handleError = (e: any) => {
    const error = e.target.error;
    console.error(`[MediaElement] Error loading ${clip.type}: ${clip.name}`, {
      error: error,
      code: error?.code,
      message: error?.message,
      url: clip.url
    });
    let msg = `Failed to load ${clip.type}`;
    if (error?.code === 4) msg = `File not found: ${clip.name}`;
    onError(msg);
  };

  if (clip.type === 'video') {
    return (
      <video
        ref={mediaRef as React.RefObject<HTMLVideoElement>}
        src={clip.url}
        key={clip.id}
        className={`absolute inset-0 w-full h-full object-contain transition-opacity duration-300 ${isVisible ? 'opacity-100 z-10' : 'opacity-0 z-0'}`}
        muted={isMuted}
        playsInline
        onLoadedMetadata={handleLoaded}
        onCanPlay={handleLoaded}
        onError={handleError}
      />
    );
  }

  // For audio, we use native elements created in useEffect
  // Don't render a React-controlled audio element
  if ((clip.type as any) === 'audio') {
    return null;
  }

  return (
    <audio
      ref={mediaRef as React.RefObject<HTMLAudioElement>}
      src={clip.url}
      key={clip.id}
      style={{
        position: 'absolute' as any,
        top: '-9999px',
        left: '-9999px',
        width: '1px',
        height: '1px',
        display: 'block',
        opacity: '1'
      } as any}
      muted={isMuted}
      onLoadedMetadata={handleLoaded}
      onCanPlay={handleLoaded}
      onError={handleError}
    />
  );
}

export function VideoPreview() {
  const currentTime = useEditorStore((state: any) => state.currentTime);
  const clips = useEditorStore((state: any) => state.clips);
  const duration = useEditorStore((state: any) => state.duration);
  const isPlaying = useEditorStore((state: any) => state.isPlaying);
  const setIsPlaying = useEditorStore((state: any) => state.setIsPlaying);
  const setCurrentTime = useEditorStore((state: any) => state.setCurrentTime);

  const [isMuted, setIsMuted] = useState(false);
  const [loadCount, setLoadCount] = useState(0);
  const [errors, setErrors] = useState<string[]>([]);
  const [isEditingTime, setIsEditingTime] = useState(false);
  const [timeInput, setTimeInput] = useState('');
  const [showControls, setShowControls] = useState(false);

  // STABLE callbacks to prevent remounting
  const handleReady = useCallback(() => {
    setLoadCount(prev => prev + 1);
  }, []);

  const handleError = useCallback((msg: string) => {
    setErrors(prev => [...prev, msg]);
  }, []);

  const activeClips = useMemo(() => {
    return clips.filter((c: any) =>
      currentTime >= c.startAt && currentTime <= (c.startAt + c.duration)
    );
  }, [clips, currentTime]);

  const topVideoClip = useMemo(() => {
    const videos = activeClips.filter((c: any) => c.type === 'video');
    if (videos.length === 0) return null;
    return [...videos].sort((a, b) => {
      const priority: Record<string, number> = { 'v2': 2, 'v1': 1 };
      return (priority[b.trackId] || 0) - (priority[a.trackId] || 0);
    })[0];
  }, [activeClips]);

  const formatTime = (timeInSeconds: number) => {
    const mins = Math.floor(timeInSeconds / 60);
    const secs = Math.floor(timeInSeconds % 60);
    const frames = Math.floor((timeInSeconds % 1) * 30);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')};${frames.toString().padStart(2, '0')}`;
  };

  const parseTimeCode = (input: string) => {
    const parts = input.replace(';', ':').split(':');
    if (parts.length === 1) return parseFloat(parts[0]);
    if (parts.length === 2) return parseInt(parts[0]) * 60 + parseFloat(parts[1]);
    if (parts.length >= 3) return parseInt(parts[0]) * 60 + parseInt(parts[1]) + parseFloat(parts[2]) / 30;
    return 0;
  };

  const handleTimeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let newTime = parseTimeCode(timeInput);
    if (!isNaN(newTime)) {
      newTime = Math.max(0, Math.min(newTime, duration));
      setCurrentTime(newTime);
    }
    setIsEditingTime(false);
  };

  const skip = (seconds: number) => {
    setCurrentTime(Math.max(0, Math.min(currentTime + seconds, duration)));
  };

  return (
    <div 
      className="relative w-full aspect-video bg-slate-900 flex items-center justify-center border border-slate-800 rounded-lg overflow-hidden shadow-2xl group ring-1 ring-slate-800 hover:ring-indigo-500/30"
      onMouseEnter={() => setShowControls(true)}
      onMouseLeave={() => setShowControls(false)}
    >
      {/* Background/Shadow Overlays */}
      <div className={`absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/30 pointer-events-none transition-opacity duration-500 z-10 ${showControls ? 'opacity-100' : 'opacity-0'}`}></div>
      
      {/* Top Overlays */}
      <div className={`absolute top-4 left-4 right-4 flex justify-between items-start z-30 transition-all duration-300 ${showControls || !isPlaying ? 'translate-y-0 opacity-100' : '-translate-y-4 opacity-0'}`}>
        <div className="flex flex-col gap-2">
            {isEditingTime ? (
              <form onSubmit={handleTimeSubmit}>
                <input
                  autoFocus
                  className="bg-black/80 text-white font-mono px-3 py-1 rounded text-sm border border-indigo-500 outline-none w-24"
                  value={timeInput}
                  onChange={(e) => setTimeInput(e.target.value)}
                  onBlur={() => setIsEditingTime(false)}
                  placeholder="0:00"
                />
              </form>
            ) : (
              <div 
                className="text-white font-mono bg-black/60 px-3 py-1.5 rounded-md text-sm border border-slate-700/50 backdrop-blur-md shadow-lg cursor-pointer hover:bg-black/90 hover:border-indigo-500 transition-colors"
                onClick={() => { setTimeInput(formatTime(currentTime).split(';')[0]); setIsEditingTime(true); }}
              >
                {formatTime(currentTime)}
              </div>
            )}
            
            {topVideoClip && (
              <div className="text-[10px] bg-indigo-600/90 text-white px-2 py-1.5 rounded-md border border-indigo-400/50 backdrop-blur-md shadow-lg flex items-center gap-2 uppercase tracking-widest font-bold">
                <div className="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></div>
                {topVideoClip.name}
              </div>
            )}
        </div>

        <button 
           onClick={() => setIsMuted(!isMuted)}
           className={`p-2.5 rounded-full backdrop-blur-md border border-white/10 transition shadow-lg ${isMuted ? 'bg-red-500/80 hover:bg-red-600 ring-4 ring-red-500/20' : 'bg-slate-800/80 hover:bg-slate-700'}`}
        >
           {isMuted ? (
             <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" /></svg>
           ) : (
             <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" /></svg>
           )}
        </button>
      </div>

      {/* Muted Notification */}
      {isMuted && isPlaying && (
        <div className="absolute top-20 right-4 z-40 animate-bounce">
            <div className="bg-indigo-600 text-white text-[10px] font-bold px-3 py-1.5 rounded-full shadow-xl border border-indigo-400 flex items-center gap-2">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" /></svg>
                CLICK UNMUTE FOR SOUND
            </div>
        </div>
      )}

      {/* Error Overlays */}
      {errors.length > 0 && (
        <div className="absolute inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-8 pointer-events-none">
            <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 max-w-sm w-full text-center shadow-2xl">
                <svg className="w-8 h-8 text-red-500 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                <div className="text-red-400 font-bold mb-1">Playback Error</div>
                <div className="text-red-300/70 text-xs">{errors[0]}</div>
                <button 
                  className="mt-4 px-4 py-1.5 bg-red-600 hover:bg-red-500 text-white text-xs rounded-md pointer-events-auto transition-colors"
                  onClick={() => setErrors([])}
                >
                  Dismiss
                </button>
            </div>
        </div>
      )}

      {/* Bottom Control Bar */}
      <div className={`absolute bottom-6 left-1/2 -translate-x-1/2 z-30 flex items-center gap-4 transition-all duration-300 ${showControls || !isPlaying ? 'translate-y-0 opacity-100' : 'translate-y-8 opacity-0'}`}>
        <div className="flex items-center gap-1 bg-black/50 backdrop-blur-xl border border-white/10 p-1.5 rounded-2xl shadow-2xl">
            <button onClick={() => setCurrentTime(0)} className="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-xl transition-colors">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M6 6h2v12H6zm3.5 6l8.5 6V6z"/></svg>
            </button>
            <button onClick={() => skip(-5)} className="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-xl transition-colors">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z"/></svg>
            </button>
            <button
                onClick={() => setIsPlaying(!isPlaying)}
                className="w-12 h-12 flex items-center justify-center bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl shadow-lg shadow-indigo-500/20 transition-all transform active:scale-95"
            >
                {isPlaying ? (
                    <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                ) : (
                    <svg className="w-6 h-6 ml-1" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                )}
            </button>
            <button onClick={() => skip(5)} className="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-xl transition-colors">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M4 18l8.5-6L4 6v12zm9-12v12l8.5-6L13 6z"/></svg>
            </button>
            <button onClick={() => setCurrentTime(duration)} className="p-2 text-slate-400 hover:text-white hover:bg-white/10 rounded-xl transition-colors">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M6 18l8.5-6L6 6v12zM16 6h2v12h-2z"/></svg>
            </button>
        </div>
      </div>

      {/* Actual Media Container */}
      <div className="absolute inset-0 flex items-center justify-center bg-black">
        {activeClips.map((clip: any) => (
          <MediaElement
            key={clip.id}
            clip={clip}
            globalTime={currentTime}
            isPlaying={isPlaying}
            isMuted={isMuted}
            onReady={handleReady}
            onError={handleError}
            isVisible={topVideoClip?.id === clip.id}
          />
        ))}

        {activeClips.length === 0 && (
          <div className="flex flex-col items-center opacity-40">
            <svg className="w-16 h-16 mb-4 text-slate-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14v-4z" />
              <path d="M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <span className="text-sm font-semibold tracking-wider uppercase text-slate-500">Timeline Empty</span>
          </div>
        )}
      </div>

      <PlayheadSimulator />
    </div>
  );
}

function PlayheadSimulator() {
  const isPlaying = useEditorStore((state: any) => state.isPlaying);
  const setCurrentTime = useEditorStore((state: any) => state.setCurrentTime);
  const duration = useEditorStore((state: any) => state.duration);
  const setIsPlaying = useEditorStore((state: any) => state.setIsPlaying);

  useEffect(() => {
    let animationFrameId: number;
    let lastTime = performance.now();

    const loop = (time: number) => {
      const deltaSeconds = (time - lastTime) / 1000;
      lastTime = time;

      setCurrentTime((prev: any) => {
        const nextTime = prev + deltaSeconds;
        if (nextTime >= duration) {
          setIsPlaying(false);
          return duration;
        }
        return nextTime;
      });

      if (isPlaying) animationFrameId = requestAnimationFrame(loop);
    };

    if (isPlaying) {
      lastTime = performance.now();
      animationFrameId = requestAnimationFrame(loop);
    }

    return () => cancelAnimationFrame(animationFrameId);
  }, [isPlaying, duration, setCurrentTime, setIsPlaying]);

  return null;
}


