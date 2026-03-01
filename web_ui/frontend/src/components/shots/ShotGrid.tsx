/**
 * ShotGrid component - Grid view of shots with thumbnails and bulk actions
 */
import { useState } from 'react';
import { ShotCard } from './ShotCard';
import { Shot } from '@/types';
import { useBatchRegenerate } from '@/hooks/useShots';
import { useAgents } from '@/hooks/useAgents';
import { CheckSquare, Square, Image as ImageIcon, Video, X, RotateCw } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ShotGridProps {
  shots: Shot[];
  sessionId: string;
}

export function ShotGrid({ shots, sessionId }: ShotGridProps) {
  const [selectedIndices, setSelectedIndices] = useState<number[]>([]);
  const [showBatchModal, setShowBatchModal] = useState<'image' | 'video' | null>(null);
  
  // Overrides state
  const [imageMode, setImageMode] = useState<string>('comfyui');
  const [imageWorkflow, setImageWorkflow] = useState<string>('flux2');
  const [videoWorkflow, setVideoWorkflow] = useState<string>('workflow/video/wan22_workflow.json');

  const batchRegenerate = useBatchRegenerate(sessionId);
  const { data: agents } = useAgents();

  if (shots.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No shots yet. Generate story and plan shots first.
      </div>
    );
  }

  const toggleSelectAll = () => {
    if (selectedIndices.length === shots.length) {
      setSelectedIndices([]);
    } else {
      setSelectedIndices(shots.map(s => s.index));
    }
  };

  const toggleSelectShot = (index: number, selected: boolean) => {
    if (selected) {
      setSelectedIndices(prev => [...prev, index]);
    } else {
      setSelectedIndices(prev => prev.filter(i => i !== index));
    }
  };

  const handleBatchSubmit = async () => {
    if (selectedIndices.length === 0 || !showBatchModal) return;

    try {
      if (showBatchModal === 'image') {
        await batchRegenerate.mutateAsync({
          shot_indices: selectedIndices,
          regenerate_images: true,
          regenerate_videos: false,
          force: true,
          image_mode: imageMode,
          image_workflow: imageWorkflow
        });
      } else {
        await batchRegenerate.mutateAsync({
          shot_indices: selectedIndices,
          regenerate_images: false,
          regenerate_videos: true,
          force: true,
          video_workflow: videoWorkflow
        });
      }
      setShowBatchModal(null);
      setSelectedIndices([]); // Clear selection after success
      alert(`Successfully queued ${selectedIndices.length} shots for regeneration.`);
    } catch (error) {
      console.error('Batch generation failed:', error);
      alert('Batch regeneration failed. Check console for details.');
    }
  };

  return (
    <div className="relative">
      {/* Header Actions */}
      <div className="flex items-center justify-between mb-4">
        <button 
          onClick={toggleSelectAll}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {selectedIndices.length === shots.length ? (
            <CheckSquare className="w-4 h-4" />
          ) : (
            <Square className="w-4 h-4" />
          )}
          {selectedIndices.length > 0 ? `${selectedIndices.length} Selected` : 'Select All'}
        </button>
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
          onClick={() => setSelectedIndices([])}
          className="ml-2 p-1.5 hover:bg-muted rounded-full text-muted-foreground"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {shots.map((shot) => (
          <ShotCard
            key={shot.index}
            shot={shot}
            sessionId={sessionId}
            selectable={true}
            selected={selectedIndices.includes(shot.index)}
            onSelectChange={(selected) => toggleSelectShot(shot.index, selected)}
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
              Batch Regenerate {showBatchModal === 'image' ? 'Images' : 'Videos'} ({selectedIndices.length} shots)
            </h2>

            {showBatchModal === 'image' ? (
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
            ) : (
              <div className="space-y-4">
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
                disabled={batchRegenerate.isPending}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-sm flex items-center gap-2 disabled:opacity-50"
              >
                {batchRegenerate.isPending ? (
                  <>
                    <RotateCw className="w-4 h-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  'Start Generation'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
