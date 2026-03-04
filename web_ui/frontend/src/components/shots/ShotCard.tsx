/**
 * ShotCard component - Individual shot with editing and regeneration
 */
import { useState, useRef } from "react";
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
} from "lucide-react";
import { Shot } from "@/types";
import {
  useUpdateShot,
  useRegenerateImage,
  useRegenerateVideo,
  useSelectImage,
  useRemoveWatermark,
  useUploadShotImage,
  useDeleteVariationImage,
} from "@/hooks/useShots";
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
  sessionId: string;
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
}

export function ShotCard({
  shot,
  sessionId,
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
}: ShotCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedShot, setEditedShot] = useState(shot);
  const [viewMode, setViewMode] = useState<"image" | "video">(
    shot.video_rendered && shot.video_path ? "video" : "image",
  );

  // Regeneration modal state
  const [showRegenModal, setShowRegenModal] = useState<
    "image" | "video" | null
  >(null);
  const [showFullscreenImage, setShowFullscreenImage] = useState(false);
  const [regenForce, setRegenForce] = useState(true);
  const [regenImageMode, setRegenImageMode] = useState("comfyui");
  const [regenImageWorkflow, setRegenImageWorkflow] = useState("flux2");
  const [regenVideoWorkflow, setRegenVideoWorkflow] = useState(
    "workflow/video/wan22_workflow.json",
  );
  const [regenSeed, setRegenSeed] = useState<number | "">("");

  // ... rest of the hook setup ...
  const queryClient = useQueryClient();
  const updateShot = useUpdateShot(sessionId, shot.index);
  const regenerateImage = useRegenerateImage(sessionId);
  const regenerateVideo = useRegenerateVideo(sessionId);
  const selectImage = useSelectImage(sessionId);
  const removeWatermark = useRemoveWatermark(sessionId);
  const uploadShotImage = useUploadShotImage(sessionId);
  const deleteVariation = useDeleteVariationImage(sessionId);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [cacheBuster, setCacheBuster] = useState(Date.now());
  const [showGalleryModal, setShowGalleryModal] = useState(false);
  const [fullscreenVariationUrl, setFullscreenVariationUrl] = useState<string | null>(null);

  const hasMultipleImages = (shot.image_paths?.length ?? 0) > 1;

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await queryClient.invalidateQueries({ queryKey: ["shots", sessionId] });
    await queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
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
      });
      setIsEditing(false);
    } catch (error) {
      console.error("Failed to update shot:", error);
      alert("Failed to update shot. Please try again.");
    }
  };

  const handleCancel = () => {
    setEditedShot(shot);
    setIsEditing(false);
  };

  const handleRegenerateImage = async () => {
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
        regenerateImage.mutate({
          shotIndex: shot.index,
          force: regenForce,
          imageMode: regenImageMode,
          imageWorkflow: regenImageWorkflow,
          seed: regenSeed === "" ? undefined : regenSeed,
        });
      } else if (type === "video") {
        regenerateVideo.mutate({
          shotIndex: shot.index,
          force: regenForce,
          videoWorkflow: regenVideoWorkflow,
        });
        setViewMode("video");
      }
      setCacheBuster(Date.now());
    } catch (error) {
      console.error(`Failed to trigger regeneration:`, error);
    }
  };

  const imageUrl = getMediaUrl(shot.image_path);
  const videoUrl = getMediaUrl(shot.video_path);

  // Append cache-busting param so browser fetches the latest file from disk
  const bustCache = (url: string) =>
    url ? `${url}${url.includes("?") ? "&" : "?"}t=${cacheBuster}` : "";
  const cachedImageUrl = bustCache(imageUrl);
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
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "border rounded-lg p-4 bg-background hover:shadow-md transition-shadow relative",
        selected && "border-primary ring-1 ring-primary",
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          {selectable && (
            <input
              type="checkbox"
              checked={selected}
              onChange={(e) => onSelectChange?.(e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
            />
          )}
          <div className="flex-1">
            {showIndex && (
              <span className="text-sm font-medium text-muted-foreground">
                Shot {shot.index}
              </span>
            )}
            <div className="flex gap-2 mt-1">
              <span className="text-xs bg-muted px-2 py-0.5 rounded">
                {shot.camera}
              </span>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          {/* Hidden file input for image upload */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              // Reset so the same file can be re-selected later
              e.target.value = "";
              setIsUploading(true);
              try {
                await uploadShotImage.mutateAsync({ shotIndex: shot.index, file });
                setCacheBuster(Date.now());
              } catch (error) {
                console.error("Failed to upload image:", error);
                alert("Failed to upload image. Please try again.");
              } finally {
                setIsUploading(false);
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
            disabled={isUploading}
            className="p-1 hover:bg-indigo-50 text-indigo-600 rounded disabled:opacity-50"
            title="Upload image from disk"
          >
            {isUploading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Upload className="w-4 h-4" />
            )}
          </button>
          {shot.image_generated && (
            <button
              onClick={async () => {
                try {
                  await removeWatermark.mutateAsync(shot.index);
                  // Refresh the cache buster to show the updated image
                  setCacheBuster(Date.now());
                } catch (error) {
                  console.error("Failed to remove watermark:", error);
                  alert("Failed to remove watermark. Ensure the image exists.");
                }
              }}
              disabled={removeWatermark.isPending}
              className="p-1 hover:bg-teal-50 text-teal-600 rounded disabled:opacity-50"
              title="Remove Gemini Watermark"
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
          {hasMultipleImages && (
            <button
              onClick={() => setShowGalleryModal(true)}
              className="p-1 hover:bg-amber-50 text-amber-600 rounded relative"
              title="View image variations"
            >
              <Layers className="w-4 h-4" />
              <span className="absolute -top-1 -right-1 bg-amber-500 text-white text-[9px] font-bold rounded-full w-3.5 h-3.5 flex items-center justify-center">
                {shot.image_paths.length}
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

      {/* Status */}
      <div className="flex gap-3 text-xs mb-3">
        <span
          className={cn(
            "flex items-center gap-1",
            shot.image_generated ? "text-green-600" : "text-gray-400",
          )}
        >
          <Image className="w-3 h-3" />
          Image: {shot.image_generated ? "✓" : "○"}
        </span>
        <span
          className={cn(
            "flex items-center gap-1",
            shot.video_rendered ? "text-green-600" : "text-gray-400",
          )}
        >
          <Video className="w-3 h-3" />
          Video: {shot.video_rendered ? "✓" : "○"}
        </span>
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
              src={cachedImageUrl}
              alt={`Shot ${shot.index}`}
              className="w-full h-full object-cover cursor-pointer hover:opacity-90 transition-opacity"
              onClick={() => setShowFullscreenImage(true)}
              title="Click to view full screen"
            />
          ) : (
            <span className="text-muted-foreground text-xs">
              No media available
            </span>
          )}
        </div>

        {/* Media Toggle Controls */}
        {shot.image_path && shot.video_path && (
          <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity bg-black/50 backdrop-blur-sm p-1 rounded-md">
            <button
              onClick={() => setViewMode("image")}
              className={cn(
                "p-1.5 rounded transition-colors",
                viewMode === "image"
                  ? "bg-white text-black"
                  : "text-white hover:bg-white/20",
              )}
              title="View Image"
            >
              <Image className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode("video")}
              className={cn(
                "p-1.5 rounded transition-colors",
                viewMode === "video"
                  ? "bg-white text-black"
                  : "text-white hover:bg-white/20",
              )}
              title="View Video"
            >
              <Video className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Prompts */}
      <div className="space-y-2 text-sm">
        <div className="p-2 bg-muted rounded">
          <div className="text-xs text-muted-foreground mb-1">Image Prompt</div>
          <div className="line-clamp-2">{shot.image_prompt}</div>
        </div>
        <div className="p-2 bg-muted rounded">
          <div className="text-xs text-muted-foreground mb-1">
            Motion Prompt
          </div>
          <div className="line-clamp-2">{shot.motion_prompt}</div>
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
                            <SelectItem value="flux2">
                              Flux 2 (High Quality)
                            </SelectItem>
                            <SelectItem value="flux">
                              Flux (Standard)
                            </SelectItem>
                            <SelectItem value="sdxl">SDXL</SelectItem>
                            <SelectItem value="default">Default</SelectItem>
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
                </>
              )}

              {showRegenModal === "video" && (
                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1">
                    Video Workflow
                  </label>
                  <Input
                    type="text"
                    value={regenVideoWorkflow}
                    onChange={(e) => setRegenVideoWorkflow(e.target.value)}
                  />
                </div>
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

      {/* Fullscreen Image Modal — main shot image OR gallery variation */}
      {(showFullscreenImage || fullscreenVariationUrl) && (cachedImageUrl || fullscreenVariationUrl) && (
        <div
          className="fixed inset-0 bg-black/90 z-[70] flex items-center justify-center p-4 cursor-zoom-out"
          onClick={() => { setShowFullscreenImage(false); setFullscreenVariationUrl(null); }}
        >
          <img
            src={fullscreenVariationUrl ?? cachedImageUrl}
            alt={`Shot ${shot.index} Fullscreen`}
            className="max-w-full max-h-full object-contain"
          />
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowFullscreenImage(false);
              setFullscreenVariationUrl(null);
            }}
            className="absolute top-4 right-4 text-white/70 hover:text-white p-2 transition-colors"
          >
            <X className="w-8 h-8" />
          </button>
        </div>
      )}

      {/* Image Gallery Modal */}
      {showGalleryModal && hasMultipleImages && (
        <div className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4">
          <div className="bg-background rounded-xl shadow-2xl max-w-3xl w-full max-h-[80vh] flex flex-col relative">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-lg font-semibold">
                Shot {shot.index} — Image Variations ({shot.image_paths.length})
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
                {shot.image_paths.map((imgPath, idx) => {
                  const url = getMediaUrl(imgPath);
                  const cachedUrl = bustCache(url);
                  const isActive = imgPath === shot.image_path;
                  return (
                    <div
                      key={idx}
                      className={cn(
                        "relative group rounded-lg overflow-hidden border-2 transition-all",
                        isActive
                          ? "border-primary ring-2 ring-primary/30"
                          : "border-transparent hover:border-muted-foreground/30",
                      )}
                    >
                      <div className="aspect-video bg-muted">
                        <img
                          src={cachedUrl}
                          alt={`Variation ${idx + 1}`}
                          className="w-full h-full object-cover"
                        />
                      </div>

                      {/* Hover overlay */}
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/50 transition-colors">
                        {/* Fullscreen button — top right */}
                        <button
                          onClick={() => setFullscreenVariationUrl(cachedUrl)}
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
                                const result = await deleteVariation.mutateAsync({
                                  shotIndex: shot.index,
                                  imagePath: imgPath,
                                });
                                setCacheBuster(Date.now());
                                // Close gallery if no variations remain
                                if (result.remaining === 0) setShowGalleryModal(false);
                              } catch (error) {
                                console.error("Failed to delete variation:", error);
                                alert("Failed to delete variation. Please try again.");
                              }
                            }}
                            disabled={deleteVariation.isPending}
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
                                  await selectImage.mutateAsync({
                                    shotIndex: shot.index,
                                    imagePath: imgPath,
                                  });
                                  setCacheBuster(Date.now());
                                  setShowGalleryModal(false);
                                } catch (error) {
                                  console.error("Failed to select image:", error);
                                  alert("Failed to select image. Please try again.");
                                }
                              }}
                              disabled={selectImage.isPending}
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
      )}
    </div>
  );
}
