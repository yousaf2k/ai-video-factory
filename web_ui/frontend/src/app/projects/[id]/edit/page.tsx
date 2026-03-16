/**
 * Project editor page - Story and shot editing
 */
"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getMediaUrl } from "@/lib/utils";
import { Image as ImageIcon, Video as VideoIcon } from "lucide-react";
import { useProject } from "@/hooks/useProjects";
import { useUpdateStory, useRegenerateStory } from "@/hooks/useStory";
import { useShots, useReplanShots } from "@/hooks/useShots";
import { useAgents } from "@/hooks/useAgents";
import { SceneList } from "@/components/scenes/SceneList";
import { ShotGrid } from "@/components/shots/ShotGrid";
import { Scene, Story, Shot } from "@/types";
import { api } from "@/services/api";
import { Save, RefreshCw, X, BookOpen, Film, ChevronLeft, ChevronRight, Play } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useConfirmDialog, ConfirmDialog } from "@/components/ui/confirm-dialog";
import { toast } from "sonner";

export default function ProjectEditPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { data: project, isLoading, error } = useProject(projectId);
  const { data: shots } = useShots(projectId);
  const { data: agents } = useAgents();

  const updateStoryMutation = useUpdateStory(projectId);
  const regenerateStoryMutation = useRegenerateStory(projectId);
  const replanShotsMutation = useReplanShots(projectId);
  const confirmDialog = useConfirmDialog();

  // Local state for story editing
  const [story, setStory] = useState<Story | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [activeTab, setActiveTab] = useState("shots");
  // Media dialog states
  const [showImagesDialog, setShowImagesDialog] = useState(false);
  const [showVideosDialog, setShowVideosDialog] = useState(false);
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null);
  const [selectedVideoIndex, setSelectedVideoIndex] = useState<number | null>(null);

  // Modal states
  const [showRegenStoryModal, setShowRegenStoryModal] = useState(false);
  const [showReplanShotsModal, setShowReplanShotsModal] = useState(false);

  // Selection states
  const [selectedStoryAgent, setSelectedStoryAgent] = useState("default");
  const [selectedShotsAgent, setSelectedShotsAgent] = useState("default");
  const [maxShots, setMaxShots] = useState(0);

  // Initialize story when project loads
  if (project && project.story && !story) {
    setStory(project.story);
  }

  // Load backend config for replan shots dialog default values
  useEffect(() => {
    api
      .getConfig()
      .then((cfg) => {
        setMaxShots(cfg.default_max_shots ?? 0);
      })
      .catch(console.error);
  }, []);

  const handleUpdateScene = async (index: number, updatedScene: Scene) => {
    if (!story) return;

    const confirmed = await confirmDialog.showDialog({
      title: "Save Scene Changes",
      description: `Do you want to save changes to "${updatedScene.location || 'this scene'}"?`,
      type: "update",
    });

    if (!confirmed) return;

    const newScenes = [...story.scenes];
    newScenes[index] = updatedScene;
    const updatedStory = {
      ...story,
      scenes: newScenes,
    };

    // Update local state immediately for responsive UI
    setStory(updatedStory);
    setHasChanges(false); // Clear hasChanges since we're saving immediately

    // Automatically save to backend
    try {
      await updateStoryMutation.mutateAsync(updatedStory);
      toast.success("Scene updated successfully", {
        description: `"${updatedScene.location || 'Scene ' + (index + 1)}" has been saved.`,
        
      });
    } catch (error) {
      console.error("Failed to update scene:", error);
      await confirmDialog.showDialog({
        title: "Error",
        description: "Failed to update scene. Please try again.",
        type: "warning",
      });
      // Revert local state on error
      setStory(story);
      setHasChanges(true);
    }
  };

  const handleDeleteScene = async (index: number) => {
    if (!story) return;

    const sceneToDelete = story.scenes[index];
    const confirmed = await confirmDialog.showDialog({
      title: "Delete Scene",
      description: `Are you sure you want to delete "${sceneToDelete?.location || 'this scene'}"? This action cannot be undone.`,
      type: "delete",
      confirmText: "Delete Scene",
    });

    if (!confirmed) return;

    const newScenes = story.scenes.filter((_, i) => i !== index);
    const updatedStory = {
      ...story,
      scenes: newScenes,
    };

    // Update local state immediately for responsive UI
    setStory(updatedStory);
    setHasChanges(false); // Clear hasChanges since we're saving immediately

    // Automatically save to backend
    try {
      await updateStoryMutation.mutateAsync(updatedStory);
      toast.success("Scene deleted successfully", {
        description: `"${sceneToDelete?.location || 'Scene ' + (index + 1)}" has been removed.`,
      });
    } catch (error) {
      console.error("Failed to delete scene:", error);
      await confirmDialog.showDialog({
        title: "Error",
        description: "Failed to delete scene. Please try again.",
        type: "warning",
      });
      // Revert local state on error
      setStory(story);
      setHasChanges(true);
    }
  };

  const handleReorderScenes = async (newScenes: Scene[]) => {
    if (!story) return;

    const confirmed = await confirmDialog.showDialog({
      title: "Reorder Scenes",
      description: "Do you want to save the new scene order?",
      type: "reorder",
    });

    if (!confirmed) return;

    const updatedStory = {
      ...story,
      scenes: newScenes,
    };

    // Update local state immediately for responsive UI
    setStory(updatedStory);
    setHasChanges(false); // Clear hasChanges since we're saving immediately

    // Automatically save to backend
    try {
      await updateStoryMutation.mutateAsync(updatedStory);
      toast.success("Scenes reordered successfully", {
        description: "The scene order has been updated.",
      });
    } catch (error) {
      console.error("Failed to reorder scenes:", error);
      await confirmDialog.showDialog({
        title: "Error",
        description: "Failed to reorder scenes. Please try again.",
        type: "warning",
      });
      // Revert local state on error
      setStory(story);
      setHasChanges(true);
    }
  };

  const handleAddScene = async () => {
    if (!story) return;

    const confirmed = await confirmDialog.showDialog({
      title: "Add New Scene",
      description: "Do you want to add a new scene to the story?",
      type: "add",
    });

    if (!confirmed) return;

    const newScene: Scene = {
      location: "New Location",
      characters: "Characters",
      action: "Action happening",
      emotion: "Emotional tone",
      narration: "Narration text",
      scene_duration: 30,
    };

    const updatedStory = {
      ...story,
      scenes: [...story.scenes, newScene],
    };

    // Update local state immediately for responsive UI
    setStory(updatedStory);
    setHasChanges(false); // Clear hasChanges since we're saving immediately

    // Automatically save to backend
    try {
      await updateStoryMutation.mutateAsync(updatedStory);
      toast.success("Scene added successfully", {
        description: "New scene has been added to the story.",
      });
    } catch (error) {
      console.error("Failed to add scene:", error);
      await confirmDialog.showDialog({
        title: "Error",
        description: "Failed to add scene. Please try again.",
        type: "warning",
      });
      // Revert local state on error
      setStory(story);
      setHasChanges(true);
    }
  };

  const handleSaveStory = async () => {
    if (!story) return;

    try {
      await updateStoryMutation.mutateAsync(story);
      setHasChanges(false);
      alert("Story updated successfully!");
    } catch (error) {
      console.error("Failed to update story:", error);
      alert("Failed to update story. Please try again.");
    }
  };

  const handleRegenStory = async () => {
    try {
      await regenerateStoryMutation.mutateAsync(selectedStoryAgent);
      setShowRegenStoryModal(false);
      alert("Story regeneration started. The page will update when complete.");
    } catch (error) {
      console.error("Failed to regenerate story:", error);
      alert("Failed to regenerate story. Please try again.");
    }
  };

  const handleReplanShots = async () => {
    try {
      await replanShotsMutation.mutateAsync({
        max_shots: maxShots,
        shots_agent: selectedShotsAgent,
      });
      setShowReplanShotsModal(false);
      alert("Shot re-planning started.");
    } catch (error) {
      console.error("Failed to re-plan shots:", error);
      alert("Failed to re-plan shots. Please try again.");
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading project...</div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-500">Error loading project</div>
      </div>
    );
  }

  if (!story) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-12">
          <h2 className="text-xl font-semibold mb-4">No Story Found</h2>
          <p className="text-muted-foreground mb-6">
            This project doesn't have a story yet. Generate a story first.
          </p>
          <Link
            href={`/projects/${projectId}`}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            Back to Project
          </Link>
        </div>
      </div>
    );
  }

  // Calculate total duration
  const totalDuration = story.scenes.reduce(
    (sum, scene) => sum + (scene.scene_duration || 0),
    0,
  );

  // Flat media lists for Dialogs
  const allImages = shots?.flatMap(shot => {
    const images = [];
    if (shot.image_path) images.push({ path: shot.image_path, label: `Shot ${shot.index}` });
    if (shot.then_image_path) images.push({ path: shot.then_image_path, label: `Shot ${shot.index} (Then)` });
    if (shot.now_image_path) images.push({ path: shot.now_image_path, label: `Shot ${shot.index} (Now)` });
    return images;
  }) || [];

  const allVideos = shots?.flatMap(shot => {
    const vids = [];
    const poster = shot.image_path || shot.then_image_path || shot.now_image_path || null;
    if (shot.video_path) vids.push({ path: shot.video_path, label: `Shot ${shot.index}`, poster });
    if (shot.meeting_video_path) vids.push({ path: shot.meeting_video_path, label: `Shot ${shot.index} (Meeting)`, poster });
    if (shot.departure_video_path) vids.push({ path: shot.departure_video_path, label: `Shot ${shot.index} (Departure)`, poster });
    return vids;
  }) || [];

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          href={`/projects/${projectId}`}
          className="text-primary hover:underline mb-4 inline-block"
        >
          ← Back to Project
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">{story.title}</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Project ID: {projectId}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* View All Media Buttons */}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowImagesDialog(true)}
              className="flex items-center gap-2"
            >
              <ImageIcon className="w-4 h-4" />
              All Images
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowVideosDialog(true)}
              className="flex items-center gap-2"
            >
              <VideoIcon className="w-4 h-4" />
              All Videos
            </Button>

            {activeTab === "story" && hasChanges && (
              <>
                <Link
                  href={`/projects/${projectId}/settings`}
                  className="px-4 py-2 border rounded-md hover:bg-muted transition-colors flex items-center gap-2"
                >
                  Settings
                </Link>
                <Button
                  onClick={handleSaveStory}
                  disabled={!hasChanges || updateStoryMutation.isPending}
                  className="flex items-center gap-2"
                >
                  <Save className="w-4 h-4" />
                  {updateStoryMutation.isPending ? "Saving..." : "Save Changes"}
                </Button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Story Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="border rounded-lg p-4">
          <div className="text-sm text-muted-foreground">Total Scenes</div>
          <div className="text-2xl font-bold">{story.scenes.length}</div>
        </div>
        <div className="border rounded-lg p-4">
          <div className="text-sm text-muted-foreground">Total Duration</div>
          <div className="text-2xl font-bold">
            {Math.floor(totalDuration / 60)}:
            {(totalDuration % 60).toString().padStart(2, "0")}
          </div>
        </div>
        <div className="border rounded-lg p-4">
          <div className="text-sm text-muted-foreground">Total Shots</div>
          <div className="text-2xl font-bold">{shots ? shots.length : 0}</div>
        </div>
        <div className="border rounded-lg p-4">
          <div className="text-sm text-muted-foreground">Status</div>
          <div className="text-2xl font-bold">
            {activeTab === "story" && hasChanges ? "Unsaved" : "Saved"}
          </div>
        </div>
      </div>

      {/* Tabs for Story and Shots */}
      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as any)}
        className="w-full"
      >
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="story" className="flex items-center gap-2">
            <BookOpen className="w-4 h-4" />
            Story
          </TabsTrigger>
          <TabsTrigger value="shots" className="flex items-center gap-2">
            <Film className="w-4 h-4" />
            Shots
          </TabsTrigger>
        </TabsList>

        <TabsContent value="story" className="mt-6">
          {/* Scenes Editor */}
          <div className="border rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Scenes</h2>
              <button
                onClick={() => setShowRegenStoryModal(true)}
                className="flex items-center gap-2 text-sm px-3 py-1.5 border rounded-md hover:bg-muted transition-colors text-blue-600"
                title="Regenerate entire story using an AI agent"
              >
                <RefreshCw className="w-4 h-4" />
                Regenerate Story
              </button>
            </div>
            <SceneList
              scenes={story.scenes}
              onUpdate={handleUpdateScene}
              onDelete={handleDeleteScene}
              onReorder={handleReorderScenes}
              onAdd={handleAddScene}
            />
          </div>

          {/* Instructions */}
          <div className="mt-8 p-4 bg-muted rounded-lg">
            <h3 className="font-semibold mb-2">Tips for editing scenes:</h3>
            <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
              <li>Drag scenes to reorder them in the story</li>
              <li>Click the edit icon to modify scene details</li>
              <li>Adjust scene durations to control pacing</li>
              <li>Click "Save Changes" to persist your edits</li>
            </ul>
          </div>
        </TabsContent>

        <TabsContent value="shots" className="mt-6">
          {/* Shots Grid */}
          <div className="border rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">
                Shots
              </h2>
              <button
                onClick={() => setShowReplanShotsModal(true)}
                className="flex items-center gap-2 text-sm px-3 py-1.5 border rounded-md hover:bg-muted transition-colors text-purple-600"
                title="Re-plan all shots from the current story"
              >
                <RefreshCw className="w-4 h-4" />
                Re-plan Shots
              </button>
            </div>
            <ShotGrid
              shots={shots || []}
              projectId={projectId}
              scenes={project?.story?.scenes}
            />
          </div>

          {/* Instructions */}
          <div className="mt-8 p-4 bg-muted rounded-lg">
            <h3 className="font-semibold mb-2">Tips for editing shots:</h3>
            <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
              <li>Click the edit icon to modify image/motion prompts</li>
              <li>Click the rotation icon to regenerate an image</li>
              <li>Click the video icon to regenerate a video</li>
              <li>Changes are saved immediately</li>
            </ul>
          </div>
        </TabsContent>
      </Tabs>

      {/* Regenerate Story Modal */}
      {showRegenStoryModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-background rounded-lg shadow-xl max-w-md w-full p-6 relative">
            <button
              onClick={() => setShowRegenStoryModal(false)}
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
            >
              <X className="w-5 h-5" />
            </button>

            <h2 className="text-xl font-semibold mb-4">Regenerate Story</h2>
            <p className="text-sm text-muted-foreground mb-6">
              This will overwrite your current story structure. This action
              cannot be undone.
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Story Agent
                </label>
                <Select
                  value={selectedStoryAgent}
                  onValueChange={(val) => setSelectedStoryAgent(val)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Agent" />
                  </SelectTrigger>
                  <SelectContent>
                    {!agents?.story.length && (
                      <SelectItem value="default">Default Agent</SelectItem>
                    )}
                    {agents?.story.map((agent) => (
                      <SelectItem key={agent.id} value={agent.id}>
                        {agent.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="mt-8 flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => setShowRegenStoryModal(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={handleRegenStory}
                disabled={regenerateStoryMutation.isPending}
                className="flex items-center gap-2"
              >
                {regenerateStoryMutation.isPending ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Regenerating...
                  </>
                ) : (
                  "Start Regeneration"
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Re-plan Shots Modal */}
      {showReplanShotsModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-background rounded-lg shadow-xl max-w-md w-full p-6 relative">
            <button
              onClick={() => setShowReplanShotsModal(false)}
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
            >
              <X className="w-5 h-5" />
            </button>

            <h2 className="text-xl font-semibold mb-4">Re-plan Shots</h2>
            <p className="text-sm text-muted-foreground mb-6">
              This will re-calculate all shots based on the current story. All
              existing shot prompts will be overwritten.
            </p>

            <div className="space-y-4">
              <div className="grid grid-cols-1 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Shots Agent
                  </label>
                  <Select
                    value={selectedShotsAgent}
                    onValueChange={(val) => setSelectedShotsAgent(val)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select Agent" />
                    </SelectTrigger>
                    <SelectContent>
                      {!agents?.shots?.length && (
                        <SelectItem value="default">Default</SelectItem>
                      )}
                      {agents?.shots?.map((agent) => (
                        <SelectItem key={agent.id} value={agent.id}>
                          {agent.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Max Shots (0 = Auto)
                </label>
                <Input
                  type="number"
                  value={maxShots}
                  onChange={(e) => setMaxShots(parseInt(e.target.value) || 0)}
                  min="0"
                  max="100"
                />
              </div>
            </div>

            <div className="mt-8 flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => setShowReplanShotsModal(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={handleReplanShots}
                disabled={replanShotsMutation.isPending}
                className="flex items-center gap-2"
              >
                {replanShotsMutation.isPending ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Re-planning...
                  </>
                ) : (
                  "Start Re-planning"
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Dialog */}

      {/* View All Images Modal */}
      <Dialog open={showImagesDialog} onOpenChange={(open) => {
        setShowImagesDialog(open);
        if (!open) setSelectedImageIndex(null);
      }}>
        <DialogContent className="max-w-5xl h-[85vh] flex flex-col p-0 overflow-hidden bg-card border-border">
          <DialogHeader className="p-4 border-b border-border/60">
            <DialogTitle>All Project Images ({allImages.length})</DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto p-4">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {allImages.map((img, i) => (
                <div 
                  key={i} 
                  onClick={() => setSelectedImageIndex(i)} 
                  className="relative aspect-video rounded-lg overflow-hidden border border-border/50 group bg-black/20 cursor-pointer hover:border-primary/50 transition-colors"
                >
                  <img src={getMediaUrl(img.path)} alt={img.label} className="object-cover w-full h-full" loading="lazy" />
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-2">
                    <span className="text-xs text-white font-medium">{img.label}</span>
                  </div>
                  <div className="absolute bottom-2 left-2 bg-black/60 px-2 py-1 rounded text-xs text-white group-hover:hidden">
                    {img.label}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Lightbox Slideshow */}
          {selectedImageIndex !== null && allImages[selectedImageIndex] && (
            <div className="absolute inset-0 z-[100] bg-black/95 flex flex-col items-center justify-center animate-in fade-in-0 duration-200">
              <button 
                onClick={(e) => { e.stopPropagation(); setSelectedImageIndex(null); }} 
                className="absolute top-4 right-4 text-white/70 hover:text-white p-2 rounded-full hover:bg-white/10 transition-colors z-10"
              >
                <X className="w-6 h-6" />
              </button>

              {selectedImageIndex > 0 && (
                <button 
                  onClick={(e) => { e.stopPropagation(); setSelectedImageIndex(selectedImageIndex - 1); }} 
                  className="absolute left-6 text-white/70 hover:text-white p-3 rounded-full hover:bg-white/10 transition-colors z-10"
                >
                  <ChevronLeft className="w-8 h-8" />
                </button>
              )}

              <div className="relative aspect-video w-full max-w-6xl max-h-[80vh] flex items-center justify-center bg-black/40 rounded-lg overflow-hidden border border-border/40">
                <img 
                  src={getMediaUrl(allImages[selectedImageIndex].path)} 
                  alt={allImages[selectedImageIndex].label} 
                  className="w-full h-full object-contain select-none" 
                />
              </div>
              
              <div className="mt-4 text-white text-center">
                <span className="font-semibold">{allImages[selectedImageIndex].label}</span>
                <div className="text-xs text-white/60 mt-1">{selectedImageIndex + 1} of {allImages.length}</div>
              </div>

              {selectedImageIndex < allImages.length - 1 && (
                <button 
                  onClick={(e) => { e.stopPropagation(); setSelectedImageIndex(selectedImageIndex + 1); }} 
                  className="absolute right-6 text-white/70 hover:text-white p-3 rounded-full hover:bg-white/10 transition-colors z-10"
                >
                  <ChevronRight className="w-8 h-8" />
                </button>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* View All Videos Modal */}
      <Dialog open={showVideosDialog} onOpenChange={(open) => {
        setShowVideosDialog(open);
        if (!open) setSelectedVideoIndex(null);
      }}>
        <DialogContent className="max-w-5xl h-[85vh] flex flex-col p-0 overflow-hidden bg-card border-border">
          <DialogHeader className="p-4 border-b border-border/60">
            <DialogTitle>All Project Videos ({allVideos.length})</DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto p-4">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {allVideos.map((vid, i) => (
                <div 
                  key={i} 
                  onClick={() => setSelectedVideoIndex(i)} 
                  className="relative aspect-video rounded-lg overflow-hidden border border-border/50 group bg-black/20 cursor-pointer hover:border-primary/50 transition-colors"
                >
                  {vid.poster ? (
                    <img src={getMediaUrl(vid.poster)} alt={vid.label} className="object-cover w-full h-full" loading="lazy" />
                  ) : (
                    <div className="flex items-center justify-center w-full h-full bg-slate-900/40 text-xs text-muted-foreground">
                      No Poster
                    </div>
                  )}
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <div className="bg-primary p-3 rounded-full shadow-lg">
                      <Play className="w-6 h-6 text-primary-foreground fill-current" />
                    </div>
                  </div>
                  <div className="absolute bottom-2 left-2 bg-black/60 px-2 py-1 rounded text-xs text-white group-hover:hidden">
                    {vid.label}
                  </div>
                  <div className="absolute top-2 right-2 bg-black/60 px-1.5 py-0.5 rounded text-[10px] text-white/80">
                    Video
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Fullscreen Video Player */}
          {selectedVideoIndex !== null && allVideos[selectedVideoIndex] && (
            <div className="absolute inset-0 z-[100] bg-black/98 flex flex-col items-center justify-center animate-in fade-in-0 duration-200">
              <button 
                onClick={(e) => { e.stopPropagation(); setSelectedVideoIndex(null); }} 
                className="absolute top-4 right-4 text-white/70 hover:text-white p-2 rounded-full hover:bg-white/10 transition-colors z-10"
              >
                <X className="w-6 h-6" />
              </button>

              {selectedVideoIndex > 0 && (
                <button 
                  onClick={(e) => { e.stopPropagation(); setSelectedVideoIndex(selectedVideoIndex - 1); }} 
                  className="absolute left-6 text-white/70 hover:text-white p-3 rounded-full hover:bg-white/10 transition-colors z-10"
                >
                  <ChevronLeft className="w-8 h-8" />
                </button>
              )}

              <div className="relative aspect-video w-full max-w-5xl max-h-[80vh] flex items-center justify-center bg-black rounded-lg overflow-hidden shadow-2xl">
                <video 
                  src={getMediaUrl(allVideos[selectedVideoIndex].path)} 
                  controls 
                  autoPlay 
                  className="w-full h-full object-contain" 
                  onClick={(e) => e.stopPropagation()} 
                />
              </div>
              
              <div className="mt-4 text-white text-center">
                <span className="font-semibold">{allVideos[selectedVideoIndex].label}</span>
                <div className="text-xs text-white/60 mt-1">{selectedVideoIndex + 1} of {allVideos.length}</div>
              </div>

              {selectedVideoIndex < allVideos.length - 1 && (
                <button 
                  onClick={(e) => { e.stopPropagation(); setSelectedVideoIndex(selectedVideoIndex + 1); }} 
                  className="absolute right-6 text-white/70 hover:text-white p-3 rounded-full hover:bg-white/10 transition-colors z-10"
                >
                  <ChevronRight className="w-8 h-8" />
                </button>
              )}
            </div>
          )}

          {/* Lightbox Slideshow */}
          {selectedImageIndex !== null && allImages[selectedImageIndex] && (
            <div className="absolute inset-0 z-[100] bg-black/95 flex flex-col items-center justify-center animate-in fade-in-0 duration-200">
              <button 
                onClick={(e) => { e.stopPropagation(); setSelectedImageIndex(null); }} 
                className="absolute top-4 right-4 text-white/70 hover:text-white p-2 rounded-full hover:bg-white/10 transition-colors z-10"
              >
                <X className="w-6 h-6" />
              </button>

              {selectedImageIndex > 0 && (
                <button 
                  onClick={(e) => { e.stopPropagation(); setSelectedImageIndex(selectedImageIndex - 1); }} 
                  className="absolute left-6 text-white/70 hover:text-white p-3 rounded-full hover:bg-white/10 transition-colors z-10"
                >
                  <ChevronLeft className="w-8 h-8" />
                </button>
              )}

              <div className="relative aspect-video w-full max-w-6xl max-h-[80vh] flex items-center justify-center bg-black/40 rounded-lg overflow-hidden border border-border/40">
                <img 
                  src={getMediaUrl(allImages[selectedImageIndex].path)} 
                  alt={allImages[selectedImageIndex].label} 
                  className="w-full h-full object-contain select-none" 
                />
              </div>
              
              <div className="mt-4 text-white text-center">
                <span className="font-semibold">{allImages[selectedImageIndex].label}</span>
                <div className="text-xs text-white/60 mt-1">{selectedImageIndex + 1} of {allImages.length}</div>
              </div>

              {selectedImageIndex < allImages.length - 1 && (
                <button 
                  onClick={(e) => { e.stopPropagation(); setSelectedImageIndex(selectedImageIndex + 1); }} 
                  className="absolute right-6 text-white/70 hover:text-white p-3 rounded-full hover:bg-white/10 transition-colors z-10"
                >
                  <ChevronRight className="w-8 h-8" />
                </button>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>



      <ConfirmDialog {...confirmDialog.dialogProps} />
    </div>
  );
}
