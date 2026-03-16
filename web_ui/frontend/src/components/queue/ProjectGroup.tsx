/**
 * ProjectGroup component - Collapsible project grouping for queue
 */
import React, { useState } from 'react';
import { Progress } from '../ui/progress';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { QueueItem as QueueItemType, QueueItemStatus } from '../../types';
import QueueList from './QueueList';

interface ProjectGroupProps {
  projectId: string;
  projectTitle: string;
  items: QueueItemType[];
  selectedItems?: Set<string>;
  onSelectItem?: (itemId: string) => void;
  onCancelItem?: (itemId: string) => void;
  onRequeueItem?: (itemId: string) => void;
  onReorder?: (itemIds: string[]) => void;
  onImageClick?: (itemId: string) => void;
}

export function ProjectGroup({
  projectId,
  projectTitle,
  items,
  selectedItems,
  onSelectItem,
  onCancelItem,
  onRequeueItem,
  onReorder,
  onImageClick
}: ProjectGroupProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  // Calculate project statistics
  const total = items.length;
  const completed = items.filter(item => item.status === QueueItemStatus.COMPLETED).length;
  const active = items.filter(item => item.status === QueueItemStatus.ACTIVE).length;
  const failed = items.filter(item => item.status === QueueItemStatus.FAILED).length;

  // Count by type
  const images = items.filter(item =>
    item.generation_type.includes('image') || item.generation_type.includes('IMAGE')
  ).length;
  const videos = items.filter(item =>
    item.generation_type.includes('video') || item.generation_type.includes('VIDEO')
  ).length;
  const flfi2v = items.filter(item => item.is_flfi2v).length;

  return (
    <div className="border border-border rounded-xl overflow-hidden bg-card/20 backdrop-blur-sm">
      {/* Project header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 bg-card hover:bg-accent/50 transition-colors flex items-center justify-between border-b border-border/50"
      >
        <div className="flex items-center gap-3">
          {/* Expand/collapse icon */}
          {isExpanded ? (
            <ChevronDown className="w-5 h-5 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-5 h-5 text-muted-foreground" />
          )}

          {/* Project title */}
          <span className="font-medium text-foreground">
            {projectTitle}
          </span>

          {/* Badge with item count */}
          <span className="px-2 py-0.5 bg-muted text-muted-foreground rounded-full text-xs font-medium">
            {total}
          </span>

          {/* Status badges */}
          {active > 0 && (
            <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-full text-xs font-medium">
              {active} active
            </span>
          )}
          {completed > 0 && (
            <span className="px-2 py-0.5 bg-green-500/10 text-green-400 border border-green-500/20 rounded-full text-xs font-medium">
              {completed} completed
            </span>
          )}
          {failed > 0 && (
            <span className="px-2 py-0.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded-full text-xs font-medium">
              {failed} failed
            </span>
          )}
        </div>

        {/* Type breakdown */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          {images > 0 && (
            <span className="px-2 py-0.5 bg-purple-500/10 text-purple-400 border border-purple-500/20 rounded-full">
              {images} images
            </span>
          )}
          {videos > 0 && (
            <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-full">
              {videos} videos
            </span>
          )}
          {flfi2v > 0 && (
            <span className="px-2 py-0.5 bg-pink-500/10 text-pink-400 border border-pink-500/20 rounded-full">
              {flfi2v} FLFI2V
            </span>
          )}
        </div>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="p-4 bg-transparent">
          {/* Progress bar */}
          {total > 0 && (
            <div className="mb-4">
              <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                <span>Progress</span>
                <span>{completed}/{total} items completed</span>
              </div>
              <Progress value={(completed / total) * 100} className="h-2 bg-muted/40" />
            </div>
          )}

          {/* Queue items list */}
          <QueueList
            items={items}
            selectedItems={selectedItems}
            onSelectItem={onSelectItem}
            onCancelItem={onCancelItem}
            onRequeueItem={onRequeueItem}
            onReorder={onReorder}
            onImageClick={onImageClick}
          />
        </div>
      )}
    </div>
  );
}

export default ProjectGroup;
