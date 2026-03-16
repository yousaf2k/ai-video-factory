/**
 * ShotCard component - Individual shot with editing and regeneration
 */
import { useState, useRef, useEffect, useCallback } from "react";
import {
  Edit3,
  RotateCw,
  RefreshCw,
  Image,
  Layers,
  Video,
  Check,
  X,
  Loader2,
  Clock,
  Plus,
  Trash2,
  Wand2,
  Upload,
  Maximize2,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Copy,
  ClipboardCheck,
  GripVertical,
} from "lucide-react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Shot } from "@/types";
import { toast } from "sonner";
import {
  useUpdateShot,
  useRegenerateImage,
  useRegenerateVideo,
  useSelectImage,
  useRemoveWatermark,
  useUploadShotImage,
  useDeleteVariationImage,
  useSelectVideo,
  useDeleteVariationVideo,
  useUploadShotVideo,
} from "@/hooks/useShots";
import { useAgents, useConfig } from "@/hooks/useAgents";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";
import { cn, getMediaUrl } from "@/lib/utils";
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

interface ShotCardProps {
  shot: Shot;
  projectId: string;
  showIndex?: boolean;
  selectable?: boolean;
  selected?: boolean;
  onSelectChange?: (selected: boolean) => void;
  isGenerating?: boolean;
  isQueued?: boolean;
  progress?: number;
  onCancel?: () => void;
  onInsertBefore?: () => void;
  onInsertAfter?: () => void;
  onDelete?: () => void;
  viewModeOverride?: "image" | "video" | null;
  scenes?: any[];
}

