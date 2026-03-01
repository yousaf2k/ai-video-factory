/**
 * ShotCard component - Individual shot with editing and regeneration
 */
import { useState } from 'react';
import { Edit3, RotateCw, Image, Video, Check, X } from 'lucide-react';
import { Shot } from '@/types';
import { useUpdateShot, useRegenerateImage, useRegenerateVideo } from '@/hooks/useShots';
import { api } from '@/services/api';
import { cn } from '@/lib/utils';

interface ShotCardProps {
  shot: Shot;
  sessionId: string;
  showIndex?: boolean;
  selectable?: boolean;
  selected?: boolean;
  onSelectChange?: (selected: boolean) => void;
}

export function ShotCard({ 
  shot, 
  sessionId, 
  showIndex = true,
  selectable = false,
  selected = false,
  onSelectChange
}: ShotCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedShot, setEditedShot] = useState(shot);
  const [viewMode, setViewMode] = useState<'image' | 'video'>(
    shot.video_rendered && shot.video_path ? 'video' : 'image'
  );
  
  // Regeneration modal state
  const [showRegenModal, setShowRegenModal] = useState<'image' | 'video' | null>(null);
  const [regenForce, setRegenForce] = useState(true);
  const [regenImageMode, setRegenImageMode] = useState('comfyui');
  const [regenImageWorkflow, setRegenImageWorkflow] = useState('flux2');
  const [regenVideoWorkflow, setRegenVideoWorkflow] = useState('workflow/video/wan22_workflow.json');

  // ... rest of the hook setup ...
  const updateShot = useUpdateShot(sessionId, shot.index);
  const regenerateImage = useRegenerateImage(sessionId);
  const regenerateVideo = useRegenerateVideo(sessionId);

  const handleSave = async () => {
    try {
      await updateShot.mutateAsync({
        image_prompt: editedShot.image_prompt,
        motion_prompt: editedShot.motion_prompt,
        camera: editedShot.camera,
        narration: editedShot.narration,
      });
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to update shot:', error);
      alert('Failed to update shot. Please try again.');
    }
  };

  const handleCancel = () => {
    setEditedShot(shot);
    setIsEditing(false);
  };

  const handleRegenerateImage = async () => {
    setShowRegenModal('image');
  };

  const handleRegenerateVideo = async () => {
    setShowRegenModal('video');
  };

  const handleRegenSubmit = async () => {
    try {
      if (showRegenModal === 'image') {
        await regenerateImage.mutateAsync({ 
          shotIndex: shot.index, 
          force: regenForce,
          imageMode: regenImageMode,
          imageWorkflow: regenImageWorkflow
        });
      } else if (showRegenModal === 'video') {
        await regenerateVideo.mutateAsync({ 
          shotIndex: shot.index, 
          force: regenForce,
          videoWorkflow: regenVideoWorkflow
        });
        setViewMode('video');
      }
      setShowRegenModal(null);
    } catch (error) {
      console.error(`Failed to regenerate ${showRegenModal}:`, error);
      alert(`Failed to regenerate ${showRegenModal}. Please try again.`);
    }
  };

  // Helper to convert internal output paths to API URLs
  const getMediaUrl = (path: string | null) => {
    if (!path) return '';
    
    // Normalize slashes
    let normalizedPath = path.replace(/\\/g, '/');
    
    // If it's an absolute path (e.g. C:/... or /home/...), extract the part starting from 'output/'
    const outputIndex = normalizedPath.indexOf('output/sessions/');
    if (outputIndex !== -1) {
      normalizedPath = normalizedPath.substring(outputIndex);
    }
    
    return normalizedPath.replace(/^output[\\/]sessions[\\/]/, '/api/sessions/').replace(/\\/g, '/');
  };

  const imageUrl = getMediaUrl(shot.image_path);
  const videoUrl = getMediaUrl(shot.video_path);

  if (isEditing) {
    return (
      <div className={cn("border rounded-lg p-4 bg-background", selected && "border-primary ring-1 ring-primary")}>
        {/* ... editing UI ... */}
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-muted-foreground">
            Shot {shot.index}
          </span>
          <div className="flex gap-2">
            <button
              onClick={handleCancel}
              className="p-1 hover:bg-muted rounded"
              title="Cancel"
            >
              <X className="w-4 h-4" />
            </button>
            <button
              onClick={handleSave}
              disabled={updateShot.isPending}
              className="p-1 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50"
              title="Save"
            >
              <Check className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="space-y-3">
          <div>
            <label className="text-xs text-muted-foreground">Image Prompt</label>
            <textarea
              value={editedShot.image_prompt}
              onChange={(e) => setEditedShot({ ...editedShot, image_prompt: e.target.value })}
              className="w-full px-2 py-1 border rounded text-sm mt-1 min-h-[60px]"
            />
          </div>

          <div>
            <label className="text-xs text-muted-foreground">Motion Prompt</label>
            <textarea
              value={editedShot.motion_prompt}
              onChange={(e) => setEditedShot({ ...editedShot, motion_prompt: e.target.value })}
              className="w-full px-2 py-1 border rounded text-sm mt-1 min-h-[60px]"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted-foreground">Camera</label>
              <input
                type="text"
                value={editedShot.camera}
                onChange={(e) => setEditedShot({ ...editedShot, camera: e.target.value })}
                className="w-full px-2 py-1 border rounded text-sm mt-1"
              />
            </div>

            <div>
              <label className="text-xs text-muted-foreground">Narration</label>
              <input
                type="text"
                value={editedShot.narration}
                onChange={(e) => setEditedShot({ ...editedShot, narration: e.target.value })}
                className="w-full px-2 py-1 border rounded text-sm mt-1"
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("border rounded-lg p-4 bg-background hover:shadow-md transition-shadow relative", selected && "border-primary ring-1 ring-primary")}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          {selectable && (
            <input
              type="checkbox"
              checked={selected}
              onChange={(e) => onSelectChange?.(e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
            />
          )}
          <div className="flex-1">
            {showIndex && (
              <span className="text-sm font-medium text-muted-foreground">
                Shot {shot.index}
              </span>
            )}
            <div className="flex gap-2 mt-1">
              <span className="text-xs bg-muted px-2 py-0.5 rounded">
                {shot.camera}
              </span>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          <button
            onClick={() => setIsEditing(true)}
            className="p-1 hover:bg-muted rounded"
            title="Edit prompts"
          >
            <Edit3 className="w-4 h-4" />
          </button>
          <button
            onClick={handleRegenerateImage}
            disabled={regenerateImage.isPending}
            className="p-1 hover:bg-blue-50 text-blue-600 rounded disabled:opacity-50"
            title="Regenerate image"
          >
            <RotateCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleRegenerateVideo}
            disabled={regenerateVideo.isPending}
            className="p-1 hover:bg-purple-50 text-purple-600 rounded disabled:opacity-50"
            title="Regenerate video"
          >
            <Video className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Status */}
      <div className="flex gap-3 text-xs mb-3">
        <span className={cn(
          "flex items-center gap-1",
          shot.image_generated ? "text-green-600" : "text-gray-400"
        )}>
          <Image className="w-3 h-3" />
          Image: {shot.image_generated ? "✓" : "○"}
        </span>
        <span className={cn(
          "flex items-center gap-1",
          shot.video_rendered ? "text-green-600" : "text-gray-400"
        )}>
          <Video className="w-3 h-3" />
          Video: {shot.video_rendered ? "✓" : "○"}
        </span>
      </div>

      {/* Media Preview */}
      <div className="mb-3 relative group">
        <div className="aspect-video bg-muted rounded overflow-hidden flex items-center justify-center relative">
          {viewMode === 'video' && videoUrl ? (
            <video
              src={videoUrl}
              poster={imageUrl}
              controls
              autoPlay
              muted
              loop
              playsInline
              className="w-full h-full object-cover"
            />
          ) : imageUrl ? (
            <img
              src={imageUrl}
              alt={`Shot ${shot.index}`}
              className="w-full h-full object-cover"
            />
          ) : (
            <span className="text-muted-foreground text-xs">No media available</span>
          )}
        </div>

        {/* Media Toggle Controls */}
        {shot.image_path && shot.video_path && (
          <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity bg-black/50 backdrop-blur-sm p-1 rounded-md">
            <button
              onClick={() => setViewMode('image')}
              className={cn(
                "p-1.5 rounded transition-colors",
                viewMode === 'image' ? "bg-white text-black" : "text-white hover:bg-white/20"
              )}
              title="View Image"
            >
              <Image className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode('video')}
              className={cn(
                "p-1.5 rounded transition-colors",
                viewMode === 'video' ? "bg-white text-black" : "text-white hover:bg-white/20"
              )}
              title="View Video"
            >
              <Video className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Prompts */}
      <div className="space-y-2 text-sm">
        <div className="p-2 bg-muted rounded">
          <div className="text-xs text-muted-foreground mb-1">Image Prompt</div>
          <div className="line-clamp-2">{shot.image_prompt}</div>
        </div>
        <div className="p-2 bg-muted rounded">
          <div className="text-xs text-muted-foreground mb-1">Motion Prompt</div>
          <div className="line-clamp-2">{shot.motion_prompt}</div>
        </div>
      </div>

      {/* Narration */}
      {shot.narration && (
        <div className="mt-2 text-sm italic text-muted-foreground">
          "{shot.narration}"
        </div>
      )}

      {/* Regeneration Modal */}
      {showRegenModal && (
        <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4">
          <div className="bg-background rounded-lg shadow-xl max-w-sm w-full p-6 relative">
            <button 
              onClick={() => setShowRegenModal(null)}
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
            >
              <X className="w-5 h-5" />
            </button>
            
            <h2 className="text-lg font-semibold mb-4">
              Regenerate {showRegenModal === 'image' ? 'Image' : 'Video'}
            </h2>

            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="regen-force"
                  checked={regenForce}
                  onChange={(e) => setRegenForce(e.target.checked)}
                  className="rounded border-gray-300 text-primary focus:ring-primary"
                />
                <label htmlFor="regen-force" className="text-sm">
                  Force regeneration (ignore cache)
                </label>
              </div>

              {showRegenModal === 'image' && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1">Generation Mode</label>
                    <select 
                      value={regenImageMode}
                      onChange={(e) => setRegenImageMode(e.target.value)}
                      className="w-full border rounded-md p-2 text-sm"
                    >
                      <option value="comfyui">ComfyUI (Local)</option>
                      <option value="gemini">Gemini (Cloud)</option>
                    </select>
                  </div>

                  {regenImageMode === 'comfyui' && (
                    <div>
                      <label className="block text-xs font-medium text-muted-foreground mb-1">Workflow</label>
                      <select 
                        value={regenImageWorkflow}
                        onChange={(e) => setRegenImageWorkflow(e.target.value)}
                        className="w-full border rounded-md p-2 text-sm"
                      >
                        <option value="flux2">Flux 2 (High Quality)</option>
                        <option value="flux">Flux (Standard)</option>
                        <option value="sdxl">SDXL</option>
                        <option value="default">Default</option>
                      </select>
                    </div>
                  )}
                </>
              )}

              {showRegenModal === 'video' && (
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">Video Workflow</label>
                  <input 
                    type="text"
                    value={regenVideoWorkflow}
                    onChange={(e) => setRegenVideoWorkflow(e.target.value)}
                    className="w-full border rounded-md p-2 text-sm"
                  />
                </div>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button 
                onClick={() => setShowRegenModal(null)}
                className="px-3 py-1.5 border rounded-md hover:bg-muted text-sm"
              >
                Cancel
              </button>
              <button 
                onClick={handleRegenSubmit}
                disabled={regenerateImage.isPending || regenerateVideo.isPending}
                className="px-3 py-1.5 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-sm flex items-center gap-2 disabled:opacity-50"
              >
                {regenerateImage.isPending || regenerateVideo.isPending ? (
                  <>
                    <RotateCw className="w-3 h-3 animate-spin" />
                    Processing...
                  </>
                ) : (
                  'Start'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
