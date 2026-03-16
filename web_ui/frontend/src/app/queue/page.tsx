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
import { Loader2, ChevronLeft, ChevronRight, X } from 'lucide-react';
import { ConfirmDialog, useConfirmDialog } from '../../components/ui/confirm-dialog';

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
    clearMultipleItems,
    clearCompleted,
    clearFailed,
    clearCancelled,
    reorderItems,
    requeueItem,
    refetch
  } = useQueue({ enabled: true });

  const { showDialog, dialogProps } = useConfirmDialog();

  const [viewMode, setViewMode] = useState<ViewMode>('flat');
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [mounted, setMounted] = useState(false);

  // Compute selected items statistics
  const selectedItemsList = useMemo(() => {
    return items.filter(item => selectedItems.has(item.item_id));
  }, [items, selectedItems]);

  const hasCancellableSelected = useMemo(() => {
    return selectedItemsList.some(item => 
      item.status === QueueItemStatus.QUEUED || item.status === QueueItemStatus.ACTIVE
    );
  }, [selectedItemsList]);

  const hasClearableSelected = useMemo(() => {
    return selectedItemsList.some(item => 
      item.status === QueueItemStatus.COMPLETED || 
      item.status === QueueItemStatus.FAILED || 
      item.status === QueueItemStatus.CANCELLED
    );
  }, [selectedItemsList]);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  // Load preferences from localStorage
  useEffect(() => {
    setMounted(true);
    const savedView = localStorage.getItem('queue-view-mode');
    if (savedView === 'flat' || savedView === 'grouped') {
      setViewMode(savedView);
    }

    const savedStatus = localStorage.getItem('queue-status-filter');
    if (savedStatus) {
      setStatusFilter(savedStatus);
    }

    const savedType = localStorage.getItem('queue-type-filter');
    if (savedType) {
      setTypeFilter(savedType);
    }
  }, []);

  // Save preferences to localStorage
  useEffect(() => {
    if (!mounted) return;
    localStorage.setItem('queue-view-mode', viewMode);
  }, [viewMode, mounted]);

  useEffect(() => {
    if (!mounted) return;
    localStorage.setItem('queue-status-filter', statusFilter);
  }, [statusFilter, mounted]);

  useEffect(() => {
    if (!mounted) return;
    localStorage.setItem('queue-type-filter', typeFilter);
  }, [typeFilter, mounted]);


  // Filter items based on selected filters
  const displayItems = useMemo(() => {
    return items.filter(item => {
      // Status filter
      if (statusFilter !== 'all') {
        if (statusFilter === 'active_queued') {
          if (item.status !== QueueItemStatus.ACTIVE && item.status !== QueueItemStatus.QUEUED) {
            return false;
          }
        } else if (item.status !== statusFilter) {
          return false;
        }
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

    // Filter display items that can have pictures
  const imageItems = useMemo(() => {
    return displayItems.filter(item => 
      item.shot_index && item.project_id &&
      [GenerationType.IMAGE, GenerationType.THEN_IMAGE, GenerationType.NOW_IMAGE].includes(item.generation_type)
    );
  }, [displayItems]);

  const handleImageClick = (itemId: string) => {
    const idx = imageItems.findIndex(i => i.item_id === itemId);
    if (idx !== -1) setLightboxIndex(idx);
  };

  const currentLightboxImage = lightboxIndex !== null ? imageItems[lightboxIndex] : null;

  const getLightboxImageUrl = (item: QueueItem) => {
    if (!item.shot_index || !item.project_id) return '';
    const padded = String(item.shot_index).padStart(3, '0');
    if (item.generation_type === GenerationType.THEN_IMAGE) {
      return `/api/projects/${item.project_id}/images/shot_${padded}_then_001.png`;
    }
    if (item.generation_type === GenerationType.NOW_IMAGE) {
      return `/api/projects/${item.project_id}/images/shot_${padded}_now_001.png`;
    }
    return `/api/projects/${item.project_id}/images/shot_${padded}_001.png`;
  };

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

    const handleClearSelected = async () => {
    if (selectedItems.size === 0) return;

    const confirmed = await showDialog({
      title: "Clear Selected Items",
      description: `Are you sure you want to remove ${selectedItems.size} selected item(s) from the queue?`,
      type: "delete",
      confirmText: "Clear Items",
    });

    if (confirmed) {
      clearMultipleItems(Array.from(selectedItems));
      setSelectedItems(new Set());
    }
  };

  const handleCancelSelected = async () => {
    if (selectedItems.size === 0) return;

    const confirmed = await showDialog({
      title: "Cancel Items",
      description: `Are you sure you want to cancel ${selectedItems.size} item(s)?`,
      type: "delete",
      confirmText: "Cancel Items",
    });

    if (confirmed) {
      cancelMultipleItems(Array.from(selectedItems));
      setSelectedItems(new Set());
    }
  };

  const handleClearCompleted = async () => {
    if (statistics.completed === 0) return;

    const confirmed = await showDialog({
      title: "Clear Completed",
      description: `Are you sure you want to clear ${statistics.completed} completed item(s)?`,
      type: "delete",
      confirmText: "Clear",
    });

    if (confirmed) {
      clearCompleted();
    }
  };

  const handleClearFailed = async () => {
    if (statistics.failed === 0) return;

    const confirmed = await showDialog({
      title: "Clear Failed",
      description: `Are you sure you want to clear ${statistics.failed} failed item(s)?`,
      type: "delete",
      confirmText: "Clear",
    });

    if (confirmed) {
      clearFailed();
    }
  };

  const handleClearCancelled = async () => {
    if (statistics.cancelled === 0) return;

    const confirmed = await showDialog({
      title: "Clear Cancelled",
      description: `Are you sure you want to clear ${statistics.cancelled} cancelled item(s)?`,
      type: "delete",
      confirmText: "Clear",
    });

    if (confirmed) {
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

  const handleCancelItem = async (itemId: string) => {
    const confirmed = await showDialog({
      title: "Cancel Item",
      description: "Are you sure you want to cancel this item?",
      type: "delete",
      confirmText: "Yes",
    });

    if (confirmed) {
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
    <div className="min-h-screen bg-background relative">
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-colors-blue-50),_transparent_50%)] -z-10" />
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_bottom_left,_var(--tw-colors-purple-50),_transparent_40%)] -z-10" />
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
        onClearSelected={handleClearSelected}
        hasCancellableSelected={hasCancellableSelected}
        hasClearableSelected={hasClearableSelected}
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
          <div className="bg-card/50 backdrop-blur-sm rounded-xl border border-dashed border-border p-12 text-center">
            <div className="max-w-md mx-auto">
              <h3 className="text-lg font-medium text-foreground mb-2">Queue is empty</h3>
              <p className="text-muted-foreground">
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
            onImageClick={handleImageClick}
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
                onImageClick={handleImageClick}
              />
            ))}
          </div>
        )}
      </div>
      
      {/* Lightbox Slideshow for Queue Page */}
      {currentLightboxImage && (
        <div className="fixed inset-0 z-[100] bg-black/95 flex flex-col items-center justify-center animate-in fade-in-0 duration-200 p-4">
          <button 
            onClick={() => setLightboxIndex(null)} 
            className="absolute top-4 right-4 text-white/70 hover:text-white p-2 rounded-full hover:bg-white/10 transition-colors z-10"
          >
            <X className="w-6 h-6" />
          </button>

          {lightboxIndex! > 0 && (
            <button 
              onClick={() => setLightboxIndex(lightboxIndex! - 1)} 
              className="absolute left-6 text-white/70 hover:text-white p-3 rounded-full hover:bg-white/10 transition-colors z-10"
            >
              <ChevronLeft className="w-8 h-8" />
            </button>
          )}

          <div className="relative aspect-video w-full max-w-6xl max-h-[80vh] flex items-center justify-center bg-black/40 rounded-lg overflow-hidden border border-border/40">
            <img 
              src={getLightboxImageUrl(currentLightboxImage)} 
              alt={`Shot ${currentLightboxImage.shot_index}`} 
              className="w-full h-full object-contain select-none" 
              onError={(e) => {
                (e.target as HTMLImageElement).src = '/api/placeholder/1920/1080?text=Image+Not+Found';
              }}
            />
          </div>
          
          <div className="mt-4 text-white text-center">
            <span className="font-semibold">{currentLightboxImage.project_title || currentLightboxImage.project_id}</span>
            <div className="text-xs text-white/60 mt-1">Shot {currentLightboxImage.shot_index} ({currentLightboxImage.generation_type.replace('_', ' ')})</div>
            <div className="text-xs text-white/40 mt-1">{lightboxIndex! + 1} of {imageItems.length}</div>
          </div>

          {lightboxIndex! < imageItems.length - 1 && (
            <button 
              onClick={() => setLightboxIndex(lightboxIndex! + 1)} 
              className="absolute right-6 text-white/70 hover:text-white p-3 rounded-full hover:bg-white/10 transition-colors z-10"
            >
              <ChevronRight className="w-8 h-8" />
            </button>
          )}
        </div>
      )}

      <ConfirmDialog {...dialogProps} />
    </div>
  );
}
