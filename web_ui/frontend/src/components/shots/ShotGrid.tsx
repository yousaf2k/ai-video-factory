/**
 * ShotGrid component - Grid view of shots with thumbnails and bulk actions
 */
import { useState, useCallback, useMemo, useEffect } from "react";
import { ShotCard } from "./ShotCard";
import { Shot, Scene } from "@/types";
import { useAgents, useConfig } from "@/hooks/useAgents";
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
  Layers,
  ChevronRight,
  ChevronDown,
  Info,
  Clock,
  Mic,
  Music,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
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
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
} from "@dnd-kit/sortable";
import { restrictToParentElement } from "@dnd-kit/modifiers";

interface ShotGridProps {
  shots: Shot[];
  sessionId: string;
  scenes?: Scene[];
}

export function ShotGrid({ shots, sessionId, scenes }: ShotGridProps) {
  const [selectedIndices, setSelectedIndices] = useState<number[]>([]);
  const [showBatchModal, setShowBatchModal] = useState<
    "image" | "video" | "both" | "narration" | null
  >(null);
  const [showSceneMoveModal, setShowSceneMoveModal] = useState(false);
  const [targetMoveScene, setTargetMoveScene] = useState<number | null>(null);
  const [generatingIndices, setGeneratingIndices] = useState<Set<number>>(
    new Set(),
  );
  const [queuedIndices, setQueuedIndices] = useState<Set<number>>(new Set());
  const [generatingScenes, setGeneratingScenes] = useState<Set<number>>(new Set());
  const queryClient = useQueryClient();
  const updateShotsMutation = useUpdateShots(sessionId);
  const [viewModeOverride, setViewModeOverride] = useState<
    "image" | "video" | null
  >(null);
  const [isGroupingEnabled, setIsGroupingEnabled] = useState(true);
  const [activeSceneTab, setActiveSceneTab] = useState<string | "all">("all");
  const [expandedScenes, setExpandedScenes] = useState<Record<number, boolean>>({});

  const toggleSceneExpansion = (idx: number) => {
    setExpandedScenes((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  // Insert modal state
  const [insertModalConfig, setInsertModalConfig] = useState<{
    position: number;
  } | null>(null);
  const [newShotData, setNewShotData] = useState<Partial<Shot>>({
    image_prompt: "",
    motion_prompt: "",
    camera: "static",
    narration: "",
    character_id: undefined,
    then_image_prompt: undefined,
    now_image_prompt: undefined,
    meeting_video_prompt: undefined,
    departure_video_prompt: undefined,
  });

  const { shotProgress, sceneProgress } = useProgress(
    sessionId,
    useCallback(
      (id: string | number, type: 'shot' | 'scene') => {
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
  const [filterNoNarration, setFilterNoNarration] = useState(false);
  const [filterCamera, setFilterCamera] = useState<string>("");
  const [filterText, setFilterText] = useState<string>("");

  // Overrides state
  const [imageMode, setImageMode] = useState<string>("comfyui");
  const [imageWorkflow, setImageWorkflow] = useState<string>("flux2");
  const [videoWorkflow, setVideoWorkflow] = useState<string>("wan22");
  const [videoMode, setVideoMode] = useState<string>("comfyui");
  const [batchSkipImages, setBatchSkipImages] = useState<boolean>(true);

  const [ttsMethod, setTtsMethod] = useState("local");
  const [ttsVoice, setTtsVoice] = useState("en-US-AriaNeural");

  const { data: agents } = useAgents();
  const { data: globalConfig } = useConfig();

  // Drag and drop sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 8px movement required to start dragging
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;

    if (!over || active.id === over.id) {
      return;
    }

    // Find the shots in the filtered list
    const oldIndex = filteredShots.findIndex((s) => s.index === active.id);
    const newIndex = filteredShots.findIndex((s) => s.index === over.id);

    if (oldIndex === -1 || newIndex === -1) {
      return;
    }

    // Reorder the filtered shots
    const reorderedFilteredShots = arrayMove(filteredShots, oldIndex, newIndex);

    // Now we need to update the full shots array
    // Create a map of the new indices for reordered shots
    const indexUpdates: Record<number, number> = {};
    reorderedFilteredShots.forEach((shot, idx) => {
      indexUpdates[shot.index] = idx + 1;
    });

    // Create updated shots array with new indices
    const updatedShots = shots.map((shot) => {
      if (indexUpdates[shot.index] !== undefined) {
        return { ...shot, index: indexUpdates[shot.index] };
      }
      return shot;
    });

    // Sort by new index to ensure proper order
    updatedShots.sort((a, b) => a.index - b.index);

    try {
      await updateShotsMutation.mutateAsync(updatedShots);
      toast.success("Shots reordered successfully", {
        description: `Shot ${active.id} has been moved to position ${newIndex + 1}.`,
        className: toastStyles.success,
      });
    } catch (error) {
      console.error("Failed to reorder shots:", error);
      toast.error("Failed to reorder shots", {
        description: "Please try again.",
        className: toastStyles.error,
      });
    }
  };

  // Update default workflow when config loads
  useEffect(() => {
    if (globalConfig?.video_workflow) {
      setVideoWorkflow(globalConfig.video_workflow);
    }
  }, [globalConfig]);

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

    if (isGroupingEnabled && activeSceneTab !== "all") {
      const sceneDisplayIdx = parseInt(activeSceneTab);
      const targetSceneId = sceneDisplayIdx - 1;
      result = result.filter((s) => (s.scene_id ?? -1) === targetSceneId);
    }

    return result;
  }, [shots, filterNoImages, filterNoVideos, filterCamera, filterText, activeSceneTab, isGroupingEnabled]);

  const groupedShots = useMemo(() => {
    if (!isGroupingEnabled) return { all: filteredShots };

    const groups: Record<number | string, Shot[]> = {};

    // Pre-populate groups with the relevant scenes to ensure headers show even if empty
    if (scenes && scenes.length > 0) {
      if (activeSceneTab === "all") {
        scenes.forEach((_, idx) => {
          groups[idx] = [];
        });
      } else {
        const sceneDisplayIdx = parseInt(activeSceneTab);
        if (!isNaN(sceneDisplayIdx)) {
          groups[sceneDisplayIdx - 1] = [];
        }
      }
    }

    filteredShots.forEach((shot) => {
      const sceneIdx = shot.scene_id ?? "unassigned";
      if (!groups[sceneIdx]) {
        groups[sceneIdx] = [];
      }
      groups[sceneIdx].push(shot);
    });
    return groups;
  }, [filteredShots, isGroupingEnabled, scenes]);

  const hasActiveFilters =
    filterNoImages || filterNoVideos || !!filterCamera || !!filterText.trim();

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
          // When doing both: 
          // 1. Image force depends on the "Skip" checkbox
          // 2. Video force is ALWAYS true if they clicked regenerate videos
          force_images: !batchSkipImages,
          force_videos: true,
          image_mode: imageMode,
          image_workflow: imageWorkflow,
          video_mode: videoMode,
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
          force_images: true,
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
          force_videos: true,
          video_mode: videoMode,
          video_workflow: videoWorkflow,
        });
      } catch (error) {
        console.error("Failed to start batch video generation:", error);
      }
    } else if (type === "narration") {
      try {
        // Collect unique scene indices from selected shots
        const sceneIndices = Array.from(new Set(
          shots
            .filter(s => indicesToProcess.includes(s.index))
            .map(s => s.scene_id || 0)
        ));

        await api.batchGenerateNarration(sessionId, sceneIndices, {
          tts_method: ttsMethod,
          voice: ttsVoice,
        });

        // Mark scenes as generating
        setGeneratingScenes(new Set(sceneIndices));
      } catch (error) {
        console.error("Failed to start batch narration generation:", error);
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

  const handleBatchMoveToScene = async () => {
    if (selectedIndices.length === 0 || targetMoveScene === null) return;

    try {
      // Create a map of updates
      const updatedShots = shots.map(shot => {
        if (selectedIndices.includes(shot.index)) {
          return { ...shot, scene_id: targetMoveScene };
        }
        return shot;
      });

      await updateShotsMutation.mutateAsync(updatedShots);
      setShowSceneMoveModal(false);
      setSelectedIndices([]);
      setTargetMoveScene(null);
    } catch (error) {
      console.error("Failed to batch move shots to scene:", error);
      alert("Failed to move shots. Please try again.");
    }
  };

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
      toast.success("Shot deleted successfully", {
        description: `Shot ${indexToRemove} has been removed.`,
        className: toastStyles.success,
      });
    } catch (error) {
      console.error("Failed to delete shot:", error);
      toast.error("Failed to delete shot", {
        description: "Please try again.",
        className: toastStyles.error,
      });
    }
  };

  const handleInsertShot = async () => {
    if (!insertModalConfig) return;

    // Check if this is an FLFI2V session
    const isFlfi2vSession = shots.length > 0 && shots.some(s => s.is_flfi2v);

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
      // FLFI2V fields - include if this is an FLFI2V session
      ...(isFlfi2vSession ? {
        is_flfi2v: true,
        character_id: newShotData.character_id || undefined,
        then_image_prompt: newShotData.then_image_prompt || undefined,
        now_image_prompt: newShotData.now_image_prompt || undefined,
        then_image_generated: false,
        now_image_generated: false,
        then_image_path: undefined,
        now_image_path: undefined,
        meeting_video_prompt: newShotData.meeting_video_prompt || undefined,
        departure_video_prompt: newShotData.departure_video_prompt || undefined,
        meeting_video_rendered: false,
        departure_video_rendered: false,
        meeting_video_path: undefined,
        departure_video_path: undefined,
      } : {}),
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
        character_id: undefined,
        then_image_prompt: undefined,
        now_image_prompt: undefined,
        meeting_video_prompt: undefined,
        departure_video_prompt: undefined,
      });
      toast.success("Shot added successfully", {
        description: `New shot has been inserted at position ${pos + 1}.`,
        className: toastStyles.success,
      });
    } catch (error) {
      console.error("Failed to insert shot:", error);
      toast.error("Failed to insert shot", {
        description: "Please try again.",
        className: toastStyles.error,
      });
    }
  };

  if (shots.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No shots yet. Generate story and plan shots first.
      </div>
    );
  }

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

          <div className="h-4 w-px bg-border mx-2" />

          <button
            onClick={() => setViewModeOverride("image")}
            className="flex items-center gap-1.5 text-sm px-2.5 py-1 border rounded-md hover:bg-muted transition-colors text-blue-600"
            title="Switch all shots to image view"
          >
            <ImageIcon className="w-3.5 h-3.5" />
            All Images
          </button>
          <button
            onClick={() => setViewModeOverride("video")}
            className="flex items-center gap-1.5 text-sm px-2.5 py-1 border rounded-md hover:bg-muted transition-colors text-purple-600"
            title="Switch all shots to video view"
          >
            <Video className="w-3.5 h-3.5" />
            All Videos
          </button>
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
          onClick={() => setShowSceneMoveModal(true)}
          className="flex items-center gap-2 text-sm px-3 py-1.5 hover:bg-muted rounded-md transition-colors"
        >
          <Layers className="w-4 h-4 text-orange-500" />
          Move to Scene
        </button>
        <button
          onClick={() => setShowBatchModal("narration")}
          className="flex items-center gap-2 text-sm px-3 py-1.5 hover:bg-muted rounded-md transition-colors"
        >
          <Mic className="w-4 h-4 text-pink-500" />
          Regenerate Narration
        </button>
        <button
          onClick={() => setSelectedIndices([])}
          className="ml-2 p-1.5 hover:bg-muted rounded-full text-muted-foreground"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Scene Tabs (only if grouping enabled) */}
      {isGroupingEnabled && scenes && (
        <div className="flex flex-wrap gap-1 mb-6 p-1 bg-muted/30 rounded-lg border">
          <button
            onClick={() => setActiveSceneTab("all")}
            className={cn(
              "px-4 py-1.5 text-sm rounded-md transition-all font-medium border",
              activeSceneTab === "all"
                ? "bg-white dark:bg-muted shadow-sm text-primary border-border"
                : "text-muted-foreground hover:bg-muted/50 border-transparent"
            )}
          >
            All Scenes
          </button>
          {scenes.map((scene, idx) => (
            <button
              key={idx}
              onClick={() => setActiveSceneTab((idx + 1).toString())}
              className={cn(
                "px-4 py-1.5 text-sm rounded-md transition-all font-medium border",
                activeSceneTab === (idx + 1).toString()
                  ? "bg-white dark:bg-muted shadow-sm text-primary border-border"
                  : "text-muted-foreground hover:bg-muted/50 border-transparent"
              )}
            >
              Scene {idx + 1}
            </button>
          ))}
        </div>
      )}

      {/* Grid */}
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
        modifiers={[restrictToParentElement]}
      >
        <div className="space-y-8">
          {Object.entries(groupedShots).map(([sceneIdxStr, groupShots]) => {
            const isUnassigned = sceneIdxStr === "unassigned" || sceneIdxStr === "all" || sceneIdxStr === "null";
            const sIdx = isUnassigned ? null : parseInt(sceneIdxStr);
            const scene = sIdx !== null && scenes ? scenes[sIdx] : null;

            return (
              <div key={sceneIdxStr} className="space-y-4">
                {isGroupingEnabled && (
                  <div className="flex flex-col gap-3 pb-4 border-b">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        <span className="bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wider whitespace-nowrap shrink-0">
                          {sIdx !== null ? `Scene ${sIdx + 1}` : "Unmatched Shots"}
                        </span>
                        {scene && (
                          <div className="flex flex-col gap-1">
                            <h3 className="text-xl font-bold tracking-tight">
                              {scene.location}
                            </h3>
                            {sIdx !== null && sceneProgress[sIdx] !== undefined && (
                              <div className="flex items-center gap-2 mt-1">
                                <div className="w-24 h-1 bg-pink-100 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-pink-500 transition-all"
                                    style={{ width: `${sceneProgress[sIdx]}%` }}
                                  />
                                </div>
                                <span className="text-[10px] text-pink-600 font-medium">
                                  Narration: {Math.round(sceneProgress[sIdx])}%
                                </span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      {scene && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => sIdx !== null && toggleSceneExpansion(sIdx)}
                          className="h-8 gap-1.5 text-muted-foreground hover:text-primary"
                        >
                          {sIdx !== null && expandedScenes[sIdx] ? (
                            <>
                              <ChevronDown className="w-4 h-4" />
                              <span className="text-xs">Less Detail</span>
                            </>
                          ) : (
                            <>
                              <ChevronRight className="w-4 h-4" />
                              <span className="text-xs">More Detail</span>
                            </>
                          )}
                        </Button>
                      )}
                    </div>

                    {scene && (
                      <div className="space-y-3">
                        <p className={cn(
                          "text-sm text-muted-foreground italic leading-relaxed",
                          !expandedScenes[sIdx || 0] && "line-clamp-1"
                        )}>
                          {scene.action}
                        </p>

                        {sIdx !== null && expandedScenes[sIdx] && (
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 p-4 bg-muted/20 rounded-xl border border-border/50 animate-in fade-in slide-in-from-top-2 duration-300">
                            <div className="space-y-1">
                              <span className="text-[10px] font-bold uppercase text-muted-foreground tracking-widest flex items-center gap-1.5">
                                <Info className="w-3 h-3" /> Characters
                              </span>
                              <p className="text-sm font-medium">{scene.characters || "None specified"}</p>
                            </div>
                            <div className="space-y-1">
                              <span className="text-[10px] font-bold uppercase text-muted-foreground tracking-widest flex items-center gap-1.5">
                                <Info className="w-3 h-3" /> Emotion
                              </span>
                              <p className="text-sm font-medium capitalize">{scene.emotion || "Neutral"}</p>
                            </div>
                            <div className="col-span-full space-y-1">
                              <span className="text-[10px] font-bold uppercase text-muted-foreground tracking-widest flex items-center gap-1.5">
                                <Info className="w-3 h-3" /> Narration
                              </span>
                              <p className="text-sm leading-relaxed bg-background/50 p-2.5 rounded-lg border italic">
                                "{scene.narration || "No narration for this scene."}"
                              </p>
                            </div>
                            {scene.scene_duration && (
                              <div className="col-span-full pt-2 flex items-center gap-2 text-xs text-muted-foreground">
                                <Clock className="w-3.5 h-3.5" />
                                <span>Estimated Duration: <strong>{scene.scene_duration}s</strong></span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                <SortableContext
                  items={groupShots.map(s => s.index)}
                  strategy={rectSortingStrategy}
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {groupShots.map((shot) => {
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
                          viewModeOverride={viewModeOverride}
                          scenes={scenes}
                        />
                      );
                    })}
                  </div>
                </SortableContext>
              </div>
            );
          })}
        </div>
      </DndContext>

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
      {
        insertModalConfig && (
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
                {/* FLFI2V Indicator */}
                {shots.length > 0 && shots.some(s => s.is_flfi2v) && (
                  <div className="bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 rounded-lg p-3 mb-4">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] bg-gradient-to-r from-purple-500 to-pink-500 text-white px-2 py-0.5 rounded-full font-bold">
                        FLFI2V MODE
                      </span>
                      <span className="text-sm text-purple-700 dark:text-purple-300">
                        This is a ThenVsNow session - FLFI2V fields will be included
                      </span>
                    </div>
                  </div>
                )}

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

                {/* FLFI2V: THEN Image Prompt */}
                {shots.length > 0 && shots.some(s => s.is_flfi2v) && (
                  <div>
                    <label className="block text-sm font-medium mb-1 text-purple-700 dark:text-purple-300">
                      THEN Image Prompt (Original Appearance)
                    </label>
                    <Textarea
                      value={newShotData.then_image_prompt || ""}
                      onChange={(e) =>
                        setNewShotData({
                          ...newShotData,
                          then_image_prompt: e.target.value,
                        })
                      }
                      className="min-h-[80px]"
                      placeholder="Describe the character's original/THEN appearance..."
                    />
                  </div>
                )}

                {/* FLFI2V: NOW Image Prompt */}
                {shots.length > 0 && shots.some(s => s.is_flfi2v) && (
                  <div>
                    <label className="block text-sm font-medium mb-1 text-pink-700 dark:text-pink-300">
                      NOW Image Prompt (Current Appearance)
                    </label>
                    <Textarea
                      value={newShotData.now_image_prompt || ""}
                      onChange={(e) =>
                        setNewShotData({
                          ...newShotData,
                          now_image_prompt: e.target.value,
                        })
                      }
                      className="min-h-[80px]"
                      placeholder="Describe the character's current/NOW appearance..."
                    />
                  </div>
                )}

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

                {/* FLFI2V: Meeting Video Prompt */}
                {shots.length > 0 && shots.some(s => s.is_flfi2v) && (
                  <div>
                    <label className="block text-sm font-medium mb-1 text-purple-700 dark:text-purple-300">
                      Meeting Video Prompt
                    </label>
                    <Textarea
                      value={newShotData.meeting_video_prompt || ""}
                      onChange={(e) =>
                        setNewShotData({
                          ...newShotData,
                          meeting_video_prompt: e.target.value,
                        })
                      }
                      className="min-h-[80px]"
                      placeholder="Describe the meeting video motion..."
                    />
                  </div>
                )}

                {/* FLFI2V: Departure Video Prompt */}
                {shots.length > 0 && shots.some(s => s.is_flfi2v) && (
                  <div>
                    <label className="block text-sm font-medium mb-1 text-pink-700 dark:text-pink-300">
                      Departure Video Prompt
                    </label>
                    <Textarea
                      value={newShotData.departure_video_prompt || ""}
                      onChange={(e) =>
                        setNewShotData({
                          ...newShotData,
                          departure_video_prompt: e.target.value,
                        })
                      }
                      className="min-h-[80px]"
                      placeholder="Describe the departure/transitional video motion..."
                    />
                  </div>
                )}

                {/* FLFI2V: Character ID */}
                {shots.length > 0 && shots.some(s => s.is_flfi2v) && (
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Character ID (Optional)
                    </label>
                    <Input
                      type="text"
                      value={newShotData.character_id || ""}
                      onChange={(e) =>
                        setNewShotData({
                          ...newShotData,
                          character_id: e.target.value,
                        })
                      }
                      placeholder="e.g., char_000, char_001..."
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Assign this shot to a character (leave empty to auto-assign)
                    </p>
                  </div>
                )}

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
        )
      }

      {/* Batch Modal Overlay */}
      {
        showBatchModal && (
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
                          {globalConfig?.available_image_workflows?.map((wf) => (
                            <SelectItem key={wf} value={wf}>
                              {wf.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                            </SelectItem>
                          )) || (
                              <>
                                <SelectItem value="flux2">Flux 2</SelectItem>
                                <SelectItem value="flux">Flux</SelectItem>
                                <SelectItem value="sdxl">SDXL</SelectItem>
                                <SelectItem value="default">Default</SelectItem>
                              </>
                            )}
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
                      Video Generation Mode
                    </label>
                    <Select
                      value={videoMode}
                      onValueChange={(val) => setVideoMode(val)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select Video Mode" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="comfyui">ComfyUI (Local)</SelectItem>
                        <SelectItem value="geminiweb">
                          GeminiWeb - Gemini Web (Browser)
                        </SelectItem>
                        <SelectItem value="flowweb">FlowWeb (Experimental)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Video Workflow
                    </label>
                    <Select
                      value={videoWorkflow}
                      onValueChange={(val) => setVideoWorkflow(val)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select Video Workflow" />
                      </SelectTrigger>
                      <SelectContent>
                        {globalConfig?.available_video_workflows?.map((wf) => (
                          <SelectItem key={wf} value={wf}>
                            {wf}
                          </SelectItem>
                        )) || (
                            <SelectItem value="wan22">Wan 2.2</SelectItem>
                          )}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground mt-1">
                      Pre-configured ComfyUI video workflow.
                    </p>
                  </div>
                </div>
              )}

              {showBatchModal === "narration" && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      TTS Method
                    </label>
                    <Select
                      value={ttsMethod}
                      onValueChange={(val) => setTtsMethod(val)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select TTS Method" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="local">Local (Edge-TTS)</SelectItem>
                        <SelectItem value="elevenlabs">ElevenLabs (High Quality)</SelectItem>
                        <SelectItem value="comfyui">ComfyUI TTS</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Voice
                    </label>
                    <Select
                      value={ttsVoice}
                      onValueChange={(val) => setTtsVoice(val)}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select Voice" />
                      </SelectTrigger>
                      <SelectContent>
                        {ttsMethod === "local" ? (
                          <>
                            <SelectItem value="en-US-AriaNeural">Aria (Female)</SelectItem>
                            <SelectItem value="en-US-GuyNeural">Guy (Male)</SelectItem>
                            <SelectItem value="en-GB-SoniaNeural">Sonia (UK Female)</SelectItem>
                            <SelectItem value="en-GB-RyanNeural">Ryan (UK Male)</SelectItem>
                          </>
                        ) : ttsMethod === "elevenlabs" ? (
                          <>
                            <SelectItem value="premade/adam">Adam (Deep Engine)</SelectItem>
                            <SelectItem value="premade/antoni">Antoni (Soothing)</SelectItem>
                            <SelectItem value="premade/bella">Bella (Soft)</SelectItem>
                          </>
                        ) : (
                          <>
                            <SelectItem value="default_female.wav">Default Female</SelectItem>
                            <SelectItem value="default_male.wav">Default Male</SelectItem>
                          </>
                        )}
                      </SelectContent>
                    </Select>
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
        )
      }

      {/* Bulk Move Scene Modal Overlay */}
      {showSceneMoveModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-background rounded-lg shadow-xl max-w-md w-full p-6 relative">
            <button
              onClick={() => {
                setShowSceneMoveModal(false);
                setTargetMoveScene(null);
              }}
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
            >
              <X className="w-5 h-5" />
            </button>

            <h2 className="text-xl font-semibold mb-6">
              Move Selected to Scene
            </h2>
            <p className="text-sm text-muted-foreground mb-4">
              Moving {selectedIndices.length} selected shots to a new scene.
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Target Scene
                </label>
                <Select
                  value={targetMoveScene !== null ? targetMoveScene.toString() : "null"}
                  onValueChange={(val) => setTargetMoveScene(val === "null" ? null : parseInt(val))}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select target scene" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="null">None (Unassigned)</SelectItem>
                    {scenes?.map((_, idx) => (
                      <SelectItem key={idx} value={idx.toString()}>
                        Scene {idx + 1}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="mt-8 flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setShowSceneMoveModal(false);
                  setTargetMoveScene(null);
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleBatchMoveToScene}
                disabled={targetMoveScene === null || updateShotsMutation.isPending}
              >
                {updateShotsMutation.isPending ? "Moving..." : "Move Selected"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
