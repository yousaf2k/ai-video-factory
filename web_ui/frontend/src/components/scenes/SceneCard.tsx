/**
 * SceneCard component - Individual scene in the story editor
 */
import { useState } from 'react';
import { GripVertical, Trash2, Edit3, Check } from 'lucide-react';
import { Scene } from '@/types';
import { cn } from '@/lib/utils';

interface SceneCardProps {
  scene: Scene;
  index: number;
  isDragging?: boolean;
  onUpdate?: (index: number, scene: Scene) => void;
  onDelete?: (index: number) => void;
}

export function SceneCard({ scene, index, isDragging, onUpdate, onDelete }: SceneCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedScene, setEditedScene] = useState<Scene>(scene);

  const handleSave = () => {
    onUpdate?.(index, editedScene);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedScene(scene);
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <div className={cn(
        "border rounded-lg p-4 bg-background",
        isDragging && "opacity-50"
      )}>
        <div className="flex items-start gap-3 mb-3">
          <GripVertical className="mt-1 text-muted-foreground cursor-move" />
          <div className="flex-1 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-muted-foreground">Scene {index + 1}</span>
              <div className="flex gap-2">
                <button
                  onClick={handleCancel}
                  className="p-1 hover:bg-muted rounded"
                  title="Cancel"
                >
                  ✕
                </button>
                <button
                  onClick={handleSave}
                  className="p-1 bg-primary text-primary-foreground rounded hover:bg-primary/90"
                  title="Save"
                >
                  <Check className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-muted-foreground">Location</label>
                <input
                  type="text"
                  value={editedScene.location}
                  onChange={(e) => setEditedScene({ ...editedScene, location: e.target.value })}
                  className="w-full px-2 py-1 border rounded text-sm mt-1"
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground">Characters</label>
                <input
                  type="text"
                  value={editedScene.characters}
                  onChange={(e) => setEditedScene({ ...editedScene, characters: e.target.value })}
                  className="w-full px-2 py-1 border rounded text-sm mt-1"
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground">Action</label>
                <input
                  type="text"
                  value={editedScene.action}
                  onChange={(e) => setEditedScene({ ...editedScene, action: e.target.value })}
                  className="w-full px-2 py-1 border rounded text-sm mt-1"
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground">Emotion</label>
                <input
                  type="text"
                  value={editedScene.emotion}
                  onChange={(e) => setEditedScene({ ...editedScene, emotion: e.target.value })}
                  className="w-full px-2 py-1 border rounded text-sm mt-1"
                />
              </div>

              <div className="md:col-span-2">
                <label className="text-xs text-muted-foreground">Narration</label>
                <textarea
                  value={editedScene.narration}
                  onChange={(e) => setEditedScene({ ...editedScene, narration: e.target.value })}
                  className="w-full px-2 py-1 border rounded text-sm mt-1 min-h-[60px]"
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground">Duration (seconds)</label>
                <input
                  type="number"
                  value={editedScene.scene_duration || ''}
                  onChange={(e) => setEditedScene({
                    ...editedScene,
                    scene_duration: e.target.value ? parseInt(e.target.value) : undefined
                  })}
                  className="w-full px-2 py-1 border rounded text-sm mt-1"
                  min="5"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn(
      "border rounded-lg p-4 bg-background hover:shadow-md transition-shadow",
      isDragging && "opacity-50"
    )}>
      <div className="flex items-start gap-3">
        <GripVertical className="mt-1 text-muted-foreground cursor-move" />
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-muted-foreground">Scene {index + 1}</span>
            <div className="flex gap-2">
              <button
                onClick={() => setIsEditing(true)}
                className="p-1 hover:bg-muted rounded"
                title="Edit scene"
              >
                <Edit3 className="w-4 h-4" />
              </button>
              <button
                onClick={() => onDelete?.(index)}
                className="p-1 hover:bg-red-50 text-red-600 rounded"
                title="Delete scene"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="space-y-1 text-sm">
            <div>
              <span className="font-medium">Location:</span> {scene.location}
            </div>
            <div>
              <span className="font-medium">Characters:</span> {scene.characters}
            </div>
            <div>
              <span className="font-medium">Action:</span> {scene.action}
            </div>
            <div>
              <span className="font-medium">Emotion:</span> {scene.emotion}
            </div>
            {scene.scene_duration && (
              <div>
                <span className="font-medium">Duration:</span> {scene.scene_duration}s
              </div>
            )}
            {scene.narration && (
              <div className="italic text-muted-foreground mt-2">
                "{scene.narration}"
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
