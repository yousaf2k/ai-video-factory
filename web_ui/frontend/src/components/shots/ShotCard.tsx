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
}

export function ShotCard({ shot, sessionId, showIndex = true }: ShotCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedShot, setEditedShot] = useState(shot);

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
    if (!confirm(`Regenerate image for Shot ${shot.index}?`)) return;
    try {
      await regenerateImage.mutateAsync({ shotIndex: shot.index, force: true });
    } catch (error) {
      console.error('Failed to regenerate image:', error);
      alert('Failed to regenerate image. Please try again.');
    }
  };

  const handleRegenerateVideo = async () => {
    if (!confirm(`Regenerate video for Shot ${shot.index}?`)) return;
    try {
      await regenerateVideo.mutateAsync({ shotIndex: shot.index, force: true });
    } catch (error) {
      console.error('Failed to regenerate video:', error);
      alert('Failed to regenerate video. Please try again.');
    }
  };

  if (isEditing) {
    return (
      <div className="border rounded-lg p-4 bg-background">
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
    <div className="border rounded-lg p-4 bg-background hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
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

      {/* Image Preview */}
      {shot.image_path && (
        <div className="mb-3 aspect-video bg-muted rounded overflow-hidden">
          <img
            src={shot.image_path}
            alt={`Shot ${shot.index}`}
            className="w-full h-full object-cover"
          />
        </div>
      )}

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
    </div>
  );
}
