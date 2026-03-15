/**
 * QueueHeader component - Header with statistics and actions
 */
import React from 'react';
import { QueueStatistics, ViewMode } from '../../types';
import {
  List,
  FolderOpen,
  CheckSquare,
  Square,
  Trash2,
  Pause,
  Play,
  RefreshCw,
  Wifi,
  WifiOff,
  Filter
} from 'lucide-react';

interface QueueHeaderProps {
  statistics: QueueStatistics;
  isPaused: boolean;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  selectedCount: number;
  totalCount: number;
  isAllSelected: boolean;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onCancelSelected: () => void;
  onClearCompleted: () => void;
  onClearFailed: () => void;
  onClearCancelled: () => void;
  onPauseResume: () => void;
  statusFilter: string;
  onStatusFilterChange: (filter: string) => void;
  typeFilter: string;
  onTypeFilterChange: (filter: string) => void;
  wsConnected?: boolean;
}

export function QueueHeader({
  statistics,
  isPaused,
  viewMode,
  onViewModeChange,
  selectedCount,
  totalCount,
  isAllSelected,
  onSelectAll,
  onDeselectAll,
  onCancelSelected,
  onClearCompleted,
  onClearFailed,
  onClearCancelled,
  onPauseResume,
  statusFilter,
  onStatusFilterChange,
  typeFilter,
  onTypeFilterChange,
  wsConnected
}: QueueHeaderProps) {
  return (
    <div className="bg-white border-b border-gray-200 p-4">
      {/* Title row */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900">Generation Queue</h1>

          {/* Connection status indicator */}
          <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${
            wsConnected
              ? 'bg-green-100 text-green-700'
              : 'bg-gray-100 text-gray-600'
          }`} title={wsConnected ? 'Real-time updates active' : 'Using polling (5s updates)'}>
            {wsConnected ? (
              <>
                <Wifi className="w-3.5 h-3.5" />
                <span>Live</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3.5 h-3.5" />
                <span>Polling</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Statistics pills */}
      <div className="flex flex-wrap items-center gap-2 mb-4">
        {/* Total count */}
        <div className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-full text-sm font-medium">
          Total: {statistics.total}
        </div>

        {/* Queued count */}
        {statistics.queued > 0 && (
          <div className="px-3 py-1.5 bg-yellow-100 text-yellow-700 rounded-full text-sm font-medium">
            Queued: {statistics.queued}
          </div>
        )}

        {/* Active count */}
        {statistics.active > 0 && (
          <div className="px-3 py-1.5 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
            Active: {statistics.active}
          </div>
        )}

        {/* Images count */}
        {statistics.images > 0 && (
          <div className="px-3 py-1.5 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
            Images: {statistics.images}
          </div>
        )}

        {/* Videos count */}
        {statistics.videos > 0 && (
          <div className="px-3 py-1.5 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
            Videos: {statistics.videos}
          </div>
        )}

        {/* FLFI2V count */}
        {statistics.flfi2v > 0 && (
          <div className="px-3 py-1.5 bg-pink-100 text-pink-700 rounded-full text-sm font-medium">
            FLFI2V: {statistics.flfi2v}
          </div>
        )}

        {/* Completed count */}
        {statistics.completed > 0 && (
          <div className="px-3 py-1.5 bg-green-100 text-green-700 rounded-full text-sm font-medium">
            Completed: {statistics.completed}
          </div>
        )}

        {/* Failed count */}
        {statistics.failed > 0 && (
          <div className="px-3 py-1.5 bg-red-100 text-red-700 rounded-full text-sm font-medium">
            Failed: {statistics.failed}
          </div>
        )}

        {/* Projects count */}
        {statistics.total_projects > 0 && (
          <div className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full text-sm font-medium">
            Projects: {statistics.total_projects}
          </div>
        )}
      </div>

      {/* Action buttons row */}
      <div className="flex flex-wrap items-center gap-2">
        {/* View mode toggle */}
        <div className="flex items-center border border-gray-300 rounded-lg overflow-hidden">
          <button
            onClick={() => onViewModeChange('flat')}
            className={`
              px-3 py-2 text-sm font-medium transition-colors flex items-center gap-2
              ${viewMode === 'flat' ? 'bg-gray-100 text-gray-900' : 'bg-white text-gray-600 hover:bg-gray-50'}
            `}
          >
            <List className="w-4 h-4" />
            Flat View
          </button>
          <button
            onClick={() => onViewModeChange('grouped')}
            className={`
              px-3 py-2 text-sm font-medium transition-colors flex items-center gap-2
              ${viewMode === 'grouped' ? 'bg-gray-100 text-gray-900' : 'bg-white text-gray-600 hover:bg-gray-50'}
            `}
          >
            <FolderOpen className="w-4 h-4" />
            Grouped View
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center border border-gray-300 rounded-lg overflow-hidden bg-white h-auto">
          <div className="pl-3 pr-1 py-2 flex items-center bg-gray-50 border-r border-gray-200">
            <Filter className="w-4 h-4 text-gray-500" />
          </div>
          <select 
            value={statusFilter}
            onChange={(e) => onStatusFilterChange(e.target.value)}
            className="text-sm bg-transparent border-none focus:ring-0 text-gray-700 py-2 pl-2 pr-8 outline-none cursor-pointer"
          >
            <option value="all">All Status</option>
            <option value="queued">Queued</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <div className="w-px h-6 bg-gray-300 mx-1 self-center"></div>
          <select 
            value={typeFilter}
            onChange={(e) => onTypeFilterChange(e.target.value)}
            className="text-sm bg-transparent border-none focus:ring-0 text-gray-700 py-2 pl-2 pr-8 outline-none cursor-pointer"
          >
            <option value="all">All Types</option>
            <option value="image">Images</option>
            <option value="video">Videos</option>
            <option value="narration">Audio</option>
          </select>
        </div>

        {/* Selection controls */}
        <div className="h-6 w-px bg-gray-300 mx-2" />

        {isAllSelected ? (
          <button
            onClick={onDeselectAll}
            className="px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors flex items-center gap-2"
          >
            <Square className="w-4 h-4" />
            Deselect All
          </button>
        ) : (
          <button
            onClick={onSelectAll}
            className="px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors flex items-center gap-2"
          >
            <CheckSquare className="w-4 h-4" />
            Select All
          </button>
        )}

        {/* Cancel selected button */}
        {selectedCount > 0 && (
          <button
            onClick={onCancelSelected}
            className="px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors flex items-center gap-2"
          >
            <Trash2 className="w-4 h-4" />
            Cancel Selected ({selectedCount})
          </button>
        )}

        {/* Pause/Resume button */}
        <button
          onClick={onPauseResume}
          className={`
            px-3 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-2
            ${isPaused
              ? 'text-green-600 hover:bg-green-50'
              : 'text-yellow-600 hover:bg-yellow-50'
            }
          `}
        >
          {isPaused ? (
            <>
              <Play className="w-4 h-4" />
              Resume Queue
            </>
          ) : (
            <>
              <Pause className="w-4 h-4" />
              Pause Queue
            </>
          )}
        </button>

        {/* Clear completed button */}
        {statistics.completed > 0 && (
          <button
            onClick={onClearCompleted}
            className="px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Clear Completed ({statistics.completed})
          </button>
        )}

        {/* Clear failed button */}
        {statistics.failed > 0 && (
          <button
            onClick={onClearFailed}
            className="px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Clear Failed ({statistics.failed})
          </button>
        )}

        {/* Clear cancelled button */}
        {statistics.cancelled > 0 && (
          <button
            onClick={onClearCancelled}
            className="px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Clear Cancelled ({statistics.cancelled})
          </button>
        )}
      </div>
    </div>
  );
}

export default QueueHeader;
