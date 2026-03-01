/**
 * ShotGrid component - Grid view of shots with thumbnails and bulk actions
 */
import { useState, useCallback, useMemo } from 'react';
import { ShotCard } from './ShotCard';
import { Shot } from '@/types';
import { useAgents } from '@/hooks/useAgents';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import { CheckSquare, Square, Image as ImageIcon, Video, X, RotateCw, Search, Filter, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useProgress } from '@/hooks/useProgress';

interface ShotGridProps {
  shots: Shot[];
  sessionId: string;
}

export function ShotGrid({ shots, sessionId }: ShotGridProps) {
  const [selectedIndices, setSelectedIndices] = useState<number[]>([]);
  const [showBatchModal, setShowBatchModal] = useState<'image' | 'video' | 'both' | null>(null);
  const [generatingIndices, setGeneratingIndices] = useState<Set<number>>(new Set());
  const { shotProgress } = useProgress(sessionId);

  // Filter state
  const [filterNoImages, setFilterNoImages] = useState(false);
  const [filterNoVideos, setFilterNoVideos] = useState(false);
  const [filterCamera, setFilterCamera] = useState<string>('');
  const [filterText, setFilterText] = useState<string>('');

  // Overrides state
  const [imageMode, setImageMode] = useState<string>('comfyui');
  const [imageWorkflow, setImageWorkflow] = useState<string>('flux2');
  const [videoWorkflow, setVideoWorkflow] = useState<string>('workflow/video/wan22_workflow.json');

  const queryClient = useQueryClient();
  const { data: agents } = useAgents();

  // Extract unique camera values for the dropdown
  const cameraOptions = useMemo(() => {
    const cameras = new Set(shots.map(s => s.camera).filter(Boolean));
    return Array.from(cameras).sort();
  }, [shots]);

  // Apply filters
  const filteredShots = useMemo(() => {
    let result = shots;

    if (filterNoImages) {
      result = result.filter(s => !s.image_generated);
    }
    if (filterNoVideos) {
      result = result.filter(s => !s.video_rendered);
    }
    if (filterCamera) {
      result = result.filter(s => s.camera === filterCamera);
    }
    if (filterText.trim()) {
      const q = filterText.trim().toLowerCase();
      result = result.filter(s => {
        return (
          (s.image_prompt || '').toLowerCase().includes(q) ||
          (s.motion_prompt || '').toLowerCase().includes(q) ||
          (s.narration || '').toLowerCase().includes(q)
        );
      });
    }

    return result;
  }, [shots, filterNoImages, filterNoVideos, filterCamera, filterText]);

  const hasActiveFilters = filterNoImages || filterNoVideos || !!filterCamera || !!filterText.trim();

  if (shots.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No shots yet. Generate story and plan shots first.
      </div>
    );
  }

  const toggleSelectAll = () => {
    if (selectedIndices.length === filteredShots.length) {
      setSelectedIndices([]);
    } else {
      setSelectedIndices(filteredShots.map(s => s.index));
    }
  };

  const toggleSelectShot = (index: number, selected: boolean) => {
    if (selected) {
      setSelectedIndices(prev => [...prev, index]);
    } else {
      setSelectedIndices(prev => prev.filter(i => i !== index));
    }
  };

  const handleBatchSubmit = useCallback(async () => {
    if (selectedIndices.length === 0 || !showBatchModal) return;

    const indicesToProcess = [...selectedIndices];
    const type = showBatchModal;

    // Close modal and clear selection immediately
    setShowBatchModal(null);
    setSelectedIndices([]);

    // Mark all selected shots as generating
    setGeneratingIndices(prev => {
      const next = new Set(prev);
      indicesToProcess.forEach(i => next.add(i));
      return next;
    });

    if (type === 'both') {
      // Sequential: first all images, then all videos
      // Phase 1: Generate images with concurrency limit (max 4)
      // This leaves 2 browser connections free for UI updates (like invalidateQueries)
      const inProgress = new Set<Promise<void>>();
      for (const shotIndex of indicesToProcess) {
        const p = (async () => {
          try {
            await api.regenerateShotImage(sessionId, shotIndex, true, imageMode, imageWorkflow);
          } catch (error) {
            console.error(`Failed to regenerate image for shot ${shotIndex}:`, error);
          } finally {
            // Invalidate and remove from generating as soon as each image finishes
            queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
            queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
            setGeneratingIndices(prev => {
              const next = new Set(prev);
              next.delete(shotIndex);
              return next;
            });
          }
        })().finally(() => inProgress.delete(p));

        inProgress.add(p);
        if (inProgress.size >= 4) {
          await Promise.race(inProgress);
        }
      }
      await Promise.all(inProgress);

      // Clear generating state and refresh to show new images
      setGeneratingIndices(new Set());
      await queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      await queryClient.invalidateQueries({ queryKey: ['session', sessionId] });

      // Phase 2: Re-mark for video generation, then start videos with concurrency limit
      setGeneratingIndices(new Set(indicesToProcess));
      const inProgressVideos = new Set<Promise<void>>();
      for (const shotIndex of indicesToProcess) {
        const p = (async () => {
          try {
            await api.regenerateShotVideo(sessionId, shotIndex, true, videoWorkflow);
          } catch (error) {
            console.error(`Failed to regenerate video for shot ${shotIndex}:`, error);
          } finally {
            setGeneratingIndices(prev => {
              const next = new Set(prev);
              next.delete(shotIndex);
              return next;
            });
            queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
            queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
          }
        })().finally(() => inProgressVideos.delete(p));

        inProgressVideos.add(p);
        if (inProgressVideos.size >= 4) {
          await Promise.race(inProgressVideos);
        }
      }
      await Promise.all(inProgressVideos);

    } else {
      // Single type: fire individual requests with concurrency limit (max 4)
      const inProgressSingle = new Set<Promise<void>>();
      for (const shotIndex of indicesToProcess) {
        const p = (async () => {
          try {
            if (type === 'image') {
              await api.regenerateShotImage(sessionId, shotIndex, true, imageMode, imageWorkflow);
            } else {
              await api.regenerateShotVideo(sessionId, shotIndex, true, videoWorkflow);
            }
          } catch (error) {
            console.error(`Failed to regenerate ${type} for shot ${shotIndex}:`, error);
          } finally {
            setGeneratingIndices(prev => {
              const next = new Set(prev);
              next.delete(shotIndex);
              return next;
            });
            queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
            queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
          }
        })().finally(() => inProgressSingle.delete(p));

        inProgressSingle.add(p);
        if (inProgressSingle.size >= 4) {
          await Promise.race(inProgressSingle);
        }
      }
      await Promise.all(inProgressSingle);
    }
  }, [selectedIndices, showBatchModal, sessionId, imageMode, imageWorkflow, videoWorkflow, queryClient]);

  const handleCancelAll = useCallback(async () => {
    try {
      await api.cancelGeneration(sessionId);
      setGeneratingIndices(new Set());
      queryClient.invalidateQueries({ queryKey: ['shots', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] });
    } catch (error) {
      console.error('Failed to cancel generation:', error);
    }
  }, [sessionId, queryClient]);

  return (
    <div className="relative">
      {/* Header Actions */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSelectedIndices(filteredShots.map(s => s.index))}
            className="flex items-center gap-1.5 text-sm px-2.5 py-1 border rounded-md hover:bg-muted transition-colors"
          >
            <CheckSquare className="w-3.5 h-3.5" />
            Select All
          </button>
          <button
            onClick={() => setSelectedIndices([])}
            disabled={selectedIndices.length === 0}
            className="flex items-center gap-1.5 text-sm px-2.5 py-1 border rounded-md hover:bg-muted transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Square className="w-3.5 h-3.5" />
            Select None
          </button>
          {selectedIndices.length > 0 && (
            <span className="text-xs text-muted-foreground ml-1">
              {selectedIndices.length} of {shots.length} selected
            </span>
          )}
        </div>
        {generatingIndices.size > 0 && (
          <button
            onClick={handleCancelAll}
            className="flex items-center gap-1.5 text-sm px-3 py-1.5 border border-red-300 text-red-600 rounded-md hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          >
            <XCircle className="w-4 h-4" />
            Cancel All Generation
          </button>
        )}
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-2 mb-4 p-3 bg-muted/40 rounded-lg border">
        <Filter className="w-4 h-4 text-muted-foreground shrink-0" />

        <button
          onClick={() => setFilterNoImages(v => !v)}
          className={cn(
            "flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-full border transition-colors",
            filterNoImages
              ? "bg-orange-100 border-orange-300 text-orange-700 dark:bg-orange-900/30 dark:border-orange-700 dark:text-orange-400"
              : "hover:bg-muted"
          )}
        >
          <ImageIcon className="w-3 h-3" />
          No Images
        </button>

        <button
          onClick={() => setFilterNoVideos(v => !v)}
          className={cn(
            "flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-full border transition-colors",
            filterNoVideos
              ? "bg-purple-100 border-purple-300 text-purple-700 dark:bg-purple-900/30 dark:border-purple-700 dark:text-purple-400"
              : "hover:bg-muted"
          )}
        >
          <Video className="w-3 h-3" />
          No Videos
        </button>

        <select
          value={filterCamera}
          onChange={(e) => setFilterCamera(e.target.value)}
          className="text-xs px-2.5 py-1.5 rounded-full border bg-background transition-colors"
        >
          <option value="">All Cameras</option>
          {cameraOptions.map(cam => (
            <option key={cam} value={cam}>{cam}</option>
          ))}
        </select>

        <div className="relative flex-1 min-w-[180px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <input
            type="text"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            placeholder="Search prompts & narration..."
            className="w-full text-xs pl-8 pr-3 py-1.5 rounded-full border bg-background"
          />
        </div>

        {hasActiveFilters && (
          <button
            onClick={() => {
              setFilterNoImages(false);
              setFilterNoVideos(false);
              setFilterCamera('');
              setFilterText('');
            }}
            className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-full border text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          >
            <X className="w-3 h-3" />
            Clear
          </button>
        )}

        <span className="text-xs text-muted-foreground ml-auto">
          {filteredShots.length} of {shots.length} shots
        </span>
      </div>

      {/* Floating Bulk Actions Bar */}
      <div className={cn(
        "fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-background border shadow-lg rounded-full px-6 py-3 flex items-center gap-4 transition-all duration-300",
        selectedIndices.length > 0 ? "translate-y-0 opacity-100" : "translate-y-16 opacity-0 pointer-events-none"
      )}>
        <span className="text-sm font-medium border-r pr-4">
          {selectedIndices.length} shots selected
        </span>
        <button
          onClick={() => setShowBatchModal('image')}
          className="flex items-center gap-2 text-sm px-3 py-1.5 hover:bg-muted rounded-md transition-colors"
        >
          <ImageIcon className="w-4 h-4 text-blue-500" />
          Regenerate Images
        </button>
        <button
          onClick={() => setShowBatchModal('video')}
          className="flex items-center gap-2 text-sm px-3 py-1.5 hover:bg-muted rounded-md transition-colors"
        >
          <Video className="w-4 h-4 text-purple-500" />
          Regenerate Videos
        </button>
        <button
          onClick={() => setShowBatchModal('both')}
          className="flex items-center gap-2 text-sm px-3 py-1.5 hover:bg-muted rounded-md transition-colors"
        >
          <RotateCw className="w-4 h-4 text-green-500" />
          Both (Images + Videos)
        </button>
        <button
          onClick={() => setSelectedIndices([])}
          className="ml-2 p-1.5 hover:bg-muted rounded-full text-muted-foreground"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredShots.map((shot) => (
          <ShotCard
            key={`${shot.index}-${shot.image_path}`}
            shot={shot}
            sessionId={sessionId}
            selectable={true}
            selected={selectedIndices.includes(shot.index)}
            onSelectChange={(selected: boolean) => toggleSelectShot(shot.index, selected)}
            isGenerating={generatingIndices.has(shot.index)}
            progress={shotProgress[shot.index]}
            onCancel={generatingIndices.has(shot.index) ? handleCancelAll : undefined}
          />
        ))}
      </div>

      {/* Batch Modal Overlay */}
      {showBatchModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-background rounded-lg shadow-xl max-w-md w-full p-6 relative">
            <button
              onClick={() => setShowBatchModal(null)}
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
            >
              <X className="w-5 h-5" />
            </button>

            <h2 className="text-xl font-semibold mb-6">
              Batch Regenerate {showBatchModal === 'image' ? 'Images' : showBatchModal === 'video' ? 'Videos' : 'Images + Videos'} ({selectedIndices.length} shots)
            </h2>

            {(showBatchModal === 'image' || showBatchModal === 'both') && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Generation Mode</label>
                  <select
                    value={imageMode}
                    onChange={(e) => setImageMode(e.target.value)}
                    className="w-full border rounded-md p-2 text-sm"
                  >
                    <option value="comfyui">ComfyUI (Local)</option>
                    <option value="gemini">Gemini (Cloud)</option>
                    <option value="geminiweb">GeminiWeb - Gemini Web (Browser)</option>
                  </select>
                </div>

                {imageMode === 'comfyui' && (
                  <div>
                    <label className="block text-sm font-medium mb-1">ComfyUI Workflow</label>
                    <select
                      value={imageWorkflow}
                      onChange={(e) => setImageWorkflow(e.target.value)}
                      className="w-full border rounded-md p-2 text-sm"
                    >
                      <option value="flux2">Flux 2 (High Quality)</option>
                      <option value="flux">Flux (Standard)</option>
                      <option value="sdxl">SDXL</option>
                      <option value="hidream">HiDream</option>
                      <option value="qwen">Qwen</option>
                      <option value="default">Default</option>
                    </select>
                  </div>
                )}
              </div>
            )}

            {(showBatchModal === 'video' || showBatchModal === 'both') && (
              <div className="space-y-4">
                {showBatchModal === 'both' && <hr className="my-3" />}
                <div>
                  <label className="block text-sm font-medium mb-1">Video Workflow</label>
                  <input
                    type="text"
                    value={videoWorkflow}
                    onChange={(e) => setVideoWorkflow(e.target.value)}
                    className="w-full border rounded-md p-2 text-sm"
                    placeholder="workflow/video/wan22_workflow.json"
                  />
                  <p className="text-xs text-muted-foreground mt-1">Path to the ComfyUI video JSON workflow.</p>
                </div>
              </div>
            )}

            <div className="mt-8 flex justify-end gap-3">
              <button
                onClick={() => setShowBatchModal(null)}
                className="px-4 py-2 border rounded-md hover:bg-muted text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleBatchSubmit}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-sm flex items-center gap-2"
              >
                Start Generation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
