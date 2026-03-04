/**
 * ShotGrid component - Grid view of shots with thumbnails and bulk actions
 */
import { useState, useCallback, useMemo, useEffect } from "react";
import { ShotCard } from "./ShotCard";
import { Shot } from "@/types";
import { useAgents } from "@/hooks/useAgents";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import { useUpdateShots } from "@/hooks/useShots";
import {
  CheckSquare,
  Square,
  Image as ImageIcon,
  Video,
  X,
  RotateCw,
  Search,
  Filter,
  XCircle,
  Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useProgress } from "@/hooks/useProgress";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ShotGridProps {
  shots: Shot[];
  sessionId: string;
}

export function ShotGrid({ shots, sessionId }: ShotGridProps) {
  const [selectedIndices, setSelectedIndices] = useState<number[]>([]);
  const [showBatchModal, setShowBatchModal] = useState<
    "image" | "video" | "both" | null
  >(null);
  const [generatingIndices, setGeneratingIndices] = useState<Set<number>>(
    new Set(),
  );
  const [queuedIndices, setQueuedIndices] = useState<Set<number>>(new Set());
  const queryClient = useQueryClient();
  const updateShotsMutation = useUpdateShots(sessionId);

  // Insert modal state
  const [insertModalConfig, setInsertModalConfig] = useState<{
    position: number;
  } | null>(null);
  const [newShotData, setNewShotData] = useState<Partial<Shot>>({
    image_prompt: "",
    motion_prompt: "",
    camera: "static",
    narration: "",
  });

  const { shotProgress } = useProgress(
    sessionId,
    useCallback(
      (shotId: string) => {
        // Whenever a WebSocket progress message broadcasts 'completed', refresh this session's UI!
        queryClient.invalidateQueries({ queryKey: ["shots", sessionId] });
        queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
      },
      [queryClient, sessionId],
    ),
  );

  // Filter state
  const [filterNoImages, setFilterNoImages] = useState(false);
  const [filterNoVideos, setFilterNoVideos] = useState(false);
  const [filterCamera, setFilterCamera] = useState<string>("");
  const [filterText, setFilterText] = useState<string>("");

  // Overrides state
  const [imageMode, setImageMode] = useState<string>("comfyui");
  const [imageWorkflow, setImageWorkflow] = useState<string>("flux2");
  const [videoWorkflow, setVideoWorkflow] = useState<string>(
    "workflow/video/wan22_workflow.json",
  );
  const [batchSkipImages, setBatchSkipImages] = useState<boolean>(true);

  const { data: agents } = useAgents();

  // Extract unique camera values for the dropdown
  const cameraOptions = useMemo(() => {
    const cameras = new Set(shots.map((s) => s.camera).filter(Boolean));
    return Array.from(cameras).sort();
  }, [shots]);

  // Apply filters
  const filteredShots = useMemo(() => {
    let result = shots;

    if (filterNoImages) {
      result = result.filter((s) => !s.image_generated);
    }
    if (filterNoVideos) {
      result = result.filter((s) => !s.video_rendered);
    }
    if (filterCamera) {
      result = result.filter((s) => s.camera === filterCamera);
    }
    if (filterText.trim()) {
      const q = filterText.trim().toLowerCase();
      result = result.filter((s) => {
        return (
          (s.image_prompt || "").toLowerCase().includes(q) ||
          (s.motion_prompt || "").toLowerCase().includes(q) ||
          (s.narration || "").toLowerCase().includes(q)
        );
      });
    }

    return result;
  }, [shots, filterNoImages, filterNoVideos, filterCamera, filterText]);

  const hasActiveFilters =
    filterNoImages || filterNoVideos || !!filterCamera || !!filterText.trim();

  if (shots.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No shots yet. Generate story and plan shots first.
      </div>
    );
  }

  const toggleSelectAll = () => {
    if (selectedIndices.length === filteredShots.length) {
      setSelectedIndices([]);
    } else {
      setSelectedIndices(filteredShots.map((s) => s.index));
    }
  };

  const toggleSelectShot = (index: number, selected: boolean) => {
    if (selected) {
      setSelectedIndices((prev) => [...prev, index]);
    } else {
      setSelectedIndices((prev) => prev.filter((i) => i !== index));
    }
  };

  const handleBatchSubmit = useCallback(async () => {
    if (selectedIndices.length === 0 || !showBatchModal) return;

    const indicesToProcess = [...selectedIndices];
    const type = showBatchModal;

    // Close modal and clear selection immediately
    setShowBatchModal(null);
    setSelectedIndices([]);

    // Mark all selected shots as generating
    setGeneratingIndices((prev) => {
      const next = new Set(prev);
      indicesToProcess.forEach((i) => next.add(i));
      return next;
    });

    if (type === "both") {
      try {
        await api.batchRegenerate(sessionId, {
          shot_indices: indicesToProcess,
          regenerate_images: true,
          regenerate_videos: true,
          force: !batchSkipImages,
          image_mode: imageMode,
          image_workflow: imageWorkflow,
          video_workflow: videoWorkflow,
        });
      } catch (error) {
        console.error("Failed to start batch both generation:", error);
      }
    } else if (type === "image") {
      try {
        await api.batchRegenerate(sessionId, {
          shot_indices: indicesToProcess,
          regenerate_images: true,
          regenerate_videos: false,
          force: true,
          image_mode: imageMode,
          image_workflow: imageWorkflow,
        });
      } catch (error) {
        console.error("Failed to start batch image generation:", error);
      }
    } else if (type === "video") {
      try {
        await api.batchRegenerate(sessionId, {
          shot_indices: indicesToProcess,
          regenerate_images: false,
          regenerate_videos: true,
          force: true,
          video_workflow: videoWorkflow,
        });
      } catch (error) {
        console.error("Failed to start batch video generation:", error);
      }
    }

    // Modal cleanup - the actual progress will be tracked organically via the WebSocket state we implemented
    setShowBatchModal(null);
    setSelectedIndices([]);
    setGeneratingIndices(new Set()); // Fallback visual clear, websocket will fill valid ones
    setQueuedIndices(new Set(indicesToProcess));

    // We optionally fetch the latest data just in case
    queryClient.invalidateQueries({ queryKey: ["shots", sessionId] });
    queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
  }, [
    selectedIndices,
    showBatchModal,
    sessionId,
    imageMode,
    imageWorkflow,
    videoWorkflow,
    queryClient,
    batchSkipImages,
  ]);

  // Remove shots from queued status once the backend confirms they started generating
  useEffect(() => {
    if (Object.keys(shotProgress).length > 0) {
      setQueuedIndices((prev) => {
        const next = new Set(prev);
        let changed = false;
        // shotProgress is keyed by shot_id, so we need to iterate all shots to find matches
        shots.forEach((shot) => {
          const key = shot.id || shot.index.toString();
          if (shotProgress[key] !== undefined && next.has(shot.index)) {
            next.delete(shot.index);
            changed = true;
          }
        });
        return changed ? next : prev;
      });
    }
  }, [shotProgress, shots]);

  // Request the backend queue status on initial load/mount to hydrate the UI after a page refresh
  useEffect(() => {
    const fetchQueueStatus = async () => {
      try {
        const data = await api.getQueueStatus(sessionId);
        if (data.queued_indices && data.queued_indices.length > 0) {
          setQueuedIndices(
            (prev) => new Set([...prev, ...data.queued_indices]),
          );
        }
      } catch (err) {
        console.error("Failed to fetch queue status:", err);
      }
    };
    fetchQueueStatus();
  }, [sessionId]);

  const handleCancelAll = useCallback(async () => {
    try {
      await api.cancelGeneration(sessionId);
      setGeneratingIndices(new Set());
      setQueuedIndices(new Set());
      queryClient.invalidateQueries({ queryKey: ["shots", sessionId] });
      queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
    } catch (error) {
      console.error("Failed to cancel generation:", error);
    }
  }, [sessionId, queryClient]);

  const handleCancelShot = useCallback(
    async (shotIndex: number) => {
      try {
        await api.cancelShotGeneration(sessionId, shotIndex);

        // Remove just this one shot from local sets
        setGeneratingIndices((prev) => {
          const next = new Set(prev);
          next.delete(shotIndex);
          return next;
        });
        setQueuedIndices((prev) => {
          const next = new Set(prev);
          next.delete(shotIndex);
          return next;
        });

        queryClient.invalidateQueries({ queryKey: ["shots", sessionId] });
      } catch (error) {
        console.error(`Failed to cancel shot ${shotIndex}:`, error);
      }
    },
    [sessionId, queryClient],
  );

  const handleDeleteShot = async (indexToRemove: number) => {
    if (
      !confirm(
        "Are you sure you want to delete this shot? This cannot be undone.",
      )
    )
      return;

    // Filter out the deleted shot
    const updatedShots = shots.filter((s) => s.index !== indexToRemove);

    // Re-index remaining shots cleanly 1..N
    const reindexedShots = updatedShots.map((s, idx) => ({
      ...s,
      index: idx + 1,
    }));

    try {
      await updateShotsMutation.mutateAsync(reindexedShots);
    } catch (error) {
      console.error("Failed to delete shot:", error);
      alert("Failed to delete shot. Please try again.");
    }
  };

  const handleInsertShot = async () => {
    if (!insertModalConfig) return;

    // Build a clean default shot
    const defaultShot: Shot = {
      index: 0, // Temporarily 0, will be overwritten by re-indexing below
      image_prompt: newShotData.image_prompt || "",
      motion_prompt: newShotData.motion_prompt || "",
      camera: newShotData.camera || "static",
      narration: newShotData.narration || "",
      batch_number: 1,
      image_generated: false,
      video_rendered: false,
      image_path: null,
      image_paths: [],
      video_path: null,
    };

    // Slice the array and insert exactly at position
    const pos = insertModalConfig.position;
    const newShotsList = [
      ...shots.slice(0, pos),
      defaultShot,
      ...shots.slice(pos),
    ];

    // Re-index cleanly 1..N
    const reindexedShots = newShotsList.map((s, idx) => ({
      ...s,
      index: idx + 1,
    }));

    try {
      await updateShotsMutation.mutateAsync(reindexedShots);
      setInsertModalConfig(null);
      setNewShotData({
        image_prompt: "",
        motion_prompt: "",
        camera: "static",
        narration: "",
      });
    } catch (error) {
      console.error("Failed to insert shot:", error);
      alert("Failed to insert shot. Please try again.");
    }
  };

  return (
    <div className="relative">
      {/* Header Actions */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <button
            onClick={() =>
              setSelectedIndices(filteredShots.map((s) => s.index))
            }
            className="flex items-center gap-1.5 text-sm px-2.5 py-1 border rounded-md hover:bg-muted transition-colors"
          >
            <CheckSquare className="w-3.5 h-3.5" />
            Select All
          </button>
          <button
            onClick={() => setSelectedIndices([])}
            disabled={selectedIndices.length === 0}
            className="flex items-center gap-1.5 text-sm px-2.5 py-1 border rounded-md hover:bg-muted transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Square className="w-3.5 h-3.5" />
            Select None
          </button>
          {selectedIndices.length > 0 && (
            <span className="text-xs text-muted-foreground ml-1">
              {selectedIndices.length} of {shots.length} selected
            </span>
          )}
        </div>
        {(generatingIndices.size > 0 ||
          Object.keys(shotProgress).length > 0) && (
          <button
            onClick={handleCancelAll}
            className="flex items-center gap-1.5 text-sm px-3 py-1.5 border border-red-300 text-red-600 rounded-md hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          >
            <XCircle className="w-4 h-4" />
            Cancel All Generation
          </button>
        )}
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-2 mb-4 p-3 bg-muted/40 rounded-lg border">
        <Filter className="w-4 h-4 text-muted-foreground shrink-0" />

        <button
          onClick={() => setFilterNoImages((v) => !v)}
          className={cn(
            "flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-full border transition-colors",
            filterNoImages
              ? "bg-orange-100 border-orange-300 text-orange-700 dark:bg-orange-900/30 dark:border-orange-700 dark:text-orange-400"
              : "hover:bg-muted",
          )}
        >
          <ImageIcon className="w-3 h-3" />
          No Images
        </button>

        <button
          onClick={() => setFilterNoVideos((v) => !v)}
          className={cn(
            "flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-full border transition-colors",
            filterNoVideos
              ? "bg-purple-100 border-purple-300 text-purple-700 dark:bg-purple-900/30 dark:border-purple-700 dark:text-purple-400"
              : "hover:bg-muted",
          )}
        >
          <Video className="w-3 h-3" />
          No Videos
        </button>

        <Select
          value={filterCamera}
          onValueChange={(val) => setFilterCamera(val === "all" ? "" : val)}
        >
          <SelectTrigger className="w-[140px] h-8 text-xs rounded-full bg-background border">
            <SelectValue placeholder="All Cameras" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Cameras</SelectItem>
            {cameraOptions.map((cam) => (
              <SelectItem key={cam} value={cam}>
                {cam}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <div className="relative flex-1 min-w-[180px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input
            type="text"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            placeholder="Search prompts & narration..."
            className="pl-8 h-8 text-xs rounded-full"
          />
        </div>

        {hasActiveFilters && (
          <button
            onClick={() => {
              setFilterNoImages(false);
              setFilterNoVideos(false);
              setFilterCamera("");
              setFilterText("");
            }}
            className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-full border text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          >
            <X className="w-3 h-3" />
            Clear
          </button>
        )}

        <span className="text-xs text-muted-foreground ml-auto">
          {filteredShots.length} of {shots.length} shots
        </span>
      </div>

      {/* Floating Bulk Actions Bar */}
      <div
        className={cn(
          "fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-background border shadow-lg rounded-full px-6 py-3 flex items-center gap-4 transition-all duration-300",
          selectedIndices.length > 0
            ? "translate-y-0 opacity-100"
            : "translate-y-16 opacity-0 pointer-events-none",
        )}
      >
        <span className="text-sm font-medium border-r pr-4">
          {selectedIndices.length} shots selected
        </span>
        <button
          onClick={() => setShowBatchModal("image")}
          className="flex items-center gap-2 text-sm px-3 py-1.5 hover:bg-muted rounded-md transition-colors"
        >
          <ImageIcon className="w-4 h-4 text-blue-500" />
          Regenerate Images
        </button>
        <button
          onClick={() => setShowBatchModal("video")}
          className="flex items-center gap-2 text-sm px-3 py-1.5 hover:bg-muted rounded-md transition-colors"
        >
          <Video className="w-4 h-4 text-purple-500" />
          Regenerate Videos
        </button>
        <button
          onClick={() => setShowBatchModal("both")}
          className="flex items-center gap-2 text-sm px-3 py-1.5 hover:bg-muted rounded-md transition-colors"
        >
          <RotateCw className="w-4 h-4 text-green-500" />
          Both (Images + Videos)
        </button>
        <button
          onClick={() => setSelectedIndices([])}
          className="ml-2 p-1.5 hover:bg-muted rounded-full text-muted-foreground"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredShots.map((shot) => {
          const progressKey = shot.id || shot.index.toString();
          const isCurrentlyGenerating =
            generatingIndices.has(shot.index) ||
            shotProgress[progressKey] !== undefined;
          const isCurrentlyQueued =
            queuedIndices.has(shot.index) && !isCurrentlyGenerating;
          return (
            <ShotCard
              key={`${progressKey}-${shot.image_path}`}
              shot={shot}
              sessionId={sessionId}
              selectable={true}
              selected={selectedIndices.includes(shot.index)}
              onSelectChange={(selected: boolean) =>
                toggleSelectShot(shot.index, selected)
              }
              isGenerating={isCurrentlyGenerating}
              isQueued={isCurrentlyQueued}
              progress={shotProgress[progressKey]}
              onCancel={
                isCurrentlyGenerating || isCurrentlyQueued
                  ? () => handleCancelShot(shot.index)
                  : undefined
              }
              onInsertBefore={() =>
                setInsertModalConfig({ position: shot.index - 1 })
              }
              onInsertAfter={() =>
                setInsertModalConfig({ position: shot.index })
              }
              onDelete={() => handleDeleteShot(shot.index)}
            />
          );
        })}
      </div>

      <div className="mt-8 flex justify-center">
        <button
          onClick={() => setInsertModalConfig({ position: shots.length })}
          className="flex items-center gap-2 px-6 py-3 border-2 border-dashed rounded-lg hover:border-primary/50 hover:bg-muted/50 transition-colors text-muted-foreground hover:text-foreground"
        >
          <Plus className="w-5 h-5" />
          Add Shot to End
        </button>
      </div>

      {/* Insert Shot Modal Overlay */}
      {insertModalConfig && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-background rounded-lg shadow-xl max-w-2xl w-full p-6 relative max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => setInsertModalConfig(null)}
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
            >
              <X className="w-5 h-5" />
            </button>

            <h2 className="text-xl font-semibold mb-6">Insert New Shot</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Image Prompt
                </label>
                <Textarea
                  value={newShotData.image_prompt}
                  onChange={(e) =>
                    setNewShotData({
                      ...newShotData,
                      image_prompt: e.target.value,
                    })
                  }
                  className="min-h-[120px]"
                  placeholder="Describe the initial visual frame of the shot..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Motion Prompt
                </label>
                <Textarea
                  value={newShotData.motion_prompt}
                  onChange={(e) =>
                    setNewShotData({
                      ...newShotData,
                      motion_prompt: e.target.value,
                    })
                  }
                  className="min-h-[80px]"
                  placeholder="Describe the motion/video prompt..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Camera Movement
                </label>
                <Input
                  type="text"
                  value={newShotData.camera}
                  onChange={(e) =>
                    setNewShotData({ ...newShotData, camera: e.target.value })
                  }
                  placeholder="e.g. static, pan right, zoom in..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Narration (Optional)
                </label>
                <Textarea
                  value={newShotData.narration}
                  onChange={(e) =>
                    setNewShotData({
                      ...newShotData,
                      narration: e.target.value,
                    })
                  }
                  className="min-h-[60px]"
                  placeholder="Voiceover narration for this section..."
                />
              </div>
            </div>

            <div className="mt-8 flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => setInsertModalConfig(null)}
              >
                Cancel
              </Button>
              <Button
                onClick={handleInsertShot}
                disabled={
                  updateShotsMutation.isPending ||
                  (!newShotData.image_prompt && !newShotData.motion_prompt)
                }
              >
                {updateShotsMutation.isPending ? "Inserting..." : "Insert Shot"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Batch Modal Overlay */}
      {showBatchModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-background rounded-lg shadow-xl max-w-md w-full p-6 relative">
            <button
              onClick={() => setShowBatchModal(null)}
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
            >
              <X className="w-5 h-5" />
            </button>

            <h2 className="text-xl font-semibold mb-6">
              Batch Regenerate{" "}
              {showBatchModal === "image"
                ? "Images"
                : showBatchModal === "video"
                  ? "Videos"
                  : "Images + Videos"}{" "}
              ({selectedIndices.length} shots)
            </h2>

            {(showBatchModal === "image" || showBatchModal === "both") && (
              <div className="space-y-4">
                {showBatchModal === "both" && (
                  <div className="flex items-center gap-2 p-3 bg-muted/50 rounded-md border text-sm">
                    <Input
                      type="checkbox"
                      id="skip-existing"
                      checked={batchSkipImages}
                      onChange={(e) => setBatchSkipImages(e.target.checked)}
                      className="w-4 h-4 mr-2"
                    />
                    <label
                      htmlFor="skip-existing"
                      className="font-medium cursor-pointer"
                    >
                      Skip generating images if they already exist
                    </label>
                  </div>
                )}

                <div>
                  <label className="block text-sm font-medium mb-1">
                    Image Generation Mode
                  </label>
                  <Select
                    value={imageMode}
                    onValueChange={(val) => setImageMode(val)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select Mode" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="comfyui">ComfyUI (Local)</SelectItem>
                      <SelectItem value="gemini">Gemini (Cloud)</SelectItem>
                      <SelectItem value="geminiweb">
                        GeminiWeb - Gemini Web (Browser)
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {imageMode === "comfyui" && (
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      ComfyUI Workflow
                    </label>
                    <Select
                      value={imageWorkflow}
                      onValueChange={(val) => setImageWorkflow(val)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select Workflow" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="flux2">
                          Flux 2 (High Quality)
                        </SelectItem>
                        <SelectItem value="flux">Flux (Standard)</SelectItem>
                        <SelectItem value="sdxl">SDXL</SelectItem>
                        <SelectItem value="hidream">HiDream</SelectItem>
                        <SelectItem value="qwen">Qwen</SelectItem>
                        <SelectItem value="default">Default</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
            )}

            {(showBatchModal === "video" || showBatchModal === "both") && (
              <div className="space-y-4">
                {showBatchModal === "both" && <hr className="my-3" />}
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Video Workflow
                  </label>
                  <Input
                    type="text"
                    value={videoWorkflow}
                    onChange={(e) => setVideoWorkflow(e.target.value)}
                    placeholder="workflow/video/wan22_workflow.json"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Path to the ComfyUI video JSON workflow.
                  </p>
                </div>
              </div>
            )}

            <div className="mt-8 flex justify-end gap-3">
              <Button variant="outline" onClick={() => setShowBatchModal(null)}>
                Cancel
              </Button>
              <Button onClick={handleBatchSubmit}>Start Generation</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
