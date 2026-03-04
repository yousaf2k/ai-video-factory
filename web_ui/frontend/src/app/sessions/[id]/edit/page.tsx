/**
 * Session editor page - Story and shot editing
 */
"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useSession } from "@/hooks/useSessions";
import { useUpdateStory, useRegenerateStory } from "@/hooks/useStory";
import { useShots, useReplanShots } from "@/hooks/useShots";
import { useAgents } from "@/hooks/useAgents";
import { SceneList } from "@/components/scenes/SceneList";
import { ShotGrid } from "@/components/shots/ShotGrid";
import { Scene, Story, Shot } from "@/types";
import { api } from "@/services/api";
import { Save, RefreshCw, X } from "lucide-react";
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

export default function SessionEditPage() {
  const params = useParams();
  const sessionId = params.id as string;
  const { data: session, isLoading, error } = useSession(sessionId);
  const { data: shots } = useShots(sessionId);
  const { data: agents } = useAgents();

  const updateStoryMutation = useUpdateStory(sessionId);
  const regenerateStoryMutation = useRegenerateStory(sessionId);
  const replanShotsMutation = useReplanShots(sessionId);

  // Local state for story editing
  const [story, setStory] = useState<Story | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [activeTab, setActiveTab] = useState("shots");

  // Modal states
  const [showRegenStoryModal, setShowRegenStoryModal] = useState(false);
  const [showReplanShotsModal, setShowReplanShotsModal] = useState(false);

  // Selection states
  const [selectedStoryAgent, setSelectedStoryAgent] = useState("default");
  const [selectedShotsAgent, setSelectedShotsAgent] = useState("default");
  const [maxShots, setMaxShots] = useState(0);

  // Initialize story when session loads
  if (session && session.story && !story) {
    setStory(session.story);
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

  const handleUpdateScene = (index: number, updatedScene: Scene) => {
    if (!story) return;

    const newScenes = [...story.scenes];
    newScenes[index] = updatedScene;

    setStory({
      ...story,
      scenes: newScenes,
    });
    setHasChanges(true);
  };

  const handleDeleteScene = (index: number) => {
    if (!story) return;
    if (!confirm("Are you sure you want to delete this scene?")) return;

    const newScenes = story.scenes.filter((_, i) => i !== index);

    setStory({
      ...story,
      scenes: newScenes,
    });
    setHasChanges(true);
  };

  const handleReorderScenes = (newScenes: Scene[]) => {
    if (!story) return;

    setStory({
      ...story,
      scenes: newScenes,
    });
    setHasChanges(true);
  };

  const handleAddScene = () => {
    if (!story) return;

    const newScene: Scene = {
      location: "New Location",
      characters: "Characters",
      action: "Action happening",
      emotion: "Emotional tone",
      narration: "Narration text",
      scene_duration: 30,
    };

    setStory({
      ...story,
      scenes: [...story.scenes, newScene],
    });
    setHasChanges(true);
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
        <div className="text-lg">Loading session...</div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-500">Error loading session</div>
      </div>
    );
  }

  if (!story) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-12">
          <h2 className="text-xl font-semibold mb-4">No Story Found</h2>
          <p className="text-muted-foreground mb-6">
            This session doesn't have a story yet. Generate a story first.
          </p>
          <Link
            href={`/sessions/${sessionId}`}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            Back to Session
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

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          href={`/sessions/${sessionId}`}
          className="text-primary hover:underline mb-4 inline-block"
        >
          ← Back to Session
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Edit Session</h1>
            <p className="text-muted-foreground">
              Edit story structure and shot prompts
            </p>
          </div>
          {activeTab === "story" && hasChanges && (
            <div className="flex items-center gap-3">
              <Link
                href={`/sessions/${sessionId}/settings`}
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
            </div>
          )}
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
          <TabsTrigger value="story">Story</TabsTrigger>
          <TabsTrigger value="shots">Shots</TabsTrigger>
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
                Shots ({shots?.length || 0})
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
            <ShotGrid shots={shots || []} sessionId={sessionId} />
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
    </div>
  );
}
