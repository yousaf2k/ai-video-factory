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
import { getMediaUrl, cn } from "@/lib/utils";
import { Image as ImageIcon, Video as VideoIcon } from "lucide-react";
import { useProject } from "@/hooks/useProjects";
import { useUpdateStory, useRegenerateStory } from "@/hooks/useStory";
import { useShots, useReplanShots } from "@/hooks/useShots";
import { useAgents } from "@/hooks/useAgents";
import { SceneList } from "@/components/scenes/SceneList";
import { ShotGrid } from "@/components/shots/ShotGrid";
import { Scene, Story, Shot } from "@/types";
import { api } from "@/services/api";
import { useQueryClient } from "@tanstack/react-query";
import CharacterReferenceUpload from "@/components/characters/CharacterReferenceUpload";
import { useProgress } from "@/hooks/useProgress";
import { Save, RefreshCw, X, BookOpen, Film, ChevronLeft, ChevronRight, Play, ArrowLeft, Clock, Video, ListMusic, Settings, CheckCircle2, UserCircle } from "lucide-react";
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
import { useCallback } from "react";

export default function ProjectEditPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { data: project, isLoading, error } = useProject(projectId);
  const { data: shots } = useShots(projectId);
  const { data: agents } = useAgents();
  const queryClient = useQueryClient();

  // Keep WebSocket invalidation connected top-level for both tabs
  useProgress(
    projectId,
    useCallback(
      (id: string | number, type: 'shot' | 'scene') => {
        queryClient.invalidateQueries({ queryKey: ["project", projectId] });
        queryClient.invalidateQueries({ queryKey: ["shots", projectId] });
      },
      [queryClient, projectId]
    )
  );

  const updateStoryMutation = useUpdateStory(projectId);
  const regenerateStoryMutation = useRegenerateStory(projectId);
  const replanShotsMutation = useReplanShots(projectId);
  const confirmDialog = useConfirmDialog();

  // Local state for story editing
  const [story, setStory] = useState<Story | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [activeTab, setActiveTab] = useState("shots");
  // Media dialog states
  const [showGalleryDialog, setShowGalleryDialog] = useState(false);
  const [galleryTab, setGalleryTab] = useState<"images" | "videos">("images");
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null);
  const [selectedVideoIndex, setSelectedVideoIndex] = useState<number | null>(null);

  // Modal states
  const [showRegenStoryModal, setShowRegenStoryModal] = useState(false);
  const [showReplanShotsModal, setShowReplanShotsModal] = useState(false);

  // Selection states
  const [selectedStoryAgent, setSelectedStoryAgent] = useState("default");
  const [selectedShotsAgent, setSelectedShotsAgent] = useState("default");
  const [maxShots, setMaxShots] = useState(0);

  // Initialize and sync story when project loads
  useEffect(() => {
    if (project && project.story) {
      setStory(project.story);
    }
  }, [project?.story]);

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
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Header */}
      <div className="mb-8">
        <Link
          href={`/projects/${projectId}`}
          className="inline-flex items-center gap-1 text-sm font-medium text-muted-foreground hover:text-primary mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Project
        </Link>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">
              {story.title}
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Project ID: <span className="font-mono text-xs">{projectId}</span>
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {activeTab === "story" && hasChanges && (
              <>
                <Link
                  href={`/projects/${projectId}/settings`}
                  className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium border rounded-md hover:bg-muted transition-all shadow-sm"
                >
                  <Settings className="w-4 h-4" />
                  Settings
                </Link>
                <Button
                  onClick={handleSaveStory}
                  size="sm"
                  disabled={!hasChanges || updateStoryMutation.isPending}
                  className="flex items-center gap-1.5 shadow-sm font-medium"
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
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-card/50 border border-border/50 rounded-xl p-4 flex items-center gap-4 shadow-sm backdrop-blur-md">
          <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center text-primary">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Total Scenes</p>
            <p className="text-xl font-bold">{story.scenes.length}</p>
          </div>
        </div>
        <div className="bg-card/50 border border-border/50 rounded-xl p-4 flex items-center gap-4 shadow-sm backdrop-blur-md">
          <div className="w-10 h-10 bg-accent/10 rounded-lg flex items-center justify-center text-accent">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Total Duration</p>
            <p className="text-xl font-bold">
              {Math.floor(totalDuration / 60)}:
              {(totalDuration % 60).toString().padStart(2, "0")}
            </p>
          </div>
        </div>
        <div className="bg-card/50 border border-border/50 rounded-xl p-4 flex items-center gap-4 shadow-sm backdrop-blur-md">
          <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center text-purple-500">
            <Film className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Planned Shots</p>
            <p className="text-xl font-bold">{shots ? shots.length : 0}</p>
          </div>
        </div>
        <div className="bg-card/50 border border-border/50 rounded-xl p-4 flex items-center gap-4 shadow-sm backdrop-blur-md">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${hasChanges ? "bg-amber-500/10 text-amber-500" : "bg-green-500/10 text-green-500"
            }`}>
            {hasChanges ? <RefreshCw className="w-5 h-5 animate-spin-slow" /> : <CheckCircle2 className="w-5 h-5" />}
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Status</p>
            <p className={`text-xl font-bold ${hasChanges ? "text-amber-500" : "text-green-500"}`}>
              {hasChanges ? "Unsaved" : "Saved"}
            </p>
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
          {/* Characters Section */}
          {story.characters && story.characters.length > 0 && (
            <div className="bg-card border border-border rounded-xl p-6 shadow-sm mb-6">
              <h2 className="text-xl font-bold flex items-center gap-2 mb-6 pb-4 border-b border-border/50">
                <UserCircle className="w-5 h-5 text-primary" />
                Character References
              </h2>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {story.characters.map((character, idx) => (
                  <div key={idx} className="border border-border/50 rounded-xl p-5 bg-background shadow-sm hover:border-primary/30 transition-colors">
                    <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
                       <span className="w-6 h-6 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs">{idx + 1}</span>
                       {character.name}
                    </h3>
                    <CharacterReferenceUpload
                      character={character}
                      characterIndex={idx}
                      projectId={projectId}
                      onUpdate={() => {
                        queryClient.invalidateQueries({ queryKey: ["project", projectId] });
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Scenes Editor */}
          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6 pb-4 border-b border-border/50">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <ListMusic className="w-5 h-5 text-primary" />
                Scenes Breakdown
              </h2>
              <button
                onClick={() => setShowRegenStoryModal(true)}
                className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 border border-blue-500/20 rounded-md hover:bg-blue-500/10 transition-colors text-blue-500 shadow-sm"
                title="Regenerate entire story using an AI agent"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Regenerate Story
              </button>
            </div>
            <SceneList
              scenes={story.scenes}
              onUpdate={handleUpdateScene}
              onDelete={handleDeleteScene}
              onReorder={handleReorderScenes}
              onAdd={handleAddScene}
              projectType={story.project_type}
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
          <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-border/50">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Film className="w-5 h-5 text-primary" />
                Shots Timeline
              </h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setGalleryTab("images");
                    setShowGalleryDialog(true);
                  }}
                  className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 border border-border rounded-md hover:bg-muted transition-colors shadow-sm"
                  title="Open Project Media Gallery"
                >
                  <ImageIcon className="w-3.5 h-3.5" />
                  Media Gallery
                </button>
                <button
                  onClick={() => setShowReplanShotsModal(true)}
                  className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 border border-purple-500/20 rounded-md hover:bg-purple-500/10 transition-colors text-purple-500 shadow-sm"
                  title="Re-plan all shots from the current story"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Re-plan Shots
                </button>
              </div>
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

      {/* Combined Media Gallery Modal */}
      <Dialog open={showGalleryDialog} onOpenChange={(open) => {
        setShowGalleryDialog(open);
        if (!open) {
          setSelectedImageIndex(null);
          setSelectedVideoIndex(null);
        }
      }}>
        <DialogContent className="max-w-5xl h-[85vh] flex flex-col p-0 overflow-hidden bg-card border-border">
          <DialogHeader className="p-4 border-b border-border/60 flex flex-row items-center justify-between">
            <DialogTitle>Project Media Gallery</DialogTitle>
            
            <div className="flex items-center bg-muted/40 p-1 rounded-lg border shadow-sm mr-8">
              <button
                onClick={() => setGalleryTab("images")}
                className={cn("flex items-center gap-1.5 text-xs font-semibold px-4 py-1.5 rounded-md transition-all", galleryTab === "images" ? "bg-background text-blue-600 shadow-sm ring-1 ring-border" : "text-muted-foreground hover:text-foreground")}
              >
                <ImageIcon className="w-4 h-4" />
                Images ({allImages.length})
              </button>
              <button
                onClick={() => setGalleryTab("videos")}
                className={cn("flex items-center gap-1.5 text-xs font-semibold px-4 py-1.5 rounded-md transition-all", galleryTab === "videos" ? "bg-background text-purple-600 shadow-sm ring-1 ring-border" : "text-muted-foreground hover:text-foreground")}
              >
                <VideoIcon className="w-4 h-4" />
                Videos ({allVideos.length})
              </button>
            </div>
          </DialogHeader>

          <div className="flex-1 overflow-y-auto p-4 bg-muted/10">
            {galleryTab === "images" ? (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {allImages.length === 0 && (
                  <div className="col-span-full py-12 text-center text-muted-foreground">No images generated yet.</div>
                )}
                {allImages.map((img, i) => (
                  <div
                    key={i}
                    onClick={() => setSelectedImageIndex(i)}
                    className="relative aspect-video rounded-lg overflow-hidden border border-border/50 group bg-black/20 cursor-pointer hover:border-primary/50 transition-colors shadow-sm"
                  >
                    <img src={getMediaUrl(img.path)} alt={img.label} className="object-cover w-full h-full" loading="lazy" />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-2">
                      <span className="text-xs text-white font-medium">{img.label}</span>
                    </div>
                    <div className="absolute bottom-2 left-2 bg-black/60 px-2 py-1 rounded text-xs text-white group-hover:hidden backdrop-blur-sm">
                      {img.label}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {allVideos.length === 0 && (
                  <div className="col-span-full py-12 text-center text-muted-foreground">No videos rendered yet.</div>
                )}
                {allVideos.map((vid, i) => (
                  <div
                    key={i}
                    onClick={() => setSelectedVideoIndex(i)}
                    className="relative aspect-video rounded-lg overflow-hidden border border-border/50 group bg-black/20 cursor-pointer hover:border-primary/50 transition-colors shadow-sm"
                  >
                    {vid.poster ? (
                      <img src={getMediaUrl(vid.poster)} alt={vid.label} className="object-cover w-full h-full" loading="lazy" />
                    ) : (
                      <div className="flex items-center justify-center w-full h-full bg-slate-900/40 text-xs text-muted-foreground">
                        No Poster
                      </div>
                    )}
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center backdrop-blur-[1px]">
                      <div className="bg-primary/90 p-3 rounded-full shadow-lg">
                        <Play className="w-6 h-6 text-primary-foreground fill-current" />
                      </div>
                    </div>
                    <div className="absolute bottom-2 left-2 bg-black/60 px-2 py-1 rounded text-xs text-white group-hover:hidden backdrop-blur-sm">
                      {vid.label}
                    </div>
                    <div className="absolute top-2 right-2 bg-black/60 px-1.5 py-0.5 rounded text-[10px] text-white/80 font-medium tracking-wide">
                      VIDEO
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Fullscreen Video Player */}
          {galleryTab === "videos" && selectedVideoIndex !== null && allVideos[selectedVideoIndex] && (
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
          {galleryTab === "images" && selectedImageIndex !== null && allImages[selectedImageIndex] && (
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
