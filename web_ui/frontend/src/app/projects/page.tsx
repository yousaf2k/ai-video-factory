/**
 * Projects list page
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import { 
  Trash2, 
  Copy, 
  ImageIcon, 
  RefreshCw, 
  PlaySquare,
  Plus,
  Video,
  Clock,
  Layers,
  FolderPlus,
  Sparkles
} from "lucide-react";
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
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Hero Header */}
      <div className="relative overflow-hidden bg-card/50 border border-border/50 rounded-2xl p-8 mb-10 shadow-sm">
        <div className="absolute top-0 right-0 p-12 opacity-5 pointer-events-none">
          <Video className="w-64 h-64" />
        </div>
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight mb-2">Projects</h1>
            <p className="text-lg text-muted-foreground max-w-xl">
              Create, manage, and generate cinematic videos from your text ideas.
            </p>
          </div>
          <Button 
            size="lg" 
            className="shadow-md hover:shadow-lg transition-all"
            onClick={() => setShowNewDialog(true)}
          >
            <Plus className="w-5 h-5 mr-2" />
            New Project
          </Button>
        </div>
      </div>

      {/* Projects Grid */}
      {projects && projects.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
          {projects.map((project) => (
            <div
              key={project.project_id}
              className="group relative flex flex-col gap-3 transition-all duration-300 rounded-xl bg-card border shadow-sm hover:shadow-md hover:-translate-y-1 overflow-hidden"
            >
              {/* Thumbnail Container */}
              <div className="relative aspect-video w-full overflow-hidden bg-muted">
                {project.thumbnail_url ? (
                  <img
                    src={getMediaUrl(project.thumbnail_url)}
                    alt={project.idea}
                    className="object-cover w-full h-full transition-transform duration-500 group-hover:scale-105"
                  />
                ) : (
                  <div className="flex w-full h-full flex-col items-center justify-center bg-muted text-muted-foreground relative">
                    <ImageIcon className="w-10 h-10 mb-2 opacity-30" />
                  </div>
                )}
                
                {/* Generate Button Overlay */}
                {!project.thumbnail_url && (
                  <div className="absolute inset-0 bg-background/60 backdrop-blur-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300 z-20">
                    <Button
                      variant="secondary"
                      size="sm"
                      className="gap-2 shadow-lg hover:scale-105 transition-transform"
                      onClick={(e) => {
                        e.preventDefault();
                        handleGenerateThumbnail(project.project_id);
                      }}
                      disabled={generatingThumbnails[project.project_id]}
                    >
                      {generatingThumbnails[project.project_id] ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <Sparkles className="w-4 h-4" />
                      )}
                      {generatingThumbnails[project.project_id]
                        ? "Generating..."
                        : "Generate Thumbnail"}
                    </Button>
                  </div>
                )}

                {/* Status Badges on Thumbnail */}
                <div className="absolute top-2 left-2 z-10">
                  <span className={`px-2 py-1 text-xs font-semibold rounded-md shadow-sm backdrop-blur-md ${
                    project.completed 
                      ? "bg-green-500/80 text-white" 
                      : "bg-blue-500/80 text-white"
                  }`}>
                    {project.completed ? "Done" : "In Progress"}
                  </span>
                </div>
                
                {/* Duration Overlay */}
                <div className="absolute bottom-2 right-2 px-2 py-1 text-xs font-medium text-white bg-black/70 backdrop-blur-sm rounded-md z-10 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {project.started_at
                    ? (() => {
                        try {
                          return formatDistanceToNow(
                            new Date(project.started_at),
                            { addSuffix: true },
                          );
                        } catch (e) {
                          return "Unknown";
                        }
                      })()
                    : "New"}
                </div>
              </div>

              {/* Details & Actions Section */}
              <div className="flex flex-col p-4 flex-grow">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h3
                    className="text-base font-semibold line-clamp-2 leading-tight text-card-foreground group-hover:text-primary transition-colors"
                    title={project.idea}
                  >
                    {project.story?.title || project.idea}
                  </h3>
                </div>
                
                <div className="flex items-center gap-4 text-xs text-muted-foreground mt-auto pt-4 border-t border-border/40">
                  <div className="flex items-center gap-1.5" title="Rendered Videos">
                    <Video className="w-3.5 h-3.5" />
                    <span>{project.videos_rendered || 0}</span>
                  </div>
                  <div className="flex items-center gap-1.5" title="Total Shots">
                    <Layers className="w-3.5 h-3.5" />
                    <span>{project.total_shots || 0}</span>
                  </div>
                </div>
              </div>

              {/* Clickable Area Overlay */}
              <Link
                href={`/projects/${project.project_id}`}
                className="absolute inset-0 z-10"
              >
                <span className="sr-only">View Project</span>
              </Link>

              {/* Action Menu overlay in corner */}
              <div className="absolute top-2 right-2 z-30 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col gap-2">
                <Button
                  variant="secondary"
                  size="icon"
                  className="w-8 h-8 rounded-full shadow-md bg-background/90 hover:bg-background hover:scale-110 transition-transform"
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
                  className="w-8 h-8 rounded-full shadow-md hover:scale-110 transition-transform"
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
        <div className="flex flex-col items-center justify-center py-20 px-4 text-center border-2 border-dashed rounded-2xl bg-card/30">
          <div className="w-20 h-20 bg-muted rounded-full flex items-center justify-center mb-6 shadow-sm">
            <FolderPlus className="w-10 h-10 text-muted-foreground" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight mb-2">No projects yet</h2>
          <p className="text-muted-foreground max-w-md mx-auto mb-8">
            You don't have any video projects. Create your first project to start generating cinematic videos from your ideas.
          </p>
          <Button size="lg" onClick={() => setShowNewDialog(true)} className="shadow-md">
            <Plus className="w-5 h-5 mr-2" />
            Create First Project
          </Button>
        </div>
      )}

      {/* New Project Dialog */}
      {showNewDialog && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
          <div className="bg-card border shadow-xl rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
            <div className="p-6 border-b shrink-0 bg-card/95 z-10 rounded-t-2xl">
              <h2 className="text-2xl font-bold tracking-tight">Create New Project</h2>
              <p className="text-muted-foreground mt-1">
                Configure your new video generation project.
              </p>
            </div>
            
            <form onSubmit={handleCreateProject} className="flex flex-col min-h-0">
              <div className="p-6 overflow-y-auto space-y-8 min-h-0">
                {/* Basic Details Section */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Video className="w-5 h-5 text-primary" />
                    Project Details
                  </h3>
                  
                  <div>
                    <label
                      htmlFor="idea"
                      className="block text-sm font-medium mb-1.5"
                    >
                      Video Idea
                    </label>
                    <Textarea
                      id="idea"
                      value={newIdea}
                      onChange={(e) => setNewIdea(e.target.value)}
                      className="min-h-[120px] resize-y bg-background"
                      placeholder="Describe your video idea in detail..."
                      required
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="promptsFile"
                      className="block text-sm font-medium mb-1.5"
                    >
                      Prompts File Path <span className="text-muted-foreground font-normal">(optional)</span>
                    </label>
                    <Input
                      id="promptsFile"
                      type="text"
                      value={promptsFile}
                      onChange={(e) => setPromptsFile(e.target.value)}
                      placeholder="e.g., input/my_prompts.txt"
                      className="bg-background"
                    />
                    <p className="text-xs text-muted-foreground mt-1.5">
                      Skip generation and import shots directly from a text file.
                    </p>
                  </div>
                </div>

                <div className="border-t"></div>

                {/* Configuration Section */}
                <div className="space-y-6">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-primary" />
                    Generation Settings
                  </h3>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium mb-1.5">
                        Aspect Ratio
                      </label>
                      <Select
                        value={selectedAspectRatio}
                        onValueChange={(val) => setSelectedAspectRatio(val as "16:9" | "9:16")}
                      >
                        <SelectTrigger className="bg-background">
                          <SelectValue placeholder="Select Aspect Ratio" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="16:9">16:9 (Landscape - YouTube)</SelectItem>
                          <SelectItem value="9:16">9:16 (Portrait - TikTok/Reels)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div>
                      <label
                        htmlFor="duration"
                        className="block text-sm font-medium mb-1.5"
                      >
                        Target Duration
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
                          className="bg-background"
                        />
                        <span className="text-sm font-medium whitespace-nowrap bg-muted px-3 py-2 rounded-md border min-w-[5rem] text-center">
                          {Math.floor(totalDuration / 60)}m {totalDuration % 60}s
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium mb-1.5">
                        Story Agent
                      </label>
                      <Select
                        value={selectedStoryAgent}
                        onValueChange={(val) => setSelectedStoryAgent(val)}
                      >
                        <SelectTrigger className="bg-background">
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
                      <label className="block text-sm font-medium mb-1.5">
                        Shots Agent
                      </label>
                      <Select
                        value={selectedShotsAgent}
                        onValueChange={(val) => setSelectedShotsAgent(val)}
                      >
                        <SelectTrigger className="bg-background">
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
                </div>
              </div>

              <div className="px-6 py-4 border-t flex gap-3 justify-end shrink-0 bg-card rounded-b-2xl">
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
                  className="min-w-[120px]"
                >
                  {isGeneratingStory ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : createProjectMutation.isPending ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4 mr-2" />
                      Create Project
                    </>
                  )}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