export function ShotCard({
  shot,
  projectId,
  showIndex = true,
  selectable = false,
  selected = false,
  onSelectChange,
  isGenerating = false,
  isQueued = false,
  progress,
  onCancel,
  onInsertBefore,
  onInsertAfter,
  onDelete,
  viewModeOverride,
  scenes,
}: ShotCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedShot, setEditedShot] = useState(shot);
  const [viewMode, setViewMode] = useState<"image" | "video">("image");

  // FLFI2V state management
  const [activeImageMode, setActiveImageMode] = useState<"then" | "now">("now");
  const [activeVideoMode, setActiveVideoMode] = useState<"meeting" | "departure">("meeting");

  // Update cache buster when video mode or image mode changes to force media reload
  useEffect(() => {
    if (shot.is_flfi2v) {
      setCacheBuster(Date.now());
    }
  }, [activeVideoMode, activeImageMode, shot.is_flfi2v]);

  // Update editedShot when shot prop changes (e.g., after regeneration)
  useEffect(() => {
    setEditedShot(shot);
    // Force cache buster update when shot changes to refresh media URLs
    if (shot.is_flfi2v) {
      setCacheBuster(Date.now());
    }
  }, [shot]);

  // Regeneration modal state
  const [showRegenModal, setShowRegenModal] = useState<
    "image" | "video" | null
  >(null);
  const [regenForce, setRegenForce] = useState(true);
  const [regenImageMode, setRegenImageMode] = useState("comfyui");
  const [regenImageWorkflow, setRegenImageWorkflow] = useState("flux2");
  const [regenVideoWorkflow, setRegenVideoWorkflow] = useState("wan22");
  const [regenVideoMode, setRegenVideoMode] = useState("comfyui");
  const [regenSeed, setRegenSeed] = useState<number | "">("");
  const [regenPromptOverride, setRegenPromptOverride] = useState<string>("");
  const [appendImagePrompt, setAppendImagePrompt] = useState<string>("default");

  // ... rest of the hook setup ...
  const queryClient = useQueryClient();
  const updateShot = useUpdateShot(projectId, shot.index);
  const regenerateImage = useRegenerateImage(projectId);
  const regenerateVideo = useRegenerateVideo(projectId);
  const selectImage = useSelectImage(projectId);
  const removeWatermark = useRemoveWatermark(projectId);
  const uploadShotImage = useUploadShotImage(projectId);
  const uploadShotVideo = useUploadShotVideo(projectId);
  const deleteVariation = useDeleteVariationImage(projectId);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isVideoUploading, setIsVideoUploading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [cacheBuster, setCacheBuster] = useState(Date.now());
  const [showGalleryModal, setShowGalleryModal] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  // fullscreenVariationIndex: index into shot.image_paths; null = closed
  const [fullscreenVariationIndex, setFullscreenVariationIndex] = useState<number | null>(null);
  const [isImagePromptExpanded, setIsImagePromptExpanded] = useState(false);
  const [isMotionPromptExpanded, setIsMotionPromptExpanded] = useState(false);

  const selectVideo = useSelectVideo(projectId);
  const deleteVariationVideo = useDeleteVariationVideo(projectId);

  const { data: globalConfig } = useConfig();

  // Drag and drop functionality
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: shot.index,
    disabled: isEditing || isGenerating,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  // Update default workflow when config loads
  useEffect(() => {
    if (globalConfig?.video_workflow) {
      setRegenVideoWorkflow(globalConfig.video_workflow);
    }
  }, [globalConfig]);

  // Load saved video mode preference for this project on mount
  useEffect(() => {
    const savedVideoMode = localStorage.getItem(`video_mode_${projectId}`);
    if (savedVideoMode) {
      setRegenVideoMode(savedVideoMode);
    }
  }, [projectId]);

  // Derived data for the fullscreen carousel
  // For FLFI2V shots, construct array with THEN and NOW images
  const fsImages = (() => {
    if (shot.is_flfi2v && viewMode === "image") {
      const flfi2vImages = [];
      if (shot.then_image_path) flfi2vImages.push(shot.then_image_path);
      if (shot.now_image_path) flfi2vImages.push(shot.now_image_path);
      return flfi2vImages.length > 0 ? flfi2vImages : (shot.image_paths ?? []);
    }
    return viewMode === "video" ? (shot.video_paths ?? []) : (shot.image_paths ?? []);
  })();
  const fsTotal = fsImages.length;

  const openFullscreen = useCallback((idx: number) => {
    setFullscreenVariationIndex(Math.max(0, Math.min(idx, fsTotal - 1)));
  }, [fsTotal]);

  const closeFullscreen = useCallback(() => setFullscreenVariationIndex(null), []);

  const fsNext = useCallback(() => {
    setFullscreenVariationIndex((i) => i === null ? null : (i + 1) % fsTotal);
  }, [fsTotal]);

  const fsPrev = useCallback(() => {
    setFullscreenVariationIndex((i) => i === null ? null : (i - 1 + fsTotal) % fsTotal);
  }, [fsTotal]);

  // Keyboard navigation for fullscreen
  useEffect(() => {
    if (fullscreenVariationIndex === null) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") { e.preventDefault(); fsNext(); }
      if (e.key === "ArrowLeft") { e.preventDefault(); fsPrev(); }
      if (e.key === "Escape") { e.preventDefault(); closeFullscreen(); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [fullscreenVariationIndex, fsNext, fsPrev, closeFullscreen]);

  // Update viewMode when override changes
  useEffect(() => {
    if (viewModeOverride) {
      setViewMode(viewModeOverride);
    }
  }, [viewModeOverride]);

  const hasMultipleVariations = (() => {
    if (shot.is_flfi2v && viewMode === "image") {
      // FLFI2V has multiple variations if both THEN and NOW images exist
      return !!(shot.then_image_path && shot.now_image_path);
    }
    return viewMode === "video"
      ? (shot.video_paths?.length ?? 0) > 1
      : (shot.image_paths?.length ?? 0) > 1;
  })();

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await queryClient.invalidateQueries({ queryKey: ["shots", projectId] });
    await queryClient.invalidateQueries({ queryKey: ["project", projectId] });
    setCacheBuster(Date.now());
    setTimeout(() => setIsRefreshing(false), 600);
  };

  const handleSave = async () => {
    try {
      await updateShot.mutateAsync({
        image_prompt: editedShot.image_prompt,
        motion_prompt: editedShot.motion_prompt,
        camera: editedShot.camera,
        narration: editedShot.narration,
        scene_id: editedShot.scene_id,
        // FLFI2V fields
        then_image_prompt: editedShot.then_image_prompt,
        now_image_prompt: editedShot.now_image_prompt,
        meeting_video_prompt: editedShot.meeting_video_prompt,
        departure_video_prompt: editedShot.departure_video_prompt,
      });
      setIsEditing(false);
      toast.success("Shot updated successfully", {
        description: `Shot ${shot.index} has been saved.`,
      });
    } catch (error) {
      console.error("Failed to update shot:", error);
      toast.error("Failed to update shot", {
        description: "Please try again.",
      });
    }
  };

  const handleCancel = () => {
    setEditedShot(shot);
    setIsEditing(false);
  };

  const handleRegenerateImage = async () => {
    // Pre-populate prompt textarea with the shot's current prompt
    const promptToUse = shot.is_flfi2v
      ? (activeImageMode === 'then' ? shot.then_image_prompt : shot.now_image_prompt) || shot.image_prompt
      : shot.image_prompt;
    setRegenPromptOverride(promptToUse ?? "");
    setShowRegenModal("image");
  };

  const handleRegenerateVideo = async () => {
    setShowRegenModal("video");
  };

  const handleRegenSubmit = async () => {
    try {
      const type = showRegenModal;
      // Close modal immediately
      setShowRegenModal(null);

      if (type === "image") {
        // For FLFI2V shots, only generate the currently active variant (THEN or NOW)
        const imageVariant = shot.is_flfi2v ? activeImageMode : undefined;
        regenerateImage.mutate({
          shotIndex: shot.index,
          force: regenForce,
          imageMode: regenImageMode,
          imageWorkflow: regenImageWorkflow,
          seed: regenSeed === "" ? undefined : regenSeed,
          promptOverride: regenPromptOverride.trim() || undefined,
          imageVariant,
        });
        toast.info("Image regeneration started", {
          description: `Shot ${shot.index}${shot.is_flfi2v && imageVariant ? ` (${imageVariant.toUpperCase()})` : ""} image is being generated.`,
        });
      } else if (type === "video") {
        // For FLFI2V shots, only generate the currently active variant (Meeting or Departure)
        const videoVariant = shot.is_flfi2v ? activeVideoMode : undefined;
        regenerateVideo.mutate({
          shotIndex: shot.index,
          force: regenForce,
          videoMode: regenVideoMode,
          videoWorkflow: regenVideoMode === "comfyui" ? regenVideoWorkflow : undefined,
          videoVariant,
          appendImagePrompt: appendImagePrompt === "default" ? undefined : appendImagePrompt,
        });
        setViewMode("video");
        toast.info("Video regeneration started", {
          description: `Shot ${shot.index}${shot.is_flfi2v && videoVariant ? ` (${videoVariant.charAt(0).toUpperCase() + videoVariant.slice(1)})` : ""} video is being generated.`,
        });
      }
      setCacheBuster(Date.now());
    } catch (error) {
      console.error(`Failed to trigger regeneration:`, error);
      toast.error("Failed to start regeneration", {
        description: "Please try again.",
      });
    }
  };

  const imageUrl = shot.is_flfi2v
    ? getMediaUrl(
      activeImageMode === 'then'
        ? shot.then_image_path || shot.now_image_path || shot.image_path
        : shot.now_image_path || shot.then_image_path || shot.image_path
    )
    : getMediaUrl(shot.image_path);
  const videoUrl = shot.is_flfi2v
    ? getMediaUrl(
      activeVideoMode === 'meeting'
        ? shot.meeting_video_path || shot.departure_video_path || shot.video_path
        : shot.departure_video_path || shot.meeting_video_path || shot.video_path
    )
    : getMediaUrl(shot.video_path);

  // Append cache-busting param so browser fetches the latest file from disk
  const bustCache = (url: string) =>
    url ? `${url}${url.includes("?") ? "&" : "?"}t=${cacheBuster}` : "";
  const cachedImageUrl = bustCache(imageUrl);

  // Fullscreen carousel URL (computed after bustCache is available)
  const fsUrl = fullscreenVariationIndex !== null && fsTotal > 0
    ? bustCache(getMediaUrl(fsImages[fullscreenVariationIndex]))
    : null;
  const cachedVideoUrl = bustCache(videoUrl);

  if (isEditing) {
    return (
      <div
        className={cn(
          "border rounded-lg p-4 bg-background",
          selected && "border-primary ring-1 ring-primary",
        )}
      >
        {/* ... editing UI ... */}
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-muted-foreground">
            Shot {shot.index}
          </span>
          <div className="flex gap-2">
            <button
              onClick={handleCancel}
              className="p-1 hover:bg-muted rounded"
              title="Cancel"
            >
              <X className="w-4 h-4" />
            </button>
            <button
              onClick={handleSave}
              disabled={updateShot.isPending}
              className="p-1 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50"
              title="Save"
            >
              <Check className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="space-y-3">
          {/* FLFI2V Image Prompts */}
          {shot.is_flfi2v ? (
            <>
              <div>
                <label className="text-xs text-purple-600 font-semibold">THEN Image Prompt</label>
                <Textarea
                  value={editedShot.then_image_prompt || ''}
                  onChange={(e) =>
                    setEditedShot({ ...editedShot, then_image_prompt: e.target.value })
                  }
                  placeholder="Prompt for THEN image (original appearance)"
                  className="mt-1 min-h-[80px] border-purple-200 focus:border-purple-500"
                />
              </div>

              <div>
                <label className="text-xs text-pink-600 font-semibold">NOW Image Prompt</label>
                <Textarea
                  value={editedShot.now_image_prompt || ''}
                  onChange={(e) =>
                    setEditedShot({ ...editedShot, now_image_prompt: e.target.value })
                  }
                  placeholder="Prompt for NOW image (current appearance with selfie)"
                  className="mt-1 min-h-[80px] border-pink-200 focus:border-pink-500"
                />
              </div>
            </>
          ) : (
            <div>
              <label className="text-xs text-muted-foreground">
                Image Prompt
              </label>
              <Textarea
                value={editedShot.image_prompt}
                onChange={(e) =>
                  setEditedShot({ ...editedShot, image_prompt: e.target.value })
                }
                className="mt-1 min-h-[120px]"
              />
            </div>
          )}

          {/* FLFI2V Motion Prompts */}
          {shot.is_flfi2v ? (
            <>
              <div>
                <label className="text-xs text-purple-600 font-semibold">Meeting Video Prompt</label>
                <Textarea
                  value={editedShot.meeting_video_prompt || ''}
                  onChange={(e) =>
                    setEditedShot({ ...editedShot, meeting_video_prompt: e.target.value })
                  }
                  placeholder="Prompt for meeting video (arrival at set)"
                  className="mt-1 min-h-[80px] border-purple-200 focus:border-purple-500"
                />
              </div>

              <div>
                <label className="text-xs text-pink-600 font-semibold">Departure Video Prompt</label>
                <Textarea
                  value={editedShot.departure_video_prompt || ''}
                  onChange={(e) =>
                    setEditedShot({ ...editedShot, departure_video_prompt: e.target.value })
                  }
                  placeholder="Prompt for departure video (leaving set)"
                  className="mt-1 min-h-[80px] border-pink-200 focus:border-pink-500"
                />
              </div>
            </>
          ) : (
            <div>
              <label className="text-xs text-muted-foreground">
                Motion Prompt
              </label>
              <Textarea
                value={editedShot.motion_prompt}
                onChange={(e) =>
                  setEditedShot({ ...editedShot, motion_prompt: e.target.value })
                }
                className="mt-1 min-h-[120px]"
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-muted-foreground">Camera</label>
              <Input
                type="text"
                value={editedShot.camera}
                onChange={(e) =>
                  setEditedShot({ ...editedShot, camera: e.target.value })
                }
                className="mt-1"
              />
            </div>

            <div>
              <label className="text-xs text-muted-foreground">Narration</label>
              <Input
                type="text"
                value={editedShot.narration}
                onChange={(e) =>
                  setEditedShot({ ...editedShot, narration: e.target.value })
                }
                className="mt-1"
              />
            </div>
          </div>

          {scenes && scenes.length > 0 && (
            <div>
              <label className="text-xs text-muted-foreground">Scene</label>
              <Select
                value={(editedShot.scene_id !== undefined && editedShot.scene_id !== null) ? editedShot.scene_id.toString() : "null"}
                onValueChange={(val) => setEditedShot({ ...editedShot, scene_id: val === "null" ? null : parseInt(val) })}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select Scene" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="null">None (Unassigned)</SelectItem>
                  {scenes.map((_, idx) => (
                    <SelectItem key={idx} value={idx.toString()}>
                      Scene {idx + 1}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

        </div>
      </div>
    );
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "border rounded-lg p-4 bg-background hover:shadow-md transition-shadow relative",
        selected && "border-primary ring-1 ring-primary",
        isDragging && "shadow-xl",
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-0.5">
        <div className="flex items-center gap-2">
          {/* Drag Handle */}
          <button
            {...attributes}
            {...listeners}
            className="cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground transition-colors p-0.5 rounded hover:bg-muted/50"
            title="Drag to reorder"
          >
            <GripVertical className="w-4 h-4" />
          </button>
          {selectable && (
            <input
              type="checkbox"
              checked={selected}
              onChange={(e) => onSelectChange?.(e.target.checked)}
              className="w-3.5 h-3.5 rounded border-gray-300 text-primary focus:ring-primary shrink-0"
            />
          )}
          {showIndex && (
            <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">
              {shot.index}
            </span>
          )}
          {shot.is_flfi2v && (
            <span className="text-[9px] bg-gradient-to-r from-purple-500 to-pink-500 text-white px-2 py-0.5 rounded-full font-bold">
              Then VS Now
            </span>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-1.5 bg-muted/30 p-1 rounded-md">
          {/* Hidden file input for image/video upload */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,video/*"
            className="hidden"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              // Reset so the same file can be re-selected later
              e.target.value = "";

              // Detect file type
              const isVideo = file.type.startsWith('video/');
              const isImage = file.type.startsWith('image/');

              if (isVideo) {
                setIsVideoUploading(true);
                try {
                  // For FLFI2V shots, pass the current variant (meeting/departure)
                  const variant = shot.is_flfi2v ? activeVideoMode : undefined;
                  await uploadShotVideo.mutateAsync({ shotIndex: shot.index, file, variant });
                  setCacheBuster(Date.now());
                  toast.success("Video uploaded successfully", {
                    description: `Shot ${shot.index}${shot.is_flfi2v && variant ? ` (${variant.charAt(0).toUpperCase() + variant.slice(1)})` : ""} video has been uploaded.`,
                  });
                } catch (error) {
                  console.error("Failed to upload video:", error);
                  toast.error("Failed to upload video", {
                    description: "Please try again.",
                  });
                } finally {
                  setIsVideoUploading(false);
                }
              } else if (isImage) {
                setIsUploading(true);
                try {
                  // For FLFI2V shots, pass the current variant (THEN/NOW)
                  const variant = shot.is_flfi2v ? activeImageMode : undefined;
                  await uploadShotImage.mutateAsync({ shotIndex: shot.index, file, variant });
                  setCacheBuster(Date.now());
                  toast.success("Image uploaded successfully", {
                    description: `Shot ${shot.index}${shot.is_flfi2v && variant ? ` (${variant.toUpperCase()})` : ""} image has been uploaded.`,
                  });
                } catch (error) {
                  console.error("Failed to upload image:", error);
                  toast.error("Failed to upload image", {
                    description: "Please try again.",
                  });
                } finally {
                  setIsUploading(false);
                }
              } else {
                toast.warning("Unsupported file type", {
                  description: "Please select an image or video file.",
                });
              }
            }}
          />
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="p-1 hover:bg-green-50 text-green-600 rounded disabled:opacity-50"
            title="Refresh image from disk"
          >
            <RefreshCw
              className={cn("w-4 h-4", isRefreshing && "animate-spin")}
            />
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading || isVideoUploading}
            className={cn(
              "p-1 rounded disabled:opacity-50",
              viewMode === "image"
                ? "hover:bg-indigo-50 text-indigo-600"
                : "hover:bg-purple-50 text-purple-600"
            )}
            title={viewMode === "image" ? "Upload image from disk" : "Upload video from disk"}
          >
            {(isUploading || isVideoUploading) ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : viewMode === "image" ? (
              <Upload className="w-4 h-4" />
            ) : (
              <div className="relative">
                <Video className="w-4 h-4" />
                <Plus className="w-2 h-2 absolute -top-1 -right-1" />
              </div>
            )}
          </button>
          {(shot.is_flfi2v
            ? (shot.then_image_generated || shot.now_image_generated || shot.image_generated)
            : shot.image_generated) && (
              <button
                onClick={async () => {
                  try {
                    // For FLFI2V shots, pass the currently active image variant
                    const variant = shot.is_flfi2v ? activeImageMode : undefined;
                    await removeWatermark.mutateAsync({ shotIndex: shot.index, variant });
                    // Refresh the cache buster to show the updated image
                    setCacheBuster(Date.now());
                  } catch (error: any) {
                    console.error("Failed to remove watermark:", error);
                    const errorMessage = error?.response?.data?.detail || error?.message || "Unknown error";
                    alert(`Failed to remove watermark: ${errorMessage}\n\nPlease ensure the image file exists on disk.`);
                  }
                }}
                disabled={removeWatermark.isPending}
                className="p-1 hover:bg-teal-50 text-teal-600 rounded disabled:opacity-50"
                title={`Remove Gemini Watermark${shot.is_flfi2v ? ` from ${activeImageMode.toUpperCase()} image` : ''}`}
              >
                <Wand2 className={cn("w-4 h-4", removeWatermark.isPending && "animate-pulse")} />
              </button>
            )}
          <button
            onClick={() => setIsEditing(true)}
            className="p-1 hover:bg-muted rounded"
            title="Edit prompts"
          >
            <Edit3 className="w-4 h-4" />
          </button>
          <button
            onClick={handleRegenerateImage}
            disabled={regenerateImage.isPending}
            className="p-1 hover:bg-blue-50 text-blue-600 rounded disabled:opacity-50"
            title="Regenerate image"
          >
            <RotateCw className="w-4 h-4" />
          </button>
          <button
            onClick={handleRegenerateVideo}
            disabled={regenerateVideo.isPending}
            className="p-1 hover:bg-purple-50 text-purple-600 rounded disabled:opacity-50"
            title="Regenerate video"
          >
            <Video className="w-4 h-4" />
          </button>
          {hasMultipleVariations && (
            <button
              onClick={() => setShowGalleryModal(true)}
              className="p-1 hover:bg-amber-50 text-amber-600 rounded relative"
              title={`View ${viewMode} variations`}
            >
              <Layers className="w-4 h-4" />
              <span className="absolute -top-1 -right-1 bg-amber-500 text-white text-[9px] font-bold rounded-full w-3.5 h-3.5 flex items-center justify-center">
                {viewMode === "video" ? shot.video_paths?.length : shot.image_paths?.length}
              </span>
            </button>
          )}

          <div className="w-px h-6 bg-border mx-1 my-auto"></div>

          {onInsertBefore && (
            <button
              onClick={onInsertBefore}
              className="p-1 hover:bg-muted rounded"
              title="Insert a new shot before this one"
            >
              <Plus className="w-4 h-4" />
            </button>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="p-1 hover:bg-red-50 text-red-600 rounded"
              title="Delete this shot entirely"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      <hr className="mb-1.5 border-border/80" />

      {/* Status & Metadata */}
      <div className="flex items-center justify-between mb-3 text-xs">
        <div className="flex items-center gap-2">
          <span className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground truncate uppercase font-semibold tracking-wider">
            {shot.camera}
          </span>
          {/* FLFI2V Mode Toggle Buttons - Image or Video */}
          {shot.is_flfi2v && viewMode === "image" && (
            <div className="flex gap-1 bg-muted/50 p-0.5 rounded-md">
              <button
                onClick={() => setActiveImageMode('then')}
                className={cn(
                  "px-2 py-0.5 rounded text-[10px] font-semibold transition-all",
                  activeImageMode === 'then' ? "bg-purple-500 text-white" : "text-muted-foreground hover:text-foreground"
                )}
              >
                THEN
              </button>
              <button
                onClick={() => setActiveImageMode('now')}
                className={cn(
                  "px-2 py-0.5 rounded text-[10px] font-semibold transition-all",
                  activeImageMode === 'now' ? "bg-pink-500 text-white" : "text-muted-foreground hover:text-foreground"
                )}
              >
                NOW
              </button>
            </div>
          )}
          {shot.is_flfi2v && viewMode === "video" && (
            <div className="flex gap-1 bg-muted/50 p-0.5 rounded-md">
              <button
                onClick={() => setActiveVideoMode('meeting')}
                className={cn(
                  "px-2 py-0.5 rounded text-[10px] font-semibold transition-all",
                  activeVideoMode === 'meeting' ? "bg-purple-500 text-white" : "text-muted-foreground hover:text-foreground"
                )}
              >
                Meeting
              </button>
              <button
                onClick={() => setActiveVideoMode('departure')}
                className={cn(
                  "px-2 py-0.5 rounded text-[10px] font-semibold transition-all",
                  activeVideoMode === 'departure' ? "bg-pink-500 text-white" : "text-muted-foreground hover:text-foreground"
                )}
              >
                Departure
              </button>
            </div>
          )}
        </div>

        <div className="flex gap-2.5 ml-auto">
          <button
            onClick={() => setViewMode("image")}
            className={cn(
              "flex items-center gap-1 px-2 py-0.5 rounded transition-all hover:scale-105 active:scale-95",
              viewMode === "image"
                ? "bg-purple-500 text-white font-semibold"
                : "text-muted-foreground hover:text-foreground",
            )}
            title={(shot.is_flfi2v ? (shot.then_image_generated || shot.now_image_generated || shot.image_generated) : shot.image_generated)
              ? "Image Generated - Click to view"
              : "Image Not Generated - Click to view"}
          >
            <Image className="w-3 h-3" />
            {(shot.is_flfi2v ? (shot.then_image_generated || shot.now_image_generated || shot.image_generated) : shot.image_generated)
              ? "✓"
              : "○"}
          </button>
          <button
            onClick={() => setViewMode("video")}
            className={cn(
              "flex items-center gap-1 px-2 py-0.5 rounded transition-all hover:scale-105 active:scale-95",
              viewMode === "video"
                ? "bg-purple-500 text-white font-semibold"
                : "text-muted-foreground hover:text-foreground",
            )}
            title={(shot.is_flfi2v ? (shot.meeting_video_rendered || shot.departure_video_rendered || shot.video_rendered) : shot.video_rendered)
              ? "Video Rendered - Click to view"
              : "Video Not Rendered - Click to view"}
          >
            <Video className="w-3 h-3" />
            {(shot.is_flfi2v ? (shot.meeting_video_rendered || shot.departure_video_rendered || shot.video_rendered) : shot.video_rendered)
              ? "✓"
              : "○"}
          </button>
        </div>
      </div>

      {/* Media Preview */}
      <div className="mb-3 relative group">
        <div className="aspect-video bg-muted rounded overflow-hidden flex items-center justify-center relative">
          {isGenerating ? (
            <div className="absolute inset-0 bg-black/50 flex flex-col items-center justify-center rounded-lg z-10">
              <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin mb-2"></div>
              <span className="text-white font-medium">
                {progress === 0
                  ? "Initializing Generation..."
                  : progress !== undefined
                    ? `Generating... ${progress}%`
                    : "Generating..."}
              </span>
              {onCancel && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onCancel();
                  }}
                  className="mt-2 px-3 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded-full transition-colors"
                >
                  Cancel
                </button>
              )}
            </div>
          ) : isQueued ? (
            <div className="absolute inset-0 bg-black/50 flex flex-col items-center justify-center rounded-lg z-10">
              <Clock className="w-8 h-8 text-white/70 mb-2" />
              <span className="text-white/90 font-medium text-sm">
                Queued...
              </span>
              {onCancel && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onCancel();
                  }}
                  className="mt-2 px-3 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded-full transition-colors opacity-0 group-hover:opacity-100"
                >
                  Cancel
                </button>
              )}
            </div>
          ) : null}
          {viewMode === "video" && cachedVideoUrl ? (
            <video
              key={shot.is_flfi2v ? activeVideoMode : shot.video_path}
              src={cachedVideoUrl}
              poster={cachedImageUrl}
              controls
              autoPlay
              muted
              loop
              playsInline
              className="w-full h-full object-cover"
            />
          ) : cachedImageUrl ? (
            <img
              key={shot.is_flfi2v ? `${activeImageMode}-${activeVideoMode}` : shot.image_path}
              src={cachedImageUrl}
              alt={`Shot ${shot.index}`}
              className="w-full h-full object-cover cursor-pointer hover:opacity-90 transition-opacity"
              onClick={() => {
                // Get the currently displayed image path based on FLFI2V mode
                const currentImagePath = shot.is_flfi2v
                  ? (activeImageMode === 'then'
                    ? shot.then_image_path || shot.now_image_path || shot.image_path
                    : shot.now_image_path || shot.then_image_path || shot.image_path)
                  : shot.image_path;

                const activeIdx = fsImages.indexOf(currentImagePath ?? "");
                openFullscreen(activeIdx >= 0 ? activeIdx : 0);
              }}
              title="Click to view full screen"
            />
          ) : (
            <span className="text-muted-foreground text-xs">
              No media available
            </span>
          )}
        </div>
      </div>

      {/* Prompts */}
      <div className="space-y-2 text-sm">
        {/* Image Prompt Section */}
        <div className="p-2 bg-muted rounded">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1.5">
              <div className="text-xs text-muted-foreground uppercase font-bold tracking-wider">
                Image Prompt
                {shot.is_flfi2v && (
                  <span className={cn(
                    "ml-2 text-[9px] px-1.5 py-0.5 rounded font-semibold",
                    activeImageMode === 'then' ? "bg-purple-500 text-white" : "bg-pink-500 text-white"
                  )}>
                    {activeImageMode === 'then' ? 'THEN' : 'NOW'}
                  </span>
                )}
              </div>
              <button
                onClick={() => setIsImagePromptExpanded(!isImagePromptExpanded)}
                className="p-0.5 hover:bg-background rounded text-muted-foreground hover:text-foreground transition-colors"
                title={isImagePromptExpanded ? "Collapse" : "Expand"}
              >
                {isImagePromptExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              </button>
            </div>
            <button
              onClick={() => {
                const promptToCopy = shot.is_flfi2v
                  ? (activeImageMode === 'then' ? shot.then_image_prompt : shot.now_image_prompt) || shot.image_prompt
                  : shot.image_prompt;
                navigator.clipboard.writeText(promptToCopy || "");
                setCopiedField("image");
                setTimeout(() => setCopiedField(null), 1500);
              }}
              className="p-0.5 hover:bg-background rounded text-muted-foreground hover:text-foreground transition-colors"
              title="Copy image prompt"
            >
              {copiedField === "image" ? (
                <ClipboardCheck className="w-3.5 h-3.5 text-green-500" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
          <div className={cn("text-sm", !isImagePromptExpanded && "line-clamp-2")}>
            {shot.is_flfi2v
              ? (activeImageMode === 'then' ? (shot.then_image_prompt || shot.image_prompt) : (shot.now_image_prompt || shot.image_prompt))
              : shot.image_prompt}
          </div>
        </div>

        {/* Motion Prompt Section */}
        <div key={shot.is_flfi2v ? `motion-section-${activeVideoMode}` : 'motion-section'} className="p-2 bg-muted rounded">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1.5">
              <div className="text-xs text-muted-foreground uppercase font-bold tracking-wider">
                Motion Prompt
                {shot.is_flfi2v && (
                  <span className={cn(
                    "ml-2 text-[9px] px-1.5 py-0.5 rounded font-semibold",
                    activeVideoMode === 'meeting' ? "bg-purple-500 text-white" : "bg-pink-500 text-white"
                  )}>
                    {activeVideoMode === 'meeting' ? 'MEETING' : 'DEPARTURE'}
                  </span>
                )}
              </div>
              <button
                onClick={() => setIsMotionPromptExpanded(!isMotionPromptExpanded)}
                className="p-0.5 hover:bg-background rounded text-muted-foreground hover:text-foreground transition-colors"
                title={isMotionPromptExpanded ? "Collapse" : "Expand"}
              >
                {isMotionPromptExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              </button>
            </div>
            <button
              onClick={() => {
                const promptToCopy = shot.is_flfi2v
                  ? (activeVideoMode === 'meeting' ? shot.meeting_video_prompt : shot.departure_video_prompt) || shot.motion_prompt
                  : shot.motion_prompt;
                navigator.clipboard.writeText(promptToCopy || "");
                setCopiedField("motion");
                setTimeout(() => setCopiedField(null), 1500);
              }}
              className="p-0.5 hover:bg-background rounded text-muted-foreground hover:text-foreground transition-colors"
              title="Copy motion prompt"
            >
              {copiedField === "motion" ? (
                <ClipboardCheck className="w-3.5 h-3.5 text-green-500" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
          <div key={shot.is_flfi2v ? `motion-${activeVideoMode}` : 'motion'} className={cn("text-sm", !isMotionPromptExpanded && "line-clamp-2")}>
            {shot.is_flfi2v
              ? (activeVideoMode === 'meeting' ? (shot.meeting_video_prompt || shot.motion_prompt) : (shot.departure_video_prompt || shot.motion_prompt))
              : shot.motion_prompt}
          </div>
        </div>
      </div>

      {/* Narration */}
      {shot.narration && (
        <div className="mt-2 text-sm italic text-muted-foreground">
          "{shot.narration}"
        </div>
      )}

      {/* Regeneration Modal */}
      {showRegenModal && (
        <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4">
          <div className="bg-background rounded-lg shadow-xl max-w-sm w-full p-6 relative">
            <button
              onClick={() => setShowRegenModal(null)}
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
            >
              <X className="w-5 h-5" />
            </button>

            <h2 className="text-lg font-semibold mb-4">
              Regenerate {showRegenModal === "image" ? "Image" : "Video"}
            </h2>

            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Input
                  type="checkbox"
                  id="regen-force"
                  checked={regenForce}
                  onChange={(e) => setRegenForce(e.target.checked)}
                  className="w-4 h-4 mr-2"
                />
                <label htmlFor="regen-force" className="text-sm">
                  Force regeneration (ignore cache)
                </label>
              </div>

              {showRegenModal === "image" && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1">
                      Generation Mode
                    </label>
                    <Select
                      value={regenImageMode}
                      onValueChange={(val) => setRegenImageMode(val)}
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

                  {regenImageMode === "comfyui" && (
                    <>
                      <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1">
                          Workflow
                        </label>
                        <Select
                          value={regenImageWorkflow}
                          onValueChange={(val) => setRegenImageWorkflow(val)}
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

                      <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1">
                          Noise Seed (Optional)
                        </label>
                        <Input
                          type="number"
                          value={regenSeed}
                          onChange={(e) =>
                            setRegenSeed(
                              e.target.value === ""
                                ? ""
                                : parseInt(e.target.value),
                            )
                          }
                          placeholder="Random"
                        />
                        <p className="text-[10px] text-muted-foreground mt-1">
                          Leave blank for automatic seed (1 for 1st version,
                          random otherwise).
                        </p>
                      </div>
                    </>
                  )}

                  {/* Prompt Override — visible for ALL image modes */}
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1">
                      Prompt Override
                    </label>
                    <Textarea
                      value={regenPromptOverride}
                      onChange={(e) => setRegenPromptOverride(e.target.value)}
                      rows={4}
                      placeholder="Leave blank to use the shot's saved image prompt…"
                      className="text-xs resize-y"
                    />
                    <p className="text-[10px] text-muted-foreground mt-1">
                      Edits here are one-time only — they won't change the saved shot prompt.
                    </p>
                  </div>
                </>
              )}

              {showRegenModal === "video" && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1">
                      Generation Mode
                    </label>
                    <Select
                      value={regenVideoMode}
                      onValueChange={(val) => {
                        setRegenVideoMode(val);
                        localStorage.setItem(`video_mode_${projectId}`, val);
                      }}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select Mode" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="comfyui">ComfyUI (Local)</SelectItem>
                        <SelectItem value="geminiweb">
                          GeminiWeb - Gemini Web (Browser)
                        </SelectItem>
                        <SelectItem value="flowweb">
                          FlowWeb - Google Flow (Browser)
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {regenVideoMode === "comfyui" && (
                    <div>
                      <label className="block text-xs font-medium text-muted-foreground mb-1">
                        Video Workflow
                      </label>
                      <Select
                        value={regenVideoWorkflow}
                        onValueChange={(val) => setRegenVideoWorkflow(val)}
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
                    </div>
                  )}

                  <div className="space-y-2 mt-4 border-t pt-4">
                    <label className="block text-[10px] font-medium text-muted-foreground mb-1">
                      Append Image Prompt to Motion Prompt
                    </label>
                    <Select
                      value={appendImagePrompt}
                      onValueChange={(val) => setAppendImagePrompt(val)}
                    >
                      <SelectTrigger className="h-8 text-xs">
                        <SelectValue placeholder="Select Position" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="default">Use Config Default</SelectItem>
                        <SelectItem value="none">None (Do Not Append)</SelectItem>
                        <SelectItem value="start">Start (Image + Motion)</SelectItem>
                        <SelectItem value="end">End (Motion + Image)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <Button variant="outline" onClick={() => setShowRegenModal(null)}>
                Cancel
              </Button>
              <Button
                onClick={handleRegenSubmit}
                disabled={
                  regenerateImage.isPending || regenerateVideo.isPending
                }
                className="flex items-center gap-2"
              >
                {regenerateImage.isPending || regenerateVideo.isPending ? (
                  <>
                    <RotateCw className="w-3 h-3 animate-spin" />
                    Processing...
                  </>
                ) : (
                  "Start"
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Fullscreen Carousel Modal — navigates through all image_paths */}
      {fullscreenVariationIndex !== null && fsUrl && (
        <div
          className="fixed inset-0 bg-black/92 z-[70] flex items-center justify-center p-4"
          onClick={closeFullscreen}
        >
          {viewMode === "video" ? (
            <video
              src={fsUrl}
              autoPlay
              controls
              loop
              className="max-w-full max-h-full object-contain select-none"
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <img
              src={fsUrl}
              alt={`Shot ${shot.index} — ${fullscreenVariationIndex + 1} / ${fsTotal}`}
              className="max-w-full max-h-full object-contain select-none"
              onClick={(e) => e.stopPropagation()}
            />
          )}

          {/* Counter badge */}
          {fsTotal > 1 && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-black/60 text-white text-sm px-3 py-1 rounded-full backdrop-blur-sm">
              {fullscreenVariationIndex + 1} / {fsTotal}
            </div>
          )}

          {/* Close */}
          <button
            onClick={(e) => { e.stopPropagation(); closeFullscreen(); }}
            className="absolute top-4 right-4 text-white/70 hover:text-white p-2 transition-colors"
          >
            <X className="w-8 h-8" />
          </button>

          {/* Prev */}
          {fsTotal > 1 && (
            <button
              onClick={(e) => { e.stopPropagation(); fsPrev(); }}
              className="absolute left-4 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/80 text-white p-3 rounded-full transition-colors"
              title="Previous (←)"
            >
              <ChevronLeft className="w-6 h-6" />
            </button>
          )}

          {/* Next */}
          {fsTotal > 1 && (
            <button
              onClick={(e) => { e.stopPropagation(); fsNext(); }}
              className="absolute right-4 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/80 text-white p-3 rounded-full transition-colors"
              title="Next (→)"
            >
              <ChevronRight className="w-6 h-6" />
            </button>
          )}
        </div>
      )}

      {/* Media Gallery Modal */}
      {showGalleryModal && hasMultipleVariations && (() => {
        const paths = viewMode === "video" ? (shot.video_paths ?? []) : (shot.image_paths ?? []);
        const activePath = viewMode === "video" ? shot.video_path : shot.image_path;
        const mediaType = viewMode === "video" ? "Video" : "Image";

        return (
          <div className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4">
            <div className="bg-background rounded-xl shadow-2xl max-w-3xl w-full max-h-[80vh] flex flex-col relative">
              <div className="flex items-center justify-between p-4 border-b">
                <h2 className="text-lg font-semibold">
                  Shot {shot.index} — {mediaType} Variations ({paths.length})
                </h2>
                <button
                  onClick={() => setShowGalleryModal(false)}
                  className="text-muted-foreground hover:text-foreground p-1"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="overflow-y-auto p-4">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                  {paths.map((path, idx) => {
                    const url = getMediaUrl(path);
                    const cachedUrl = bustCache(url);
                    const isActive = path === activePath;
                    return (
                      <div
                        key={idx}
                        className={cn(
                          "relative group rounded-lg overflow-hidden border-2 transition-all block",
                          isActive
                            ? "border-primary ring-2 ring-primary/30"
                            : "border-transparent hover:border-muted-foreground/30",
                        )}
                      >
                        <div className="aspect-video bg-muted flex items-center justify-center">
                          {viewMode === "video" ? (
                            <video
                              src={cachedUrl}
                              className="w-full h-full object-cover"
                              muted
                              loop
                              onMouseEnter={(e) => { e.currentTarget.play(); }}
                              onMouseLeave={(e) => { e.currentTarget.pause(); }}
                            />
                          ) : (
                            <img
                              src={cachedUrl}
                              alt={`Variation ${idx + 1}`}
                              className="w-full h-full object-cover"
                            />
                          )}
                        </div>

                        {/* Hover overlay */}
                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/50 transition-colors">
                          {/* Fullscreen button — top right */}
                          <button
                            onClick={() => openFullscreen(idx)}
                            className="absolute top-2 right-2 p-1.5 bg-black/60 text-white rounded-md opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/80"
                            title="View fullscreen"
                          >
                            <Maximize2 className="w-3.5 h-3.5" />
                          </button>

                          {/* Bottom bar: filename + select/active + delete */}
                          <div className="absolute bottom-0 left-0 right-0 p-2 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-between gap-1">
                            {/* Delete button — always visible on hover */}
                            <button
                              onClick={async () => {
                                if (!confirm(`Delete this variation? This cannot be undone.`)) return;
                                try {
                                  let remaining = 0;
                                  if (viewMode === "video") {
                                    const result = await deleteVariationVideo.mutateAsync({
                                      shotIndex: shot.index,
                                      videoPath: path,
                                    });
                                    remaining = result.remaining;
                                  } else {
                                    const result = await deleteVariation.mutateAsync({
                                      shotIndex: shot.index,
                                      imagePath: path,
                                    });
                                    remaining = result.remaining;
                                  }

                                  setCacheBuster(Date.now());
                                  // Close gallery if no variations remain
                                  if (remaining === 0) setShowGalleryModal(false);
                                } catch (error) {
                                  console.error("Failed to delete variation:", error);
                                  alert("Failed to delete variation. Please try again.");
                                }
                              }}
                              disabled={viewMode === "video" ? deleteVariationVideo.isPending : deleteVariation.isPending}
                              className="p-1.5 bg-red-600/80 text-white rounded-md hover:bg-red-600 disabled:opacity-50 flex-shrink-0"
                              title="Delete this variation"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>

                            {/* Select / Active badge */}
                            {isActive ? (
                              <span className="text-xs bg-primary text-primary-foreground px-2 py-0.5 rounded-full font-medium flex items-center gap-1 ml-auto">
                                <Check className="w-3 h-3" /> Active
                              </span>
                            ) : (
                              <button
                                onClick={async () => {
                                  try {
                                    if (viewMode === "video") {
                                      await selectVideo.mutateAsync({
                                        shotIndex: shot.index,
                                        videoPath: path,
                                      });
                                    } else {
                                      await selectImage.mutateAsync({
                                        shotIndex: shot.index,
                                        imagePath: path,
                                      });
                                    }
                                    setCacheBuster(Date.now());
                                    setShowGalleryModal(false);
                                  } catch (error) {
                                    console.error("Failed to select variation:", error);
                                    alert("Failed to select variation. Please try again.");
                                  }
                                }}
                                disabled={viewMode === "video" ? selectVideo.isPending : selectImage.isPending}
                                className="text-xs bg-white text-black px-2 py-0.5 rounded-full font-medium hover:bg-white/90 disabled:opacity-50 ml-auto"
                              >
                                Select
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
