/**
 * Project detail page
 */
"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useProject } from "@/hooks/useProjects";
import { formatDistanceToNow } from "date-fns";
import { getMediaUrl } from "@/lib/utils";
import { useState } from "react";
import { api } from "@/services/api";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { RefreshCw, ImageIcon, X } from "lucide-react";
import { GenerationDialog, GenerationConfig } from "@/components/shots/GenerationDialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { 
  Tabs, 
  TabsContent, 
  TabsList, 
  TabsTrigger 
} from "@/components/ui/tabs";
import {
  Film,
  Image as LucideImage,
  Clock,
  Video,
  CheckCircle2,
  AlertCircle,
  Settings,
  Edit,
  ArrowLeft,
  BookOpen,
  LayoutDashboard,
  Layers
} from "lucide-react";

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;
  const { data: project, isLoading, error } = useProject(projectId);
  const queryClient = useQueryClient();
  const [generatingThumbnails, setGeneratingThumbnails] = useState<
    Record<string, boolean>
  >({});
  const [imageVersion, setImageVersion] = useState<number>(Date.now());
  const [isUpdatingAspectRatio, setIsUpdatingAspectRatio] = useState(false);

  // Regeneration Modal State
  const [showRegenModal, setShowRegenModal] = useState<"16:9" | "9:16" | null>(
    null,
  );

  const handleUpdateAspectRatio = async (newAspectRatio: "16:9" | "9:16") => {
    try {
      setIsUpdatingAspectRatio(true);
      await api.updateProject(projectId, {
        aspect_ratio: newAspectRatio
      });
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    } catch (error) {
      console.error("Failed to update aspect ratio:", error);
      alert("Failed to update aspect ratio. Please try again.");
    } finally {
      setIsUpdatingAspectRatio(false);
    }
  };

  const handleGenerateThumbnail = async (
    aspectRatio: "16:9" | "9:16",
    config: GenerationConfig
  ) => {
    try {
      setGeneratingThumbnails((prev) => ({ ...prev, [aspectRatio]: true }));
      setShowRegenModal(null);
      await api.generateThumbnail(
        projectId,
        aspectRatio,
        config.force || false,
        config.mode || "comfyui",
        config.workflow || "flux2",
        config.seed === "" ? undefined : config.seed,
      );
      setImageVersion(Date.now());
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    } catch (error) {
      console.error(`Failed to generate ${aspectRatio} thumbnail:`, error);
      alert("Failed to generate thumbnail. Please check the logs.");
    } finally {
      setGeneratingThumbnails((prev) => ({ ...prev, [aspectRatio]: false }));
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

  // Calculate progress percentages
  const imageProgress =
    project.stats.total_shots > 0
      ? (project.stats.images_generated / project.stats.total_shots) * 100
      : 0;
  const videoProgress =
    project.stats.total_shots > 0
      ? (project.stats.videos_rendered / project.stats.total_shots) * 100
      : 0;

  // Calculate counts for stats
  const totalShotsCount = project.shots?.length || project.stats?.total_shots || 0;
  const imagesDoneCount = project.stats?.images_generated || 0;
  const videosDoneCount = project.stats?.videos_rendered || 0;

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/projects"
          className="inline-flex items-center gap-1 text-sm font-medium text-muted-foreground hover:text-primary mb-4 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Projects
        </Link>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-extrabold tracking-tight">
                {project.story?.title || project.idea || project.project_id}
              </h1>
              <span
                className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold backdrop-blur-md ${
                  project.completed
                    ? "bg-green-500/10 text-green-500 border border-green-500/20"
                    : "bg-blue-500/10 text-blue-500 border border-blue-500/20"
                }`}
              >
                {project.completed ? (
                  <CheckCircle2 className="w-3.5 h-3.5" />
                ) : (
                  <AlertCircle className="w-3.5 h-3.5" />
                )}
                {project.completed ? "Completed" : "In Progress"}
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              Started{" "}
              {project.started_at
                ? (() => {
                  try {
                    return formatDistanceToNow(new Date(project.started_at), {
                      addSuffix: true,
                    });
                  } catch (e) {
                    return "Unknown date";
                  }
                })()
                : "Unknown date"}
            </p>
          </div>
          <div className="flex gap-2">
            <Link
              href={`/projects/${projectId}/settings`}
              className="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium border rounded-md hover:bg-muted hover:text-primary transition-all shadow-sm"
            >
              <Settings className="w-4 h-4" />
              Settings
            </Link>
            <Link
              href={`/projects/${projectId}/edit`}
              className="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-all shadow-sm"
            >
              <Edit className="w-4 h-4" />
              Edit Project
            </Link>
          </div>
        </div>

        {/* Quick Stats Banner (Synced with Edit Page) */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-card/50 border border-border/50 rounded-xl p-4 flex items-center gap-4 shadow-sm backdrop-blur-md">
            <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center text-primary">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Total Scenes</p>
              <p className="text-xl font-bold">{project.story?.scenes?.length || 0}</p>
            </div>
          </div>
          <div className="bg-card/50 border border-border/50 rounded-xl p-4 flex items-center gap-4 shadow-sm backdrop-blur-md">
            <div className="w-10 h-10 bg-accent/10 rounded-lg flex items-center justify-center text-accent">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Total Duration</p>
              <p className="text-xl font-bold">
                {project.story?.total_duration ? (
                  `${Math.floor(project.story.total_duration / 60)}:${(project.story.total_duration % 60).toString().padStart(2, "0")}`
                ) : '0:00'}
              </p>
            </div>
          </div>
          <div className="bg-card/50 border border-border/50 rounded-xl p-4 flex items-center gap-4 shadow-sm backdrop-blur-md">
            <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center text-purple-500">
              <Film className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Planned Shots</p>
              <p className="text-xl font-bold">{totalShotsCount}</p>
            </div>
          </div>
          <div className="bg-card/50 border border-border/50 rounded-xl p-4 flex items-center gap-4 shadow-sm backdrop-blur-md">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              project.completed ? "bg-green-500/10 text-green-500" : "bg-blue-500/10 text-blue-500"
            }`}>
              {project.completed ? <CheckCircle2 className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Status</p>
              <p className={`text-xl font-bold ${project.completed ? "text-green-500" : "text-blue-500"}`}>
                {project.completed ? "Completed" : "In Progress"}
              </p>
            </div>
          </div>
        </div>
      </div>

      <Tabs defaultValue="workspace" className="space-y-6">
        <TabsList className="bg-muted p-1 border rounded-lg">
          <TabsTrigger value="workspace" className="gap-1.5">
            <LayoutDashboard className="w-4 h-4" />
            Workspace
          </TabsTrigger>
          <TabsTrigger value="shots" className="gap-1.5">
            <Layers className="w-4 h-4" />
            Shots Board ({totalShotsCount})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="workspace" className="space-y-6">
          <div className="flex flex-col lg:flex-row gap-6">
        {/* Left Sidebar (LumeFlow Style "Model/Prompt" area) */}
        <div className="w-full lg:w-1/3 space-y-6">
          <div className="bg-card border border-border rounded-xl p-5 shadow-lg">
            <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
              <span className="w-4 h-4 rounded-full bg-primary flex items-center justify-center text-[10px] text-primary-foreground">
                💡
              </span>
              Idea
            </h2>
            <div className="bg-input/50 border border-border/50 rounded-lg p-3 min-h-[120px]">
              <p className="text-sm text-foreground/90 whitespace-pre-wrap">
                {project.idea}
              </p>
            </div>

            <div className="mt-6">
              <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <span className="w-4 h-4 rounded-full bg-accent flex items-center justify-center text-[10px]">
                  📐
                </span>
                Aspect Ratio
              </h2>
              <div className="bg-background/50 rounded-lg p-4 border border-border/30">
                <Select
                  value={project.aspect_ratio || "16:9"}
                  onValueChange={(val) => handleUpdateAspectRatio(val as "16:9" | "9:16")}
                  disabled={isUpdatingAspectRatio}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Aspect Ratio" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="16:9">
                      <div className="flex items-center gap-2">
                        <span className="text-sm">16:9 Landscape</span>
                        <span className="text-xs text-muted-foreground">(YouTube, Desktop)</span>
                      </div>
                    </SelectItem>
                    <SelectItem value="9:16">
                      <div className="flex items-center gap-2">
                        <span className="text-sm">9:16 Portrait</span>
                        <span className="text-xs text-muted-foreground">(TikTok, Reels, Shorts)</span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-[10px] text-muted-foreground mt-2">
                  Current: <span className="font-semibold">{project.aspect_ratio || "16:9"}</span>
                  {isUpdatingAspectRatio && " (Updating...)"}
                </p>
              </div>
            </div>

            <div className="mt-6">
              <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                <span className="w-4 h-4 rounded-full bg-secondary flex items-center justify-center text-[10px]">
                  ⚙️
                </span>
                Generation Progress
              </h2>

              {/* Progress Bars styled heavily */}
              <div className="space-y-4 bg-background/50 rounded-lg p-4 border border-border/30">
                {/* Story */}
                <div>
                  <div className="flex justify-between text-xs mb-2">
                    <span className="text-muted-foreground">
                      Story Generation
                    </span>
                    <span className="text-foreground">
                      {project.steps.story ? "Complete" : "Pending"}
                    </span>
                  </div>
                  <div className="w-full bg-input rounded-full h-1.5 overflow-hidden">
                    <div
                      className={`h-full transition-all ${project.steps.story ? "bg-primary" : "bg-transparent"}`}
                      style={{ width: project.steps.story ? "100%" : "0%" }}
                    />
                  </div>
                </div>

                {/* Images */}
                <div>
                  <div className="flex justify-between text-xs mb-2">
                    <span className="text-muted-foreground">
                      Images ({project.stats.images_generated}/
                      {project.stats.total_shots || "-"})
                    </span>
                    <span className="text-foreground">
                      {Math.round(imageProgress)}%
                    </span>
                  </div>
                  <div className="w-full bg-input rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-blue-500 h-full transition-all shadow-[0_0_10px_rgba(59,130,246,0.5)]"
                      style={{ width: `${imageProgress}%` }}
                    />
                  </div>
                </div>

                {/* Videos */}
                <div>
                  <div className="flex justify-between text-xs mb-2">
                    <span className="text-muted-foreground">
                      Videos ({project.stats.videos_rendered}/
                      {project.stats.total_shots || "-"})
                    </span>
                    <span className="text-foreground">
                      {Math.round(videoProgress)}%
                    </span>
                  </div>
                  <div className="w-full bg-input rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-purple-500 h-full transition-all shadow-[0_0_10px_rgba(168,85,247,0.5)]"
                      style={{ width: `${videoProgress}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* 9:16 Portrait Thumbnail moved to main canvas */}
          </div>
        </div>

        {/* Right Main Canvas (LumeFlow Style "Output" area) */}
        <div className="w-full lg:w-2/3 space-y-6">
          {/* Main Thumbnail Banner */}
          {(project.thumbnail_url || project.thumbnail_url_9_16) && (
            <div className="flex flex-col sm:flex-row shadow-lg mb-6 gap-2">
              {project.thumbnail_url_9_16 && (
                <div
                  className={`bg-card border border-border rounded-xl relative ${project.thumbnail_url ? "sm:w-1/4" : "w-full max-w-sm mx-auto"} aspect-[9/16] overflow-hidden`}
                >
                  <img
                    src={getMediaUrl(project.thumbnail_url_9_16, imageVersion)}
                    alt="9:16 Thumbnail"
                    className="w-full h-full object-contain bg-black"
                  />
                </div>
              )}
              {project.thumbnail_url && (
                <div
                  className={`bg-card border border-border rounded-xl overflow-hidden relative ${project.thumbnail_url_9_16 ? "sm:w-3/4" : "w-full"} aspect-video`}
                >
                  <img
                    src={getMediaUrl(project.thumbnail_url, imageVersion)}
                    alt="16:9 Thumbnail"
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
            </div>
          )}

          {project.story && (
            <div className="bg-card border border-border rounded-xl p-6 shadow-lg">
              <div className="mb-6 pb-4 border-b border-border/50">
                <h3 className="text-xl font-bold text-foreground mb-1">
                  {project.story.title}
                </h3>
                <div className="flex flex-wrap gap-2 mt-2">
                  <span className="inline-block px-2.5 py-0.5 rounded text-xs font-medium bg-secondary text-secondary-foreground">
                    {project.story.style}
                  </span>
                  {project.story.tags?.map((tag, idx) => (
                    <span
                      key={idx}
                      className="inline-block px-2.5 py-0.5 rounded text-xs font-medium bg-primary/20 text-primary"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
                {project.story.description && (
                  <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
                    {project.story.description}
                  </p>
                )}
              </div>

              {project.story.master_script && (
                <div className="bg-background/80 p-5 rounded-lg border border-border/50 mb-6">
                  <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3">
                    Master Script
                  </h4>
                  <p className="text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed">
                    {project.story.master_script}
                  </p>
                </div>
              )}

              {/* Thumbnails Section */}
              {(project.story.thumbnail_prompt_16_9 ||
                project.story.thumbnail_prompt_9_16) && (
                  <div className="bg-background/80 p-5 rounded-lg border border-border/50 mb-6">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-0">
                        Thumbnail Prompts & Assets
                      </h4>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* 16:9 Youtube-Style Card */}
                      <div className="flex flex-col gap-3 group">
                        <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-card border border-border/80 shadow-sm transition-all group-hover:border-primary/50 flex flex-col justify-center items-center">
                          {project.thumbnail_url ? (
                            <img
                              src={getMediaUrl(
                                project.thumbnail_url,
                                imageVersion,
                              )}
                              alt="16:9 Thumbnail"
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <div className="flex flex-col items-center justify-center p-6 text-muted-foreground">
                              <ImageIcon className="w-8 h-8 opacity-40 mb-2" />
                              <span className="text-sm font-medium">
                                Coming Soon
                              </span>
                            </div>
                          )}

                          <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-20">
                            <Button
                              variant="secondary"
                              size="sm"
                              className="gap-2 shadow-lg"
                              onClick={() => setShowRegenModal("16:9")}
                              disabled={generatingThumbnails["16:9"]}
                            >
                              {generatingThumbnails["16:9"] ? (
                                <RefreshCw className="w-4 h-4 animate-spin" />
                              ) : (
                                <ImageIcon className="w-4 h-4" />
                              )}
                              {project.thumbnail_url ? "Regenerate" : "Generate"}
                            </Button>
                          </div>
                        </div>

                        <div className="flex flex-col px-1">
                          <div className="flex items-center gap-2 mb-1.5">
                            <span className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0"></span>
                            <h3 className="text-sm font-semibold text-foreground line-clamp-1">
                              Landscape (16:9)
                            </h3>
                          </div>
                          <p
                            className="text-xs text-muted-foreground line-clamp-3 leading-relaxed"
                            title={project.story.thumbnail_prompt_16_9 || ""}
                          >
                            {project.story.thumbnail_prompt_16_9 ||
                              "No prompt available"}
                          </p>
                        </div>
                      </div>

                      {/* 9:16 Youtube-Style Card (forced into 16:9 container scale) */}
                      <div className="flex flex-col gap-3 group">
                        <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-muted/80 border border-border/80 shadow-sm transition-all group-hover:border-primary/50 flex justify-center items-center">
                          {project.thumbnail_url_9_16 ? (
                            <img
                              src={getMediaUrl(
                                project.thumbnail_url_9_16,
                                imageVersion,
                              )}
                              alt="9:16 Thumbnail"
                              className="w-full h-full object-contain max-w-[56.25%] mx-auto bg-black"
                            />
                          ) : (
                            <div className="flex flex-col items-center justify-center p-6 text-muted-foreground">
                              <ImageIcon className="w-8 h-8 opacity-40 mb-2" />
                              <span className="text-sm font-medium">
                                Coming Soon
                              </span>
                            </div>
                          )}

                          <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-20">
                            <Button
                              variant="secondary"
                              size="sm"
                              className="gap-2 shadow-lg"
                              onClick={() => setShowRegenModal("9:16")}
                              disabled={generatingThumbnails["9:16"]}
                            >
                              {generatingThumbnails["9:16"] ? (
                                <RefreshCw className="w-4 h-4 animate-spin" />
                              ) : (
                                <ImageIcon className="w-4 h-4" />
                              )}
                              {project.thumbnail_url_9_16
                                ? "Regenerate"
                                : "Generate"}
                            </Button>
                          </div>
                        </div>

                        <div className="flex flex-col px-1">
                          <div className="flex items-center gap-2 mb-1.5">
                            <span className="w-2 h-2 rounded-full bg-purple-500 flex-shrink-0"></span>
                            <h3 className="text-sm font-semibold text-foreground line-clamp-1">
                              Portrait (9:16)
                            </h3>
                          </div>
                          <p
                            className="text-xs text-muted-foreground line-clamp-3 leading-relaxed"
                            title={project.story.thumbnail_prompt_9_16 || ""}
                          >
                            {project.story.thumbnail_prompt_9_16 ||
                              "No prompt available"}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

              {project.story.scenes && project.story.scenes.length > 0 && (
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-foreground mb-4">
                    Scene Breakdown
                  </h3>
                  <div className="grid grid-cols-1 gap-3">
                    {project.story.scenes.map((scene, idx) => (
                      <div
                        key={idx}
                        className="bg-input/30 border border-border/50 rounded-lg p-4 hover:border-primary/50 transition-colors"
                      >
                        <div className="flex gap-4 items-start">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs font-bold text-primary bg-primary/10 px-2 py-1 rounded">
                                Scene {idx + 1}
                              </span>
                              {scene.scene_duration && (
                                <span className="text-xs text-muted-foreground">
                                  {scene.scene_duration}s
                                </span>
                              )}
                            </div>
                            <p className="text-sm font-medium text-foreground mb-1">
                              {scene.action}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {scene.location} • {scene.characters}
                            </p>
                            {scene.narration && (
                              <div className="mt-3 p-3 bg-background/50 rounded border-l-2 border-secondary/50 text-sm italic text-foreground/80">
                                "{scene.narration}"
                              </div>
                            )}
                          </div>
                          
                          {scene.background_image_path && (
                            <div className="w-24 h-24 sm:w-28 sm:h-28 relative rounded-lg overflow-hidden bg-muted border border-border flex-shrink-0 shadow-sm">
                              <img
                                src={getMediaUrl(scene.background_image_path, imageVersion)}
                                alt={`Scene ${idx + 1} Background`}
                                className="w-full h-full object-cover"
                              />
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </TabsContent>

    <TabsContent value="shots" className="space-y-6">
      {project.shots && project.shots.length > 0 ? (
        <div className="bg-card border border-border rounded-xl p-6 shadow-sm">
          <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
            <Film className="w-5 h-5 text-primary" />
            Shots Timeline ({project.shots.length})
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-6">
            {project.shots.map((shot) => (
              <div key={shot.index} className="group relative flex flex-col gap-3 transition-all duration-300 rounded-xl bg-card border shadow-sm hover:shadow-md hover:-translate-y-1 overflow-hidden">
                <div className="relative aspect-video w-full overflow-hidden bg-muted">
                  {shot.video_rendered && shot.video_path ? (
                    <video
                      src={getMediaUrl(shot.video_path)}
                      poster={shot.image_path ? getMediaUrl(shot.image_path) : undefined}
                      className="w-full h-full object-cover transition-all"
                      controls
                    />
                  ) : shot.image_path ? (
                    <img
                      src={getMediaUrl(shot.image_path)}
                      alt={`Shot ${shot.index}`}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                  ) : (
                    <div className="flex w-full h-full flex-col items-center justify-center bg-muted text-muted-foreground">
                      <LucideImage className="w-10 h-10 mb-2 opacity-30" />
                      <span className="text-xs">No media</span>
                    </div>
                  )}

                  {/* Badges */}
                  <div className="absolute top-2 left-2 z-10 flex gap-1.5 flex-wrap">
                    <span className={`px-2 py-0.5 text-xs font-semibold rounded-md shadow-sm backdrop-blur-md ${
                      shot.image_generated ? "bg-green-500/80 text-white" : "bg-neutral-500/80 text-white"
                    }`}>
                      IMG {shot.image_generated ? "✓" : "○"}
                    </span>
                    <span className={`px-2 py-0.5 text-xs font-semibold rounded-md shadow-sm backdrop-blur-md ${
                      shot.video_rendered ? "bg-purple-500/80 text-white" : "bg-neutral-500/80 text-white"
                    }`}>
                      VID {shot.video_rendered ? "✓" : "○"}
                    </span>
                  </div>

                  <div className="absolute bottom-2 right-2 px-2 py-1 text-xs font-medium text-white bg-black/70 backdrop-blur-sm rounded-md z-10">
                    Shot {shot.index}
                  </div>
                </div>

                <div className="flex flex-col p-4 flex-grow">
                  <div className="flex justify-between text-xs font-medium text-muted-foreground mb-2">
                    <span>{shot.camera || "No Camera Info"}</span>
                  </div>
                  <p className="text-xs text-card-foreground line-clamp-3 leading-relaxed mt-auto" title={shot.image_prompt}>
                    {shot.image_prompt}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-center py-20 border-2 border-dashed rounded-2xl bg-card/30">
          <Film className="w-12 h-12 text-muted-foreground mx-auto mb-4 opacity-40" />
          <h3 className="text-lg font-medium mb-1">No shots planned yet</h3>
          <p className="text-muted-foreground text-sm max-w-sm mx-auto">
            Once you generate a story, shots will appear here for orchestrating the assets.
          </p>
        </div>
      )}
    </TabsContent>
  </Tabs>
      {/* Regeneration Modal */}
      <GenerationDialog
        isOpen={showRegenModal !== null}
        onClose={() => setShowRegenModal(null)}
        type="image"
        projectId={projectId}
        isPending={showRegenModal ? generatingThumbnails[showRegenModal] : false}
        onSubmit={(config) => {
          if (showRegenModal) handleGenerateThumbnail(showRegenModal, config);
        }}
        title={`Generate Thumbnail (${showRegenModal === "16:9" ? "Landscape" : "Portrait"})`}
        hidePrompt={true}
      />
    </div>
  );
}
