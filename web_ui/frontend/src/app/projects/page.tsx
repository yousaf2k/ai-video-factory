/**
 * Projects list page
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import { Trash2, Copy, ImageIcon, RefreshCw, PlaySquare } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import {
  useProjects,
  useCreateProject,
  useDeleteProject,
  useDuplicateProject,
} from "@/hooks/useProjects";
import { useAgents } from "@/hooks/useAgents";
import { getMediaUrl } from "@/lib/utils";
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
import { api } from "@/services/api";
import type { CreateProjectRequest } from "@/types";
import { formatDistanceToNow } from "date-fns";

export default function ProjectsPage() {
  const queryClient = useQueryClient();
  const { data: projects, isLoading, error } = useProjects();
  const { data: agents } = useAgents();
  const createProjectMutation = useCreateProject();
  const deleteProjectMutation = useDeleteProject();
  const duplicateProjectMutation = useDuplicateProject();

  const [showNewDialog, setShowNewDialog] = useState(false);
  const [newIdea, setNewIdea] = useState("");
  const [isGeneratingStory, setIsGeneratingStory] = useState(false);

  // Agent selection state
  const [selectedStoryAgent, setSelectedStoryAgent] = useState("default");
  const [selectedShotsAgent, setSelectedShotsAgent] = useState("default");
  const [totalDuration, setTotalDuration] = useState(600);
  const [promptsFile, setPromptsFile] = useState("");
  const [selectedAspectRatio, setSelectedAspectRatio] = useState<"16:9" | "9:16">("16:9");
  const [generatingThumbnails, setGeneratingThumbnails] = useState<
    Record<string, boolean>
  >({});

  const handleGenerateThumbnail = async (projectId: string) => {
    try {
      setGeneratingThumbnails((prev) => ({ ...prev, [projectId]: true }));
      await api.generateThumbnail(projectId, "16:9", true);
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    } catch (error) {
      console.error("Failed to generate thumbnail:", error);
    } finally {
      setGeneratingThumbnails((prev) => ({ ...prev, [projectId]: false }));
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newIdea.trim()) return;

    const request: CreateProjectRequest = {
      idea: newIdea,
      story_agent: selectedStoryAgent,
      shots_agent: selectedShotsAgent,
      total_duration: totalDuration,
      prompts_file: promptsFile.trim() || undefined,
      aspect_ratio: selectedAspectRatio,
    };

    try {
      setIsGeneratingStory(true);
      const project = await createProjectMutation.mutateAsync(request);

      try {
        // Automatically generate the initial story ONLY if not using a prompts file
        if (!request.prompts_file) {
          await api.regenerateStory(project.project_id, request.story_agent);
        }
      } catch (storyError) {
        console.error("Failed to generate initial story:", storyError);
        // Continue to the project page even if story generation fails
      }

      setShowNewDialog(false);
      setNewIdea("");
      setPromptsFile("");
      // Navigate to the new project
      window.location.href = `/projects/${project.project_id}`;
    } catch (error) {
      console.error("Failed to create project:", error);
      alert("Failed to create project. Please try again.");
    } finally {
      setIsGeneratingStory(false);
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    if (
      !confirm(
        "Are you sure you want to delete this project? This action cannot be undone.",
      )
    ) {
      return;
    }

    try {
      await deleteProjectMutation.mutateAsync(projectId);
    } catch (error) {
      console.error("Failed to delete project:", error);
      alert("Failed to delete project. Please try again.");
    }
  };

  const handleDuplicateProject = async (projectId: string) => {
    try {
      const project = await duplicateProjectMutation.mutateAsync({ projectId });
      // Navigate to the duplicated project
      window.location.href = `/projects/${project.project_id}`;
    } catch (error) {
      console.error("Failed to duplicate project:", error);
      alert("Failed to duplicate project. Please try again.");
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading projects...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-500">Error loading projects</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">AI Video Factory</h1>
          <p className="text-muted-foreground mt-1">
            Generate cinematic videos from text ideas
          </p>
        </div>
        <Button onClick={() => setShowNewDialog(true)}>New Project</Button>
      </div>

      {/* Projects Grid */}
      {projects && projects.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-y-10 gap-x-4">
          {projects.map((project) => (
            <div
              key={project.project_id}
              className="group relative flex flex-col gap-3 transition-colors rounded-xl hover:bg-muted/30 p-2 -m-2"
            >
              {/* Thumbnail Container */}
              <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-muted outline outline-1 outline-transparent group-hover:outline-border transition-all">
                {project.thumbnail_url ? (
                  <img
                    src={getMediaUrl(project.thumbnail_url)}
                    alt={project.idea}
                    className="object-cover w-full h-full"
                  />
                ) : (
                  <div className="flex w-full h-full flex-col items-center justify-center bg-card text-muted-foreground relative">
                    <ImageIcon className="w-8 h-8 mb-2 opacity-50" />
                  </div>
                )}

                {/* Generate Button Overlay */}
                {!project.thumbnail_url && (
                  <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-20">
                    <Button
                      variant="secondary"
                      size="sm"
                      className="gap-2 shadow-lg"
                      onClick={(e) => {
                        e.preventDefault();
                        handleGenerateThumbnail(project.project_id);
                      }}
                      disabled={generatingThumbnails[project.project_id]}
                    >
                      {generatingThumbnails[project.project_id] ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <ImageIcon className="w-4 h-4" />
                      )}
                      {generatingThumbnails[project.project_id]
                        ? "Generating..."
                        : "Generate Thumbnail"}
                    </Button>
                  </div>
                )}

                {/* Duration / Status Badges on Thumbnail */}
                <div className="absolute bottom-1 right-1 px-1.5 py-0.5 text-xs font-medium text-white bg-black/80 rounded z-10">
                  {project.completed ? "Done" : "In Progress"}
                </div>
              </div>

              {/* Details */}
              <div className="flex gap-3 px-1">
                <div className="flex-none mt-0.5 text-primary">
                  <PlaySquare
                    className="w-9 h-9 opacity-80"
                    strokeWidth={1.5}
                  />
                </div>
                <div className="flex flex-col overflow-hidden">
                  <h3
                    className="text-sm font-semibold line-clamp-2 leading-tight text-foreground"
                    title={project.idea}
                  >
                    {project.story?.title || project.idea}
                  </h3>
                  <div className="text-xs text-muted-foreground mt-1 flex flex-col gap-0.5">
                    <span className="truncate">
                      {project.started_at
                        ? (() => {
                          try {
                            return formatDistanceToNow(
                              new Date(project.started_at),
                              { addSuffix: true },
                            );
                          } catch (e) {
                            return "Unknown date";
                          }
                        })()
                        : "Unknown date"}
                    </span>
                    <span className="truncate">
                      {project.videos_rendered} videos • {project.total_shots}{" "}
                      shots
                    </span>
                  </div>
                </div>
              </div>

              <Link
                href={`/projects/${project.project_id}`}
                className="absolute inset-0 z-10"
              >
                <span className="sr-only">View Project</span>
              </Link>

              {/* Action Menu overlay in corner */}
              <div className="absolute top-4 right-4 z-30 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                <Button
                  variant="secondary"
                  size="icon"
                  className="w-8 h-8 rounded-full shadow-md bg-background/80 hover:bg-background"
                  onClick={(e) => {
                    e.preventDefault();
                    handleDuplicateProject(project.project_id);
                  }}
                  title="Duplicate project"
                >
                  <Copy className="w-4 h-4" />
                </Button>
                <Button
                  variant="destructive"
                  size="icon"
                  className="w-8 h-8 rounded-full shadow-md"
                  onClick={(e) => {
                    e.preventDefault();
                    handleDeleteProject(project.project_id);
                  }}
                  title="Delete project"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">
            No projects yet. Create your first project!
          </p>
          <Button onClick={() => setShowNewDialog(true)}>Create Project</Button>
        </div>
      )}

      {/* New Project Dialog */}
      {showNewDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Create New Project</h2>
            <form onSubmit={handleCreateProject}>
              <div className="mb-4">
                <label
                  htmlFor="idea"
                  className="block text-sm font-medium mb-2"
                >
                  Video Idea
                </label>
                <Textarea
                  id="idea"
                  value={newIdea}
                  onChange={(e) => setNewIdea(e.target.value)}
                  className="min-h-[100px] mb-4"
                  placeholder="Describe your video idea..."
                  required
                />
              </div>

              <div className="mb-4">
                <label
                  htmlFor="promptsFile"
                  className="block text-sm font-medium mb-2"
                >
                  Prompts File Path (optional)
                </label>
                <Input
                  id="promptsFile"
                  type="text"
                  value={promptsFile}
                  onChange={(e) => setPromptsFile(e.target.value)}
                  placeholder="e.g., input/my_prompts.txt"
                />
                <p className="text-[10px] text-muted-foreground mt-1">
                  Skip story generation and import shots directly from this
                  file.
                </p>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">
                  Aspect Ratio
                </label>
                <Select
                  value={selectedAspectRatio}
                  onValueChange={(val) => setSelectedAspectRatio(val as "16:9" | "9:16")}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Aspect Ratio" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="16:9">16:9 Landscape</SelectItem>
                    <SelectItem value="9:16">9:16 Portrait</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-[10px] text-muted-foreground mt-1">
                  {selectedAspectRatio === "16:9"
                    ? "Horizontal format, best for YouTube and desktop viewing"
                    : "Vertical format, best for TikTok, Reels, and Shorts"}
                </p>
              </div>

              <div className="grid grid-cols-1 gap-4 mb-6">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Story Agent
                  </label>
                  <Select
                    value={selectedStoryAgent}
                    onValueChange={(val) => setSelectedStoryAgent(val)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select Story Agent" />
                    </SelectTrigger>
                    <SelectContent>
                      {!agents?.story.length && (
                        <SelectItem value="default">Default</SelectItem>
                      )}
                      {agents?.story.map((agent) => (
                        <SelectItem key={agent.id} value={agent.id}>
                          {agent.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Shots Agent
                  </label>
                  <Select
                    value={selectedShotsAgent}
                    onValueChange={(val) => setSelectedShotsAgent(val)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select Shots Agent" />
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

              <div className="mb-6">
                <label
                  htmlFor="duration"
                  className="block text-sm font-medium mb-1"
                >
                  Target Duration (seconds)
                </label>
                <div className="flex items-center gap-3">
                  <Input
                    id="duration"
                    type="number"
                    value={totalDuration}
                    onChange={(e) =>
                      setTotalDuration(parseInt(e.target.value) || 0)
                    }
                    min="10"
                    step="10"
                  />
                  <span className="text-sm text-muted-foreground bg-muted px-2 py-1 rounded">
                    {Math.floor(totalDuration / 60)}m {totalDuration % 60}s
                  </span>
                </div>
                <p className="text-[10px] text-muted-foreground mt-1">
                  The AI will try to generate a story that fits this total
                  length.
                </p>
              </div>

              <div className="flex gap-2 justify-end">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowNewDialog(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={
                    createProjectMutation.isPending || isGeneratingStory
                  }
                >
                  {isGeneratingStory
                    ? "Generating Story..."
                    : createProjectMutation.isPending
                      ? "Creating..."
                      : "Create"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
