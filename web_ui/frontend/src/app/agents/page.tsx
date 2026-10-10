/**
 * Agents Management Page
 *
 * Three-pane editor: pick an agent type + category, pick a file
 * (agents or base/component files), edit its raw markdown.
 * Raw content keeps {{include:...}} directives intact on save.
 */
"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import { toast } from "sonner";
import {
  useAgentTree,
  useAgentContent,
  useUpdateAgentContent,
} from "@/hooks/useAgents";
import type { AgentCategory, AgentFileRef, AgentTree } from "@/types";
import {
  Save,
  RotateCcw,
  FileText,
  FileCode2,
  ChevronRight,
  Eye,
  Code,
  Layers,
  Search,
  CircleDot,
  FolderOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";

type AgentType = "story" | "shots";
type SelectedFile = { type: AgentType; file: AgentFileRef };

const GROUP_LABELS: Record<string, string> = {
  _base: "Base",
  _contexts: "Contexts",
  _styles: "Styles",
  base: "Base",
  common: "Common",
  _root: "Root files",
};

function groupLabel(group?: string): string {
  if (!group) return "Base Files";
  return GROUP_LABELS[group] ?? group.replace(/^_/, "").replace(/_/g, " ");
}

/** Find a file in the tree by bare include name (e.g. "base_standard"). */
function findIncludeTarget(
  tree: AgentTree | undefined,
  type: AgentType,
  includeName: string
): { category: AgentCategory; file: AgentFileRef } | null {
  const cats = tree?.[type] ?? [];
  for (const cat of cats) {
    for (const f of [...cat.agents, ...cat.base_files]) {
      if (f.id === includeName || f.name === includeName) return { category: cat, file: f };
    }
  }
  // Try suffix match (include may omit the category)
  for (const cat of cats) {
    for (const f of [...cat.agents, ...cat.base_files]) {
      if (f.id.endsWith(`/${includeName}`)) return { category: cat, file: f };
    }
  }
  return null;
}

export default function AgentsPage() {
  const { data: tree, isLoading: isLoadingTree } = useAgentTree();

  const [agentType, setAgentType] = useState<AgentType>("story");
  const [selectedCatId, setSelectedCatId] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<SelectedFile | null>(null);
  const [search, setSearch] = useState("");
  const [showPreview, setShowPreview] = useState(false);

  // Drafts keep unsaved edits alive while switching between files
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [editContent, setEditContent] = useState("");

  const categories = tree?.[agentType] ?? [];
  const selectedCat =
    categories.find((c) => c.id === selectedCatId) ?? null;

  const fileKey = selectedFile ? `${selectedFile.type}/${selectedFile.file.id}` : null;

  const {
    data: fileData,
    isLoading: isLoadingContent,
  } = useAgentContent(selectedFile?.type ?? null, selectedFile?.file.id ?? null);

  const serverContent = fileData?.content;
  const includes = useMemo(
    () => (selectedFile ? fileData?.includes ?? [] : []),
    [fileData, selectedFile]
  );

  const updateMutation = useUpdateAgentContent(
    selectedFile?.type ?? "",
    selectedFile?.file.id ?? ""
  );

  const dirty = selectedFile != null && serverContent !== undefined && editContent !== serverContent;

  // Default category whenever the type changes / tree arrives
  useEffect(() => {
    if (categories.length === 0) return;
    if (!categories.some((c) => c.id === selectedCatId)) {
      setSelectedCatId(categories[0].id);
    }
  }, [agentType, tree]); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync editor content: prefer a saved draft for this file, else server content
  useEffect(() => {
    if (serverContent === undefined || !fileKey) return;
    setEditContent(drafts[fileKey] ?? serverContent);
  }, [serverContent, fileKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // Warn before leaving with unsaved changes
  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  const handleSelectFile = (file: AgentFileRef) => {
    if (selectedFile && dirty && file.id !== selectedFile.file.id) {
      // Draft is kept in `drafts`, so nothing is lost - just inform
      toast.info("Unsaved changes kept as draft", {
        description: `${selectedFile.file.name}.md has unsaved edits.`,
      });
    }
    setShowPreview(false);
    setSelectedFile({ type: agentType, file });
  };

  const handleChange = (value: string) => {
    setEditContent(value);
    if (fileKey) setDrafts((d) => ({ ...d, [fileKey]: value }));
  };

  const handleSave = useCallback(async () => {
    if (!selectedFile || !dirty || updateMutation.isPending) return;
    try {
      await updateMutation.mutateAsync(editContent);
      setDrafts((d) => {
        const next = { ...d };
        delete next[fileKey!];
        return next;
      });
      toast.success(`${selectedFile.file.name}.md saved`);
    } catch (error) {
      console.error("Failed to update agent:", error);
      toast.error("Failed to save agent file.");
    }
  }, [selectedFile, dirty, editContent, fileKey, updateMutation]);

  const handleRevert = () => {
    if (!selectedFile || serverContent === undefined) return;
    setDrafts((d) => {
      const next = { ...d };
      delete next[fileKey!];
      return next;
    });
    setEditContent(serverContent);
  };

  // Ctrl/Cmd+S saves
  const saveRef = useRef(handleSave);
  saveRef.current = handleSave;
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        saveRef.current();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Filtered files for the current category
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    const match = (f: AgentFileRef) =>
      !q || f.name.toLowerCase().includes(q) || f.id.toLowerCase().includes(q);
    if (!selectedCat) return null;
    const agents = selectedCat.agents.filter(match);
    const baseFiles = selectedCat.base_files.filter(match);
    // Group base files by their group subdir
    const groups = new Map<string, AgentFileRef[]>();
    for (const f of baseFiles) {
      const g = f.group ?? "_base";
      if (!groups.has(g)) groups.set(g, []);
      groups.get(g)!.push(f);
    }
    return { agents, groups };
  }, [selectedCat, search]);

  const isLoadingFile = isLoadingContent && selectedFile != null;

  if (isLoadingTree) {
    return <div className="container mx-auto px-4 py-8">Loading agents...</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">AI Agents</h1>
        <p className="text-muted-foreground">
          Pick a category, then a file to edit. Base/component files are editable too.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[230px_280px_1fr] gap-4 h-auto lg:h-[calc(100vh-230px)]">
        {/* Pane 1: Type + Categories */}
        <div className="border rounded-lg overflow-hidden flex flex-col lg:h-full max-h-[40vh] lg:max-h-none">
          <div className="p-2 border-b bg-muted/50">
            <div className="grid grid-cols-2 gap-1 bg-card border rounded-md p-1">
              {(["story", "shots"] as AgentType[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setAgentType(t)}
                  className={cn(
                    "px-3 py-1.5 text-sm rounded-sm capitalize transition-colors",
                    agentType === t
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted"
                  )}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div className="overflow-y-auto flex-1 p-1">
            {categories.length === 0 && (
              <p className="text-sm text-muted-foreground p-3">No categories.</p>
            )}
            {categories.map((cat) => {
              const total = cat.agents.length + cat.base_files.length;
              const active = selectedCatId === cat.id;
              return (
                <button
                  key={cat.id}
                  onClick={() => {
                    setSelectedCatId(cat.id);
                    setSearch("");
                  }}
                  className={cn(
                    "w-full text-left px-3 py-2 rounded-md text-sm flex items-center gap-2 transition-colors",
                    active ? "bg-primary text-primary-foreground" : "hover:bg-muted"
                  )}
                >
                  {cat.is_base ? (
                    <Layers className="w-4 h-4 shrink-0 opacity-70" />
                  ) : (
                    <FolderOpen className="w-4 h-4 shrink-0 opacity-70" />
                  )}
                  <span className="truncate flex-1">{cat.name}</span>
                  {cat.is_base && (
                    <span
                      className={cn(
                        "text-[10px] uppercase tracking-wide",
                        active ? "text-primary-foreground/80" : "text-muted-foreground"
                      )}
                    >
                      base
                    </span>
                  )}
                  <span
                    className={cn(
                      "text-xs rounded-full px-1.5 py-0.5",
                      active ? "bg-primary-foreground/20" : "bg-muted text-muted-foreground"
                    )}
                  >
                    {total}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Pane 2: Files in category */}
        <div className="border rounded-lg overflow-hidden flex flex-col lg:h-full max-h-[50vh] lg:max-h-none">
          <div className="p-2 border-b bg-muted/50 space-y-2">
            <div className="text-sm font-semibold px-1 truncate">
              {selectedCat ? selectedCat.name : "Files"}
            </div>
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Filter files..."
                className="h-8 pl-8 text-sm bg-card"
              />
            </div>
          </div>
          <div className="overflow-y-auto flex-1 p-1">
            {!selectedCat || !filtered ? (
              <p className="text-sm text-muted-foreground p-3">Select a category.</p>
            ) : filtered.agents.length === 0 && filtered.groups.size === 0 ? (
              <p className="text-sm text-muted-foreground p-3">No files match.</p>
            ) : (
              <>
                {filtered.agents.length > 0 && (
                  <>
                    <div className="px-2 pt-1 pb-1 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                      Agents ({filtered.agents.length})
                    </div>
                    {filtered.agents.map((f) => (
                      <FileRow
                        key={f.id}
                        file={f}
                        selected={
                          selectedFile?.file.id === f.id && selectedFile.type === agentType
                        }
                        dirty={!!drafts[`${agentType}/${f.id}`]}
                        onSelect={() => handleSelectFile(f)}
                      />
                    ))}
                  </>
                )}
                {filtered.groups.size > 0 && (
                  <>
                    <div className="px-2 pt-3 pb-1 text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                      <Layers className="w-3 h-3" />
                      Base Files
                    </div>
                    {[...filtered.groups.entries()].map(([group, files]) => (
                      <div key={group} className="mb-1">
                        {filtered.groups.size > 1 && (
                          <div className="px-3 py-1 text-xs text-muted-foreground">
                            {groupLabel(group)}
                          </div>
                        )}
                        {files.map((f) => (
                          <FileRow
                            key={f.id}
                            file={f}
                            selected={
                              selectedFile?.file.id === f.id && selectedFile.type === agentType
                            }
                            dirty={!!drafts[`${agentType}/${f.id}`]}
                            onSelect={() => handleSelectFile(f)}
                          />
                        ))}
                      </div>
                    ))}
                  </>
                )}
              </>
            )}
          </div>
        </div>

        {/* Pane 3: Editor */}
        <div className="border rounded-lg overflow-hidden flex flex-col lg:h-full min-h-[50vh] lg:min-h-0">
          {selectedFile ? (
            <>
              <div className="bg-muted/50 p-2 flex items-center justify-between gap-2 border-b flex-wrap">
                <div className="flex items-center gap-1.5 px-1 min-w-0">
                  {selectedFile.file.is_base ? (
                    <FileCode2 className="w-4 h-4 shrink-0 text-muted-foreground" />
                  ) : (
                    <FileText className="w-4 h-4 shrink-0 text-muted-foreground" />
                  )}
                  <span className="font-mono text-sm truncate">
                    <span className="text-muted-foreground">
                      {selectedFile.type} / {selectedFile.file.id}
                    </span>
                    .md
                  </span>
                  {selectedFile.file.is_base && (
                    <span className="text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                      base
                    </span>
                  )}
                  {dirty && (
                    <span
                      className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400"
                      title="Unsaved changes"
                    >
                      <CircleDot className="w-3 h-3" />
                      unsaved
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex bg-card border rounded-md p-1">
                    <button
                      onClick={() => setShowPreview(false)}
                      className={cn(
                        "px-3 py-1 text-xs rounded-sm flex items-center gap-1.5 transition-colors",
                        !showPreview
                          ? "bg-muted text-foreground"
                          : "text-muted-foreground hover:bg-muted/50"
                      )}
                    >
                      <Code className="w-3.5 h-3.5" />
                      Edit
                    </button>
                    <button
                      onClick={() => setShowPreview(true)}
                      className={cn(
                        "px-3 py-1 text-xs rounded-sm flex items-center gap-1.5 transition-colors",
                        showPreview
                          ? "bg-muted text-foreground"
                          : "text-muted-foreground hover:bg-muted/50"
                      )}
                    >
                      <Eye className="w-3.5 h-3.5" />
                      Preview
                    </button>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRevert}
                    disabled={!dirty}
                    className="flex items-center gap-1.5"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Revert
                  </Button>
                  <Button
                    onClick={handleSave}
                    disabled={!dirty || updateMutation.isPending || isLoadingContent}
                    size="sm"
                    className="flex items-center gap-1.5"
                  >
                    {updateMutation.isPending ? (
                      <>
                        <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="w-3.5 h-3.5" />
                        Save
                      </>
                    )}
                  </Button>
                </div>
              </div>

              {includes.length > 0 && (
                <div className="px-3 py-1.5 border-b bg-card flex items-center gap-1.5 flex-wrap text-xs">
                  <span className="text-muted-foreground">Includes:</span>
                  {includes.map((inc) => {
                    const target = findIncludeTarget(tree, selectedFile.type, inc);
                    return target ? (
                      <button
                        key={inc}
                        onClick={() => {
                          setSelectedCatId(target.category.id);
                          handleSelectFile(target.file);
                        }}
                        className="font-mono px-1.5 py-0.5 rounded bg-muted hover:bg-primary hover:text-primary-foreground transition-colors"
                        title={`Open ${target.file.id}.md`}
                      >
                        {inc}
                      </button>
                    ) : (
                      <span
                        key={inc}
                        className="font-mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground"
                      >
                        {inc}
                      </span>
                    );
                  })}
                </div>
              )}

              <div className="flex-1 relative overflow-hidden flex flex-col">
                {isLoadingFile ? (
                  <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10">
                    <RotateCcw className="w-6 h-6 animate-spin text-primary" />
                  </div>
                ) : showPreview ? (
                  <div className="flex-1 overflow-y-auto p-8 bg-card">
                    <div className="prose prose-sm prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {editContent}
                      </ReactMarkdown>
                    </div>
                  </div>
                ) : (
                  <Textarea
                    value={editContent}
                    onChange={(e) => handleChange(e.target.value)}
                    className="flex-1 w-full p-6 font-mono text-sm resize-none focus:outline-none bg-card rounded-none border-0 focus-visible:ring-0"
                    placeholder="Paste your agent prompt here..."
                    spellCheck={false}
                  />
                )}
              </div>

              <div className="bg-muted/50 p-3 text-xs text-muted-foreground flex justify-between gap-4 border-t flex-wrap">
                <span>
                  Tips: <code className="font-mono">{"{USER_INPUT}"}</code> inserts the user's
                  request · <code className="font-mono">{"{{include:path}}"}</code> composes shared
                  files · Ctrl+S saves
                </span>
                <span className="whitespace-nowrap">
                  {editContent.length.toLocaleString()} chars
                  {showPreview && " · Preview mode"}
                </span>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-12 text-center text-muted-foreground">
              <FileText className="w-12 h-12 mb-4 opacity-20" />
              <h3 className="text-lg font-medium mb-2">Select a File</h3>
              <p className="max-w-xs">
                Choose a category on the left, then pick an agent or base file to view and edit
                its prompt.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FileRow({
  file,
  selected,
  dirty,
  onSelect,
}: {
  file: AgentFileRef;
  selected: boolean;
  dirty: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      onClick={onSelect}
      className={cn(
        "w-full text-left px-3 py-1.5 rounded-md text-sm flex items-center gap-2 transition-colors group",
        selected ? "bg-primary text-primary-foreground" : "hover:bg-muted"
      )}
    >
      {file.is_base ? (
        <FileCode2
          className={cn(
            "w-3.5 h-3.5 shrink-0",
            selected ? "opacity-80" : "text-muted-foreground"
          )}
        />
      ) : (
        <FileText
          className={cn(
            "w-3.5 h-3.5 shrink-0",
            selected ? "opacity-80" : "text-muted-foreground"
          )}
        />
      )}
      <span className="truncate flex-1">{file.name}</span>
      {dirty ? (
        <span title="Unsaved changes">
          <CircleDot className="w-3 h-3 shrink-0 text-amber-500" />
        </span>
      ) : (
        <ChevronRight
          className={cn(
            "w-3.5 h-3.5 shrink-0 opacity-0 group-hover:opacity-50 transition-opacity",
            selected && "opacity-50"
          )}
        />
      )}
    </button>
  );
}
