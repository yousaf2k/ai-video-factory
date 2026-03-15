/**
 * QueueItem component - Individual queue item card
 */
import React, { useState } from 'react';
import { QueueItem as QueueItemType, QueueItemStatus, GenerationType } from '../../types';
import {
  Clock,
  Play,
  Check,
  X,
  GripVertical,
  MoreVertical,
  StopCircle,
  RotateCw
} from 'lucide-react';

interface QueueItemProps {
  item: QueueItemType;
  isSelected?: boolean;
  onSelect?: (itemId: string) => void;
  onCancel?: (itemId: string) => void;
  onRequeue?: (itemId: string) => void;
  dragListeners?: Record<string, any>;
  dragAttributes?: Record<string, any>;
}

export function QueueItem({ item, isSelected, onSelect, onCancel, onRequeue, dragListeners, dragAttributes }: QueueItemProps) {
  const [isDragging, setIsDragging] = useState(false);

  const getStatusIcon = () => {
    switch (item.status) {
      case QueueItemStatus.QUEUED:
        return <Clock className="w-4 h-4 text-gray-400" />;
      case QueueItemStatus.ACTIVE:
        return <Play className="w-4 h-4 text-blue-500" />;
      case QueueItemStatus.COMPLETED:
        return <Check className="w-4 h-4 text-green-500" />;
      case QueueItemStatus.CANCELLED:
        return <X className="w-4 h-4 text-gray-400" />;
      case QueueItemStatus.FAILED:
        return <X className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusBadge = () => {
    switch (item.status) {
      case QueueItemStatus.ACTIVE:
        return 'border-blue-500 bg-blue-50/30';
      case QueueItemStatus.COMPLETED:
        return 'border-green-500/50 bg-green-50/20';
      case QueueItemStatus.CANCELLED:
        return 'border-gray-400/50 bg-gray-50/20 opacity-60';
      case QueueItemStatus.FAILED:
        return 'border-red-500/50 bg-red-50/20';
      default:
        return 'border-gray-200 hover:border-gray-300';
    }
  };

  const getGenerationTypeLabel = () => {
    switch (item.generation_type) {
      case GenerationType.IMAGE:
        return 'Image';
      case GenerationType.THEN_IMAGE:
        return 'THEN Image';
      case GenerationType.NOW_IMAGE:
        return 'NOW Image';
      case GenerationType.VIDEO:
        return 'Video';
      case GenerationType.MEETING_VIDEO:
        return 'Meeting Video';
      case GenerationType.DEPARTURE_VIDEO:
        return 'Departure Video';
      case GenerationType.NARRATION:
        return 'Narration';
      case GenerationType.BACKGROUND:
        return 'Background';
      default:
        return 'Unknown';
    }
  };

  const getGenerationTypeColor = () => {
    switch (item.generation_type) {
      case GenerationType.IMAGE:
      case GenerationType.THEN_IMAGE:
      case GenerationType.NOW_IMAGE:
        return 'bg-purple-100 text-purple-700';
      case GenerationType.VIDEO:
      case GenerationType.MEETING_VIDEO:
      case GenerationType.DEPARTURE_VIDEO:
        return 'bg-blue-100 text-blue-700';
      case GenerationType.NARRATION:
        return 'bg-green-100 text-green-700';
      case GenerationType.BACKGROUND:
        return 'bg-orange-100 text-orange-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  };

  const canCancel = item.status === QueueItemStatus.QUEUED || item.status === QueueItemStatus.ACTIVE;
  const canRequeue = item.status === QueueItemStatus.FAILED || item.status === QueueItemStatus.CANCELLED;

  return (
    <div
      className={`
        relative bg-white rounded-lg border-2 transition-all
        ${isSelected ? 'ring-2 ring-primary border-primary' : getStatusBadge()}
        ${isDragging ? 'opacity-50 shadow-lg' : ''}
      `}
    >
      <div className="flex items-center gap-3 p-4">
        {/* Drag handle */}
        <div
          className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600"
          {...dragAttributes}
          {...dragListeners}
        >
          <GripVertical className="w-5 h-5" />
        </div>

        {/* Checkbox */}
        {onSelect && (
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onSelect(item.item_id)}
            className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
          />
        )}

        {/* Status icon */}
        <div className="flex-shrink-0">
          {getStatusIcon()}
        </div>

        {/* Thumbnail (if available) */}
        {item.shot_index && item.project_id && (
          <div className="flex-shrink-0 w-12 h-12 rounded bg-gray-200 overflow-hidden">
            <img
              src={`/api/projects/${item.project_id}/images/shot_${String(item.shot_index).padStart(3, '0')}_001.png`}
              alt={`Shot ${item.shot_index}`}
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = 'none';
              }}
            />
          </div>
        )}

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {/* Project title */}
            <span className="font-medium text-sm text-gray-900 truncate">
              {item.project_title || item.project_id}
            </span>

            {/* Shot index */}
            {item.shot_index && (
              <span className="text-xs text-gray-500">
                Shot {item.shot_index}
              </span>
            )}

            {/* Generation type badge */}
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getGenerationTypeColor()}`}>
              {getGenerationTypeLabel()}
            </span>

            {/* FLFI2V badge */}
            {item.is_flfi2v && (
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-pink-100 text-pink-700">
                FLFI2V
              </span>
            )}
          </div>

          {/* Scene and character info */}
          {(item.scene_name || item.character_name) && (
            <div className="flex items-center gap-2 text-xs text-gray-500">
              {item.scene_name && <span>{item.scene_name}</span>}
              {item.character_name && <span>• {item.character_name}</span>}
            </div>
          )}

          {/* Error message */}
          {item.status === QueueItemStatus.FAILED && item.error_message && (
            <div className="mt-2 text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
              {item.error_message}
            </div>
          )}

          {/* Progress bar (for active items) */}
          {item.status === QueueItemStatus.ACTIVE && (
            <div className="mt-2">
              <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                <span>Generating...</span>
                <span>{item.progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-1.5">
                <div
                  className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${item.progress}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Cancel button */}
        {canCancel && onCancel && (
          <button
            onClick={() => onCancel(item.item_id)}
            className="flex-shrink-0 p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-full transition-colors"
            title="Cancel generation"
          >
            <StopCircle className="w-5 h-5" />
          </button>
        )}

        {/* Requeue button */}
        {canRequeue && onRequeue && (
          <button
            onClick={() => onRequeue(item.item_id)}
            className="flex-shrink-0 p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-full transition-colors"
            title="Requeue generation"
          >
            <RotateCw className="w-5 h-5" />
          </button>
        )}
      </div>
    </div>
  );
}

export default QueueItem;
