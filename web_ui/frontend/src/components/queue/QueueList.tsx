/**
 * QueueList component - Sortable list with drag-and-drop
 */
import React, { useState } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
  DragStartEvent
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { QueueItem as QueueItemType } from '../../types';
import QueueItem from './QueueItem';

interface SortableQueueItemProps {
  item: QueueItemType;
  isSelected?: boolean;
  onSelect?: (itemId: string) => void;
  onCancel?: (itemId: string) => void;
  onRequeue?: (itemId: string) => void;
}

function SortableQueueItem({ item, isSelected, onSelect, onCancel, onRequeue }: SortableQueueItemProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging
  } = useSortable({ id: item.item_id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    cursor: isDragging ? 'grabbing' : 'grab'
  };

  return (
    <div ref={setNodeRef} style={style}>
      <QueueItem
        item={item}
        isSelected={isSelected}
        onSelect={onSelect}
        onCancel={onCancel}
        onRequeue={onRequeue}
        dragAttributes={attributes}
        dragListeners={listeners}
      />
    </div>
  );
}

interface QueueListProps {
  items: QueueItemType[];
  selectedItems?: Set<string>;
  onSelectItem?: (itemId: string) => void;
  onCancelItem?: (itemId: string) => void;
  onRequeueItem?: (itemId: string) => void;
  onReorder?: (itemIds: string[]) => void;
}

export function QueueList({
  items,
  selectedItems = new Set(),
  onSelectItem,
  onCancelItem,
  onRequeueItem,
  onReorder
}: QueueListProps) {
  const [activeId, setActiveId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 8px movement required to start dragging
      }
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = items.findIndex((item) => item.item_id === active.id);
      const newIndex = items.findIndex((item) => item.item_id === over.id);

      const reorderedItems = arrayMove(items, oldIndex, newIndex);
      const reorderedIds = reorderedItems.map((item) => item.item_id);

      if (onReorder) {
        onReorder(reorderedIds);
      }
    }

    setActiveId(null);
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <SortableContext
        items={items.map((item) => item.item_id)}
        strategy={verticalListSortingStrategy}
      >
        <div className="space-y-2">
          {items.map((item) => (
            <SortableQueueItem
              key={item.item_id}
              item={item}
              isSelected={selectedItems.has(item.item_id)}
              onSelect={onSelectItem}
              onCancel={onCancelItem}
              onRequeue={onRequeueItem}
            />
          ))}
        </div>
      </SortableContext>
    </DndContext>
  );
}

export default QueueList;
