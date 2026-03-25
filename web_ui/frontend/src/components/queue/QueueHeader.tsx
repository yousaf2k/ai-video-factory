/**
 * QueueHeader component - Header with statistics and actions
 */
import React from 'react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
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
  Filter,
  RotateCw
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
  onClearSelected?: () => void;
  hasCancellableSelected?: boolean;
  hasClearableSelected?: boolean;
  hasPausableSelected?: boolean;
  hasResumableSelected?: boolean;
  onPauseSelected?: () => void;
  onResumeSelected?: () => void;
  hasRequeueableSelected?: boolean;
  onRequeueSelected?: () => void;
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
  onClearSelected,
  hasCancellableSelected = false,
  hasClearableSelected = false,
  hasPausableSelected = false,
  hasResumableSelected = false,
  onPauseSelected,
  onResumeSelected,
  hasRequeueableSelected = false,
  onRequeueSelected,
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
    <div className="sticky top-0 z-20 bg-background/90 backdrop-blur-md border-b border-border p-4 shadow-sm flex flex-col gap-4">
      {/* Title row */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-foreground">Generation Queue</h1>

          {/* Connection status indicator */}
          <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${wsConnected
            ? 'bg-green-100 text-green-700'
            : 'bg-gray-100 text-card-foreground/80'
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
      <div className="flex flex-wrap items-center gap-2">
        {statistics.total_projects > 0 && (
          <div className="px-2.5 py-1 bg-card border border-border/80 text-card-foreground rounded-full text-xs font-semibold shadow-sm flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-gray-400"></span>
            Projects: {statistics.total_projects}
          </div>
        )}

        {statistics.queued > 0 && (
          <div className="px-2.5 py-1 bg-card border border-yellow-200 text-yellow-700 rounded-full text-xs font-semibold shadow-sm flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-yellow-400"></span>
            Queued: {statistics.queued}
          </div>
        )}

        {statistics.active > 0 && (
          <div className="px-2.5 py-1 bg-card border border-blue-200 text-blue-700 rounded-full text-xs font-semibold shadow-sm flex items-center gap-1.5 animate-pulse">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
            Active: {statistics.active}
          </div>
        )}

        {statistics.images > 0 && (
          <div className="px-2.5 py-1 bg-card border border-purple-200 text-purple-700 rounded-full text-xs font-semibold shadow-sm flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-500"></span>
            Images: {statistics.images}
          </div>
        )}

        {statistics.videos > 0 && (
          <div className="px-2.5 py-1 bg-card border border-indigo-200 text-indigo-700 rounded-full text-xs font-semibold shadow-sm flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500"></span>
            Videos: {statistics.videos}
          </div>
        )}

        {statistics.flfi2v > 0 && (
          <div className="px-2.5 py-1 bg-card border border-pink-200 text-pink-700 rounded-full text-xs font-semibold shadow-sm flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-pink-500"></span>
            FLFI2V: {statistics.flfi2v}
          </div>
        )}

        {statistics.completed > 0 && (
          <div className="px-2.5 py-1 bg-card border border-green-200 text-green-700 rounded-full text-xs font-semibold shadow-sm flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
            Completed: {statistics.completed}
          </div>
        )}

        {statistics.failed > 0 && (
          <div className="px-2.5 py-1 bg-card border border-red-200 text-red-700 rounded-full text-xs font-semibold shadow-sm flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
            Failed: {statistics.failed}
          </div>
        )}

        <div className="px-2.5 py-1 bg-muted/40 border border-border/80 text-card-foreground rounded-full text-xs font-bold shadow-sm flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-gray-600"></span>
          Total: {statistics.total}
        </div>
      </div>

      {/* Action buttons row */}
      <div className="flex flex-wrap items-center gap-2">
        {/* View mode toggle */}
        <div className="flex items-center bg-muted/80 p-1 rounded-xl gap-1">
          <button
            onClick={() => onViewModeChange('flat')}
            className={`
              px-3 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2
              ${viewMode === 'flat' ? 'bg-card shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}
            `}
          >
            <List className="w-4 h-4" />
            Flat View
          </button>
          <button
            onClick={() => onViewModeChange('grouped')}
            className={`
              px-3 py-1.5 rounded-lg text-sm font-medium transition-all flex items-center gap-2
              ${viewMode === 'grouped' ? 'bg-card shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}
            `}
          >
            <FolderOpen className="w-4 h-4" />
            Grouped View
          </button>
        </div>

        {/* Filters */}
        <div className="flex items-center bg-card border border-border/80 rounded-xl shadow-sm h-9 overflow-hidden">
          <div className="pl-3 pr-2 py-2 flex items-center bg-muted/40 h-full border-r ">
            <Filter className="w-3.5 h-3.5 text-gray-400" />
          </div>
          <Select value={statusFilter} onValueChange={onStatusFilterChange}>
            <SelectTrigger className="border-none bg-transparent shadow-none focus:ring-0 text-xs font-medium h-full pl-2 pr-4 text-card-foreground/80 w-auto hover:bg-muted/30 transition-colors">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent className="bg-card text-card-foreground">
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="active_queued">Active + Queued</SelectItem>
              <SelectItem value="queued">Queued</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>

          <div className="w-px h-5 bg-gray-800 self-center"></div>

          <Select value={typeFilter} onValueChange={onTypeFilterChange}>
            <SelectTrigger className="border-none bg-transparent shadow-none focus:ring-0 text-xs font-medium h-full pl-2 pr-4 text-card-foreground/80 w-auto hover:bg-muted/30 transition-colors">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent className="bg-card text-card-foreground">
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="image">Images</SelectItem>
              <SelectItem value="video">Videos</SelectItem>
              <SelectItem value="narration">Audio</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Selection controls */}
        <div className="h-6 w-px bg-gray-300 mx-2" />

        {isAllSelected ? (
          <button
            onClick={onDeselectAll}
            className="px-3 py-1.5 text-sm font-medium text-card-foreground/80 hover:bg-muted/40 border border-border/80 rounded-xl shadow-sm bg-card transition-all flex items-center gap-2 hover:shadow-md"
          >
            <Square className="w-4 h-4" />
            Deselect All
          </button>
        ) : (
          <button
            onClick={onSelectAll}
            className="px-3 py-1.5 text-sm font-medium text-card-foreground/80 hover:bg-muted/40 border border-border/80 rounded-xl shadow-sm bg-card transition-all flex items-center gap-2 hover:shadow-md"
          >
            <CheckSquare className="w-4 h-4" />
            Select All
          </button>
        )}

        {/* Cancel selected button */}
        {selectedCount > 0 && hasCancellableSelected && (
          <button
            onClick={onCancelSelected}
            className="px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 border border-red-100 rounded-xl shadow-sm bg-card transition-all flex items-center gap-2 hover:shadow-md animate-in fade-in-0 duration-200"
          >
            <Pause className="w-4 h-4" />
            Cancel Selected
          </button>
        )}

        {/* Pause selected button */}
        {selectedCount > 0 && hasPausableSelected && onPauseSelected && (
          <button
            onClick={onPauseSelected}
            className="px-3 py-1.5 text-sm font-medium text-yellow-600 hover:bg-yellow-50 border border-yellow-100 rounded-xl shadow-sm bg-card transition-all flex items-center gap-2 hover:shadow-md animate-in fade-in-0 duration-200"
          >
            <Pause className="w-4 h-4" />
            Pause Selected
          </button>
        )}

        {/* Resume selected button */}
        {selectedCount > 0 && hasResumableSelected && onResumeSelected && (
          <button
            onClick={onResumeSelected}
            className="px-3 py-1.5 text-sm font-medium text-green-600 hover:bg-green-50 border border-green-100 rounded-xl shadow-sm bg-card transition-all flex items-center gap-2 hover:shadow-md animate-in fade-in-0 duration-200"
          >
            <Play className="w-4 h-4" />
            Resume Selected
          </button>
        )}

        {/* Requeue selected button */}
        {selectedCount > 0 && hasRequeueableSelected && onRequeueSelected && (
          <button
            onClick={onRequeueSelected}
            className="px-3 py-1.5 text-sm font-medium text-blue-600 hover:bg-blue-50 border border-blue-100 rounded-xl shadow-sm bg-card transition-all flex items-center gap-2 hover:shadow-md animate-in fade-in-0 duration-200"
          >
            <RotateCw className="w-4 h-4" />
            Requeue Selected
          </button>
        )}

        {/* Clear selected button */}
        {selectedCount > 0 && hasClearableSelected && (
          <button
            onClick={onClearSelected}
            className="px-3 py-1.5 text-sm font-medium text-orange-600 hover:bg-orange-50 border border-orange-100 rounded-xl shadow-sm bg-card transition-all flex items-center gap-2 hover:shadow-md animate-in fade-in-0 duration-200"
          >
            <Trash2 className="w-4 h-4" />
            Clear Selected
          </button>
        )}

        {/* Pause/Resume button */}
        <button
          onClick={onPauseResume}
          className={`
            px-3 py-1.5 text-sm font-medium rounded-xl border transition-all flex items-center gap-2 shadow-sm hover:shadow-md bg-card
            ${isPaused
              ? 'text-green-600 hover:bg-green-50 border-green-100'
              : 'text-yellow-600 hover:bg-yellow-50 border-yellow-100'
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
            className="px-3 py-1.5 text-sm font-medium text-card-foreground/80 hover:bg-muted/40 border border-border/80 rounded-xl shadow-sm bg-card transition-all flex items-center gap-2 hover:shadow-md"
          >
            <RefreshCw className="w-4 h-4" />
            Clear Completed ({statistics.completed})
          </button>
        )}

        {/* Clear failed button */}
        {statistics.failed > 0 && (
          <button
            onClick={onClearFailed}
            className="px-3 py-1.5 text-sm font-medium text-card-foreground/80 hover:bg-muted/40 border border-border/80 rounded-xl shadow-sm bg-card transition-all flex items-center gap-2 hover:shadow-md"
          >
            <RefreshCw className="w-4 h-4" />
            Clear Failed ({statistics.failed})
          </button>
        )}

        {/* Clear cancelled button */}
        {statistics.cancelled > 0 && (
          <button
            onClick={onClearCancelled}
            className="px-3 py-1.5 text-sm font-medium text-card-foreground/80 hover:bg-muted/40 border border-border/80 rounded-xl shadow-sm bg-card transition-all flex items-center gap-2 hover:shadow-md"
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
