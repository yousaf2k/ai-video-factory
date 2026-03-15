/**
 * SessionGroup component - Collapsible session grouping for queue
 */
import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { QueueItem as QueueItemType, QueueItemStatus } from '../../types';
import QueueList from './QueueList';

interface SessionGroupProps {
  sessionId: string;
  sessionTitle: string;
  items: QueueItemType[];
  selectedItems?: Set<string>;
  onSelectItem?: (itemId: string) => void;
  onCancelItem?: (itemId: string) => void;
  onReorder?: (itemIds: string[]) => void;
}

export function SessionGroup({
  sessionId,
  sessionTitle,
  items,
  selectedItems,
  onSelectItem,
  onCancelItem,
  onReorder
}: SessionGroupProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  // Calculate session statistics
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
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Session header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          {/* Expand/collapse icon */}
          {isExpanded ? (
            <ChevronDown className="w-5 h-5 text-gray-500" />
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-500" />
          )}

          {/* Session title */}
          <span className="font-medium text-gray-900">
            {sessionTitle}
          </span>

          {/* Badge with item count */}
          <span className="px-2 py-0.5 bg-gray-200 text-gray-700 rounded-full text-xs font-medium">
            {total}
          </span>

          {/* Status badges */}
          {active > 0 && (
            <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
              {active} active
            </span>
          )}
          {completed > 0 && (
            <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs font-medium">
              {completed} completed
            </span>
          )}
          {failed > 0 && (
            <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-medium">
              {failed} failed
            </span>
          )}
        </div>

        {/* Type breakdown */}
        <div className="flex items-center gap-2 text-xs text-gray-500">
          {images > 0 && (
            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full">
              {images} images
            </span>
          )}
          {videos > 0 && (
            <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">
              {videos} videos
            </span>
          )}
          {flfi2v > 0 && (
            <span className="px-2 py-0.5 bg-pink-100 text-pink-700 rounded-full">
              {flfi2v} FLFI2V
            </span>
          )}
        </div>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="p-4 bg-white">
          {/* Progress bar */}
          {total > 0 && (
            <div className="mb-4">
              <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                <span>Progress</span>
                <span>{completed}/{total} items completed</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-green-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${(completed / total) * 100}%` }}
                />
              </div>
            </div>
          )}

          {/* Queue items list */}
          <QueueList
            items={items}
            selectedItems={selectedItems}
            onSelectItem={onSelectItem}
            onCancelItem={onCancelItem}
            onReorder={onReorder}
          />
        </div>
      )}
    </div>
  );
}

export default SessionGroup;
