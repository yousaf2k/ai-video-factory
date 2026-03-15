/**
 * Queue Page - Main queue view with flat/grouped toggle
 */
'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useQueue } from '../../hooks/useQueue';
import { QueueItem, QueueItemStatus, GenerationType, ViewMode } from '../../types';
import QueueHeader from '../../components/queue/QueueHeader';
import QueueList from '../../components/queue/QueueList';
import ProjectGroup from '../../components/queue/ProjectGroup';
import { Loader2 } from 'lucide-react';

export default function QueuePage() {
  const {
    items,
    statistics,
    isPaused,
    isLoading,
    wsConnected,
    pauseQueue,
    resumeQueue,
    cancelItem,
    cancelMultipleItems,
    clearCompleted,
    clearFailed,
    clearCancelled,
    reorderItems,
    requeueItem,
    refetch
  } = useQueue({ enabled: true });

  const [viewMode, setViewMode] = useState<ViewMode>('flat');
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [statusFilter, setStatusFilter] = useState<string>('queued');
  const [typeFilter, setTypeFilter] = useState<string>('all');

  // Load view mode preference from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('queue-view-mode');
    if (saved === 'flat' || saved === 'grouped') {
      setViewMode(saved);
    }
  }, []);

  // Save view mode preference to localStorage
  useEffect(() => {
    localStorage.setItem('queue-view-mode', viewMode);
  }, [viewMode]);

  // Filter items based on selected filters
  const displayItems = useMemo(() => {
    return items.filter(item => {
      // Status filter
      if (statusFilter !== 'all' && item.status !== statusFilter) {
        return false;
      }

      // Type filter
      if (typeFilter !== 'all') {
        const isImage = [GenerationType.IMAGE, GenerationType.THEN_IMAGE, GenerationType.NOW_IMAGE].includes(item.generation_type);
        const isVideo = [GenerationType.VIDEO, GenerationType.MEETING_VIDEO, GenerationType.DEPARTURE_VIDEO].includes(item.generation_type);

        if (typeFilter === 'image' && !isImage) return false;
        if (typeFilter === 'video' && !isVideo) return false;
        if (typeFilter === 'narration' && item.generation_type !== GenerationType.NARRATION) return false;
        if (typeFilter === 'background' && item.generation_type !== GenerationType.BACKGROUND) return false;
      }

      return true;
    });
  }, [items, statusFilter, typeFilter]);

  // Group items by project for grouped view
  const groupedItems = useMemo(() => {
    const groups: Map<string, QueueItem[]> = new Map();

    displayItems.forEach((item) => {
      if (!groups.has(item.project_id)) {
        groups.set(item.project_id, []);
      }
      groups.get(item.project_id)!.push(item);
    });

    return Array.from(groups.entries()).map(([projectId, projectItems]) => ({
      projectId,
      projectTitle: projectItems[0]?.project_title || projectId,
      items: projectItems
    }));
  }, [displayItems]);

  const handleSelectAll = () => {
    const allIds = new Set(displayItems.map(item => item.item_id));
    setSelectedItems(allIds);
  };

  const handleDeselectAll = () => {
    setSelectedItems(new Set());
  };

  const handleToggleSelect = (itemId: string) => {
    const newSelected = new Set(selectedItems);
    if (newSelected.has(itemId)) {
      newSelected.delete(itemId);
    } else {
      newSelected.add(itemId);
    }
    setSelectedItems(newSelected);
  };

  const handleCancelSelected = () => {
    if (selectedItems.size === 0) return;

    if (confirm(`Are you sure you want to cancel ${selectedItems.size} item(s)?`)) {
      cancelMultipleItems(Array.from(selectedItems));
      setSelectedItems(new Set());
    }
  };

  const handleClearCompleted = () => {
    if (statistics.completed === 0) return;

    if (confirm(`Are you sure you want to clear ${statistics.completed} completed item(s)?`)) {
      clearCompleted();
    }
  };

  const handleClearFailed = () => {
    if (statistics.failed === 0) return;

    if (confirm(`Are you sure you want to clear ${statistics.failed} failed item(s)?`)) {
      clearFailed();
    }
  };

  const handleClearCancelled = () => {
    if (statistics.cancelled === 0) return;

    if (confirm(`Are you sure you want to clear ${statistics.cancelled} cancelled item(s)?`)) {
      clearCancelled();
    }
  };

  const handlePauseResume = () => {
    if (isPaused) {
      resumeQueue();
    } else {
      pauseQueue();
    }
  };

  const handleReorder = (itemIds: string[]) => {
    reorderItems(itemIds);
  };

  const handleCancelItem = (itemId: string) => {
    if (confirm('Are you sure you want to cancel this item?')) {
      cancelItem(itemId);
      selectedItems.delete(itemId);
    }
  };

  const handleRequeueItem = (itemId: string) => {
    requeueItem(itemId);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-gray-600">Loading queue...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <QueueHeader
        statistics={statistics}
        isPaused={isPaused}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        selectedCount={selectedItems.size}
        totalCount={displayItems.length}
        isAllSelected={selectedItems.size === displayItems.length && displayItems.length > 0}
        onSelectAll={handleSelectAll}
        onDeselectAll={handleDeselectAll}
        onCancelSelected={handleCancelSelected}
        onClearCompleted={handleClearCompleted}
        onClearFailed={handleClearFailed}
        onClearCancelled={handleClearCancelled}
        onPauseResume={handlePauseResume}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        typeFilter={typeFilter}
        onTypeFilterChange={setTypeFilter}
        wsConnected={wsConnected}
      />

      {/* Queue content */}
      <div className="p-4">
        {displayItems.length === 0 ? (
          /* Empty state */
          <div className="bg-white rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
            <div className="max-w-md mx-auto">
              <h3 className="text-lg font-medium text-gray-900 mb-2">Queue is empty</h3>
              <p className="text-gray-500">
                No items in the generation queue. Queue shots or videos from a project to see them here.
              </p>
            </div>
          </div>
        ) : viewMode === 'flat' ? (
          /* Flat view */
          <QueueList
            items={displayItems}
            selectedItems={selectedItems}
            onSelectItem={handleToggleSelect}
            onCancelItem={handleCancelItem}
            onRequeueItem={handleRequeueItem}
            onReorder={handleReorder}
          />
        ) : (
          /* Grouped view */
          <div className="space-y-4">
            {groupedItems.map(({ projectId, projectTitle, items }) => (
              <ProjectGroup
                key={projectId}
                projectId={projectId}
                projectTitle={projectTitle}
                items={items}
                selectedItems={selectedItems}
                onSelectItem={handleToggleSelect}
                onCancelItem={handleCancelItem}
                onRequeueItem={handleRequeueItem}
                onReorder={handleReorder}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
