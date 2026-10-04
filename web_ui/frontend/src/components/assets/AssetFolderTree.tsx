'use client';

/**
 * Recursive folder tree for the asset library sidebar.
 * Nodes are always expandable to their own path; ancestors of the selected
 * path are auto-expanded.
 */
import { useMemo, useState } from 'react';
import { ChevronRight, ChevronDown, Folder, Pencil, FolderInput, Trash2, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { AssetTreeNode } from '@/types';

interface AssetFolderTreeProps {
  nodes: AssetTreeNode[];
  selectedPath: string;
  onSelect: (path: string) => void;
  depth?: number;
  onAddSub?: (node: AssetTreeNode) => void;
  onRename?: (node: AssetTreeNode) => void;
  onMove?: (node: AssetTreeNode) => void;
  onDelete?: (node: AssetTreeNode) => void;
  onDropAsset?: (ref: string, targetPath: string) => void;
}

export default function AssetFolderTree({
  nodes,
  selectedPath,
  onSelect,
  depth = 0,
  onAddSub,
  onRename,
  onMove,
  onDelete,
  onDropAsset,
}: AssetFolderTreeProps) {
  const [manualExpanded, setManualExpanded] = useState<Set<string>>(new Set());
  const [dragOverPath, setDragOverPath] = useState<string | null>(null);

  // Ancestors of the selection are always expanded
  const autoExpanded = useMemo(() => {
    const set = new Set<string>();
    const parts = selectedPath.split('/').filter(Boolean);
    for (let i = 1; i < parts.length; i++) set.add(parts.slice(0, i).join('/'));
    return set;
  }, [selectedPath]);

  const toggle = (path: string) => {
    setManualExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  return (
    <div className={cn(depth > 0 && 'ml-3 border-l border-border/60 pl-1')}>
      {nodes.map((node) => {
        const hasChildren = node.children.length > 0;
        const expanded = manualExpanded.has(node.path) || autoExpanded.has(node.path);
        const isSelected = node.path === selectedPath;
        return (
          <div key={node.path}>
            <div
              className={cn(
                'group/row flex items-center gap-1 rounded-md px-1.5 py-1 text-sm cursor-pointer hover:bg-muted',
                isSelected && 'bg-muted font-medium text-primary',
                dragOverPath === node.path && 'ring-2 ring-primary/50 bg-primary/10'
              )}
              onClick={() => onSelect(node.path)}
              onDragOver={(e) => {
                if (!onDropAsset) return;
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                setDragOverPath(node.path);
              }}
              onDragLeave={() => setDragOverPath((cur) => (cur === node.path ? null : cur))}
              onDrop={(e) => {
                if (!onDropAsset) return;
                e.preventDefault();
                setDragOverPath(null);
                const ref = e.dataTransfer.getData('text/plain');
                if (ref) onDropAsset(ref, node.path);
              }}
            >
              <button
                className="p-0.5 shrink-0 text-muted-foreground hover:text-foreground"
                onClick={(e) => {
                  e.stopPropagation();
                  if (hasChildren) toggle(node.path);
                }}
              >
                {hasChildren ? (
                  expanded ? (
                    <ChevronDown className="w-3.5 h-3.5" />
                  ) : (
                    <ChevronRight className="w-3.5 h-3.5" />
                  )
                ) : (
                  <span className="inline-block w-3.5 h-3.5" />
                )}
              </button>
              <Folder className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
              <span className="truncate">{node.name}</span>
              {node.count > 0 && (
                <span className="ml-auto text-[10px] text-muted-foreground shrink-0 group-hover/row:hidden">
                  {node.count}
                </span>
              )}
              {(onAddSub || (depth > 0 && (onRename || onMove || onDelete))) && (
                <span className="ml-auto hidden group-hover/row:flex items-center gap-0.5 shrink-0">
                  {onAddSub && (
                    <button
                      className="p-0.5 text-muted-foreground hover:text-foreground"
                      title="Add subcategory"
                      onClick={(e) => {
                        e.stopPropagation();
                        onAddSub(node);
                      }}
                    >
                      <Plus className="w-3 h-3" />
                    </button>
                  )}
                  {depth > 0 && onRename && (
                    <button
                      className="p-0.5 text-muted-foreground hover:text-foreground"
                      title="Rename category"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRename(node);
                      }}
                    >
                      <Pencil className="w-3 h-3" />
                    </button>
                  )}
                  {onMove && (
                    <button
                      className="p-0.5 text-muted-foreground hover:text-foreground"
                      title="Move category"
                      onClick={(e) => {
                        e.stopPropagation();
                        onMove(node);
                      }}
                    >
                      <FolderInput className="w-3 h-3" />
                    </button>
                  )}
                  {onDelete && (
                    <button
                      className="p-0.5 text-muted-foreground hover:text-red-500"
                      title="Delete category"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDelete(node);
                      }}
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  )}
                </span>
              )}
            </div>
            {hasChildren && expanded && (
              <AssetFolderTree
                nodes={node.children}
                selectedPath={selectedPath}
                onSelect={onSelect}
                depth={depth + 1}
                onAddSub={onAddSub}
                onRename={onRename}
                onMove={onMove}
                onDelete={onDelete}
                onDropAsset={onDropAsset}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
