/**
 * SceneList component - Draggable list of scenes
 */
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { SceneCard } from './SceneCard';
import { Scene } from '@/types';
import { Plus } from 'lucide-react';

interface SceneListProps {
  scenes: Scene[];
  onUpdate?: (index: number, scene: Scene) => void;
  onDelete?: (index: number) => void;
  onReorder?: (scenes: Scene[]) => void;
  onAdd?: () => void;
  projectType?: number;
}

export function SceneList({ scenes, onUpdate, onDelete, onReorder, onAdd, projectType }: SceneListProps) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = scenes.findIndex((_, i) => `${i}` === active.id);
      const newIndex = scenes.findIndex((_, i) => `${i}` === over.id);

      const newScenes = arrayMove(scenes, oldIndex, newIndex);
      onReorder?.(newScenes);
    }
  };

  return (
    <div className="space-y-4">
      {scenes.length > 0 ? (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={scenes.map((_, i) => `${i}`)}
            strategy={verticalListSortingStrategy}
          >
            {scenes.map((scene, index) => (
              <div key={index} id={`${index}`}>
                <SceneCard
                  scene={scene}
                  index={index}
                  onUpdate={onUpdate}
                  onDelete={onDelete}
                  projectType={projectType}
                />
              </div>
            ))}
          </SortableContext>
        </DndContext>
      ) : (
        <div className="text-center py-12 text-muted-foreground">
          No scenes yet. Add your first scene to get started.
        </div>
      )}

      {onAdd && (
        <button
          onClick={onAdd}
          className="w-full py-3 border-2 border-dashed rounded-lg text-muted-foreground hover:border-primary hover:text-primary transition-colors flex items-center justify-center gap-2"
        >
          <Plus className="w-5 h-5" />
          Add Scene
        </button>
      )}
    </div>
  );
}
