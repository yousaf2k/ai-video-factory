/**
 * QueueItem component - Individual queue item card
 */
import React, { useState } from 'react';
import { Progress } from '../ui/progress';
import { QueueItem as QueueItemType, QueueItemStatus, GenerationType } from '../../types';
import {
  Clock,
  Play,
  Check,
  X,
  GripVertical,
  MoreVertical,
  StopCircle,
  RotateCw,
  Pause
} from 'lucide-react';

interface QueueItemProps {
  item: QueueItemType;
  isSelected?: boolean;
  onSelect?: (itemId: string) => void;
  onCancel?: (itemId: string) => void;
  onRequeue?: (itemId: string) => void;
  onImageClick?: (itemId: string) => void;
  dragListeners?: Record<string, any>;
  dragAttributes?: Record<string, any>;
}

export function QueueItem({ item, isSelected, onSelect, onCancel, onRequeue, onImageClick, dragListeners, dragAttributes }: QueueItemProps) {
  const getImageUrl = () => {
    if (!item.shot_index || !item.project_id) return null;
    const padded = String(item.shot_index).padStart(3, '0');
    if (item.generation_type === GenerationType.THEN_IMAGE) {
      return `/api/projects/${item.project_id}/images/shot_${padded}_then_001.png`;
    }
    if (item.generation_type === GenerationType.NOW_IMAGE) {
      return `/api/projects/${item.project_id}/images/shot_${padded}_now_001.png`;
    }
    return `/api/projects/${item.project_id}/images/shot_${padded}_001.png`;
  };
  const [isDragging, setIsDragging] = useState(false);

  const getStatusIcon = () => {
    switch (item.status) {
      case QueueItemStatus.QUEUED:
        return <Clock className="w-4 h-4 text-muted-foreground/80" />;
      case QueueItemStatus.ACTIVE:
        return <Play className="w-4 h-4 text-blue-500" />;
      case QueueItemStatus.COMPLETED:
        return <Check className="w-4 h-4 text-green-500" />;
      case QueueItemStatus.CANCELLED:
        return <X className="w-4 h-4 text-muted-foreground/80" />;
      case QueueItemStatus.FAILED:
        return <X className="w-4 h-4 text-red-500" />;
      case QueueItemStatus.PAUSED:
        return <Pause className="w-4 h-4 text-yellow-500" />;
      default:
        return null;
    }
  };

  const getStatusBadge = () => {
    switch (item.status) {
      case QueueItemStatus.ACTIVE:
        return 'border-blue-500/40 bg-blue-500/5 shadow-sm shadow-blue-500/10';
      case QueueItemStatus.COMPLETED:
        return 'border-green-500/30 bg-green-500/5 opacity-90';
      case QueueItemStatus.CANCELLED:
        return 'border-gray-300 bg-muted/30 opacity-70';
      case QueueItemStatus.FAILED:
        return 'border-destructive/30 bg-destructive/5';
      case QueueItemStatus.PAUSED:
        return 'border-yellow-500/30 bg-yellow-500/5';
      default:
        return 'border-gray-200/80 hover:border-gray-300/80';
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

  const canCancel = item.status === QueueItemStatus.QUEUED || item.status === QueueItemStatus.ACTIVE || item.status === QueueItemStatus.PAUSED;
  const canRequeue = item.status === QueueItemStatus.FAILED || item.status === QueueItemStatus.CANCELLED;

  const formatDateTime = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    try {
      const date = new Date(dateStr);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch (e) {
      return 'N/A';
    }
  };

  const getDuration = () => {
    if (!item.started_at || !item.completed_at) return null;
    try {
      const start = new Date(item.started_at).getTime();
      const end = new Date(item.completed_at).getTime();
      const diffMs = end - start;
      const diffSec = Math.floor(diffMs / 1000);
      if (diffSec < 0) return '0s';
      const minutes = Math.floor(diffSec / 60);
      const seconds = diffSec % 60;
      return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
    } catch (e) {
      return null;
    }
  };

  return (
    <div
      className={`
        relative bg-card/40 backdrop-blur-sm rounded-2xl border border-border shadow-sm hover:shadow-md hover:bg-card/60 hover:-translate-y-0.5 transition-all duration-200
        ${isSelected ? 'ring-2 ring-primary border-primary' : getStatusBadge()}
        ${isDragging ? 'opacity-50 shadow-lg' : ''}
      `}
    >
      <div className="flex items-center gap-3 p-4">
        {/* Drag handle */}
        <div
          className="cursor-grab active:cursor-grabbing text-muted-foreground/80 hover:text-gray-600"
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
          <div 
            className="flex-shrink-0 w-12 h-12 rounded bg-muted overflow-hidden cursor-pointer hover:ring-2 hover:ring-primary transition-all bg-black/20"
            onClick={() => onImageClick?.(item.item_id)}
            title="View Fullscreen"
          >
            <img
              src={getImageUrl() || ''}
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
            <span className="font-medium text-sm text-foreground truncate">
              {item.project_title || item.project_id}
            </span>

            {/* Shot index */}
            {item.shot_index && (
              <span className="text-xs text-muted-foreground">
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
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {item.scene_name && <span>{item.scene_name}</span>}
              {item.character_name && <span>• {item.character_name}</span>}
            </div>
          )}

          {/* Time and Duration Details */}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-[11px] text-muted-foreground/80">
            <span title={`Created: ${item.created_at ? new Date(item.created_at).toLocaleString() : 'N/A'}`}>
              Created: {formatDateTime(item.created_at)}
            </span>
            {item.started_at && (
              <span title={`Started: ${new Date(item.started_at).toLocaleString()}`}>
                • Started: {formatDateTime(item.started_at)}
              </span>
            )}
            {item.completed_at && (
              <span title={`Ended: ${new Date(item.completed_at).toLocaleString()}`}>
                • Ended: {formatDateTime(item.completed_at)}
              </span>
            )}
            {getDuration() && (
              <span className="text-blue-500 font-medium" title="Total generation time">
                • Duration: {getDuration()}
              </span>
            )}
          </div>

          {/* Error message */}
          {item.status === QueueItemStatus.FAILED && item.error_message && (
            <div className="mt-2 text-xs text-red-600 bg-red-50/80 border border-red-100/50 px-2.5 py-1.5 rounded-lg font-medium">
              {item.error_message}
            </div>
          )}

          {/* Progress bar (for active items) */}
          {item.status === QueueItemStatus.ACTIVE && (
            <div className="mt-2">
              <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                <span>Generating...</span>
                <span>{item.progress}%</span>
              </div>
              <div className="w-full bg-muted rounded-full h-1.5">
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
            className="flex-shrink-0 p-1.5 text-muted-foreground/80 hover:text-red-600 hover:bg-red-500/10 rounded-xl transition-all hover:scale-105 border border-transparent hover:border-red-100"
            title="Cancel generation"
          >
            <StopCircle className="w-5 h-5" />
          </button>
        )}

        {/* Requeue button */}
        {canRequeue && onRequeue && (
          <button
            onClick={() => onRequeue(item.item_id)}
            className="flex-shrink-0 p-1.5 text-muted-foreground/80 hover:text-blue-600 hover:bg-blue-500/10 rounded-xl transition-all hover:scale-105 border border-transparent hover:border-blue-100"
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
