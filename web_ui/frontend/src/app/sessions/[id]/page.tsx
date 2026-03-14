/**
 * Session detail page
 */
"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useSession } from "@/hooks/useSessions";
import { formatDistanceToNow } from "date-fns";
import { getMediaUrl } from "@/lib/utils";
import { useState } from "react";
import { api } from "@/services/api";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { RefreshCw, ImageIcon, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function SessionDetailPage() {
  const params = useParams();
  const sessionId = params.id as string;
  const { data: session, isLoading, error } = useSession(sessionId);
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
  const [regenImageMode, setRegenImageMode] = useState<string>("comfyui");
  const [regenImageWorkflow, setRegenImageWorkflow] = useState<string>("flux2");
  const [regenSeed, setRegenSeed] = useState<number | "">("");
  const [regenForce, setRegenForce] = useState(true);

  const handleUpdateAspectRatio = async (newAspectRatio: "16:9" | "9:16") => {
    try {
      setIsUpdatingAspectRatio(true);
      await api.updateSession(sessionId, {
        aspect_ratio: newAspectRatio
      });
      queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    } catch (error) {
      console.error("Failed to update aspect ratio:", error);
      alert("Failed to update aspect ratio. Please try again.");
    } finally {
      setIsUpdatingAspectRatio(false);
    }
  };

  const handleGenerateThumbnail = async (aspectRatio: "16:9" | "9:16") => {
    try {
      setGeneratingThumbnails((prev) => ({ ...prev, [aspectRatio]: true }));
      setShowRegenModal(null);
      await api.generateThumbnail(
        sessionId,
        aspectRatio,
        regenForce,
        regenImageMode,
        regenImageWorkflow,
        regenSeed === "" ? undefined : regenSeed,
      );
      setImageVersion(Date.now());
      queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
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

  // Calculate progress percentages
  const imageProgress =
    session.stats.total_shots > 0
      ? (session.stats.images_generated / session.stats.total_shots) * 100
      : 0;
  const videoProgress =
    session.stats.total_shots > 0
      ? (session.stats.videos_rendered / session.stats.total_shots) * 100
      : 0;

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/sessions"
          className="text-primary hover:underline mb-4 inline-block"
        >
          ← Back to Sessions
        </Link>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold">{session.session_id}</h1>
              <span
                className={`px-3 py-1 text-sm rounded-full ${session.completed
                    ? "bg-green-100 text-green-800"
                    : "bg-yellow-100 text-yellow-800"
                  }`}
              >
                {session.completed ? "Completed" : "In Progress"}
              </span>
            </div>
            <p className="text-muted-foreground">
              Started{" "}
              {session.started_at
                ? (() => {
                  try {
                    return formatDistanceToNow(new Date(session.started_at), {
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
              href={`/sessions/${sessionId}/settings`}
              className="px-4 py-2 border rounded-md hover:bg-muted transition-colors"
            >
              Settings
            </Link>
            <Link
              href={`/sessions/${sessionId}/edit`}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
            >
              Edit Session
            </Link>
          </div>
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div className="flex flex-col lg:flex-row gap-6 mb-8">
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
                {session.idea}
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
                  value={session.aspect_ratio || "16:9"}
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
                  Current: <span className="font-semibold">{session.aspect_ratio || "16:9"}</span>
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
                      {session.steps.story ? "Complete" : "Pending"}
                    </span>
                  </div>
                  <div className="w-full bg-input rounded-full h-1.5 overflow-hidden">
                    <div
                      className={`h-full transition-all ${session.steps.story ? "bg-primary" : "bg-transparent"}`}
                      style={{ width: session.steps.story ? "100%" : "0%" }}
                    />
                  </div>
                </div>

                {/* Images */}
                <div>
                  <div className="flex justify-between text-xs mb-2">
                    <span className="text-muted-foreground">
                      Images ({session.stats.images_generated}/
                      {session.stats.total_shots || "-"})
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
                      Videos ({session.stats.videos_rendered}/
                      {session.stats.total_shots || "-"})
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
          {(session.thumbnail_url || session.thumbnail_url_9_16) && (
            <div className="flex flex-col sm:flex-row shadow-lg mb-6 gap-2">
              {session.thumbnail_url_9_16 && (
                <div
                  className={`bg-card border border-border rounded-xl relative ${session.thumbnail_url ? "sm:w-1/4" : "w-full max-w-sm mx-auto"} aspect-[9/16] overflow-hidden`}
                >
                  <img
                    src={getMediaUrl(session.thumbnail_url_9_16, imageVersion)}
                    alt="9:16 Thumbnail"
                    className="w-full h-full object-contain bg-black"
                  />
                </div>
              )}
              {session.thumbnail_url && (
                <div
                  className={`bg-card border border-border rounded-xl overflow-hidden relative ${session.thumbnail_url_9_16 ? "sm:w-3/4" : "w-full"} aspect-video`}
                >
                  <img
                    src={getMediaUrl(session.thumbnail_url, imageVersion)}
                    alt="16:9 Thumbnail"
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
            </div>
          )}

          {session.story && (
            <div className="bg-card border border-border rounded-xl p-6 shadow-lg">
              <div className="mb-6 pb-4 border-b border-border/50">
                <h3 className="text-xl font-bold text-foreground mb-1">
                  {session.story.title}
                </h3>
                <div className="flex flex-wrap gap-2 mt-2">
                  <span className="inline-block px-2.5 py-0.5 rounded text-xs font-medium bg-secondary text-secondary-foreground">
                    {session.story.style}
                  </span>
                  {session.story.tags?.map((tag, idx) => (
                    <span
                      key={idx}
                      className="inline-block px-2.5 py-0.5 rounded text-xs font-medium bg-primary/20 text-primary"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
                {session.story.description && (
                  <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
                    {session.story.description}
                  </p>
                )}
              </div>

              {session.story.master_script && (
                <div className="bg-background/80 p-5 rounded-lg border border-border/50 mb-6">
                  <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3">
                    Master Script
                  </h4>
                  <p className="text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed">
                    {session.story.master_script}
                  </p>
                </div>
              )}

              {/* Thumbnails Section */}
              {(session.story.thumbnail_prompt_16_9 ||
                session.story.thumbnail_prompt_9_16) && (
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
                          {session.thumbnail_url ? (
                            <img
                              src={getMediaUrl(
                                session.thumbnail_url,
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
                              {session.thumbnail_url ? "Regenerate" : "Generate"}
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
                            title={session.story.thumbnail_prompt_16_9 || ""}
                          >
                            {session.story.thumbnail_prompt_16_9 ||
                              "No prompt available"}
                          </p>
                        </div>
                      </div>

                      {/* 9:16 Youtube-Style Card (forced into 16:9 container scale) */}
                      <div className="flex flex-col gap-3 group">
                        <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-muted/80 border border-border/80 shadow-sm transition-all group-hover:border-primary/50 flex justify-center items-center">
                          {session.thumbnail_url_9_16 ? (
                            <img
                              src={getMediaUrl(
                                session.thumbnail_url_9_16,
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
                              {session.thumbnail_url_9_16
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
                            title={session.story.thumbnail_prompt_9_16 || ""}
                          >
                            {session.story.thumbnail_prompt_9_16 ||
                              "No prompt available"}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

              {session.story.scenes && session.story.scenes.length > 0 && (
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-foreground mb-4">
                    Scene Breakdown
                  </h3>
                  <div className="grid grid-cols-1 gap-3">
                    {session.story.scenes.map((scene, idx) => (
                      <div
                        key={idx}
                        className="bg-input/30 border border-border/50 rounded-lg p-4 hover:border-primary/50 transition-colors"
                      >
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
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Shots Section */}
      {session.shots && session.shots.length > 0 && (
        <div className="border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">
            Shots ({session.shots.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {session.shots.slice(0, 12).map((shot) => (
              <div key={shot.index} className="border rounded p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">Shot {shot.index}</span>
                  <span className="text-xs text-muted-foreground">
                    {shot.camera}
                  </span>
                </div>

                {/* Media Preview */}
                <div className="mb-2 aspect-video bg-muted rounded overflow-hidden relative group flex items-center justify-center">
                  {shot.video_rendered && shot.video_path ? (
                    <video
                      src={getMediaUrl(shot.video_path)}
                      poster={getMediaUrl(shot.image_path)}
                      controls
                      className="w-full h-full object-cover"
                    />
                  ) : shot.image_path ? (
                    <img
                      src={getMediaUrl(shot.image_path)}
                      alt={`Shot ${shot.index}`}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <span className="text-muted-foreground text-xs">
                      No media
                    </span>
                  )}
                </div>

                {/* Status */}
                <div className="flex gap-2 text-xs mb-2">
                  <span
                    className={
                      shot.image_generated ? "text-green-600" : "text-gray-400"
                    }
                  >
                    Image: {shot.image_generated ? "✓" : "○"}
                  </span>
                  <span
                    className={
                      shot.video_rendered ? "text-green-600" : "text-gray-400"
                    }
                  >
                    Video: {shot.video_rendered ? "✓" : "○"}
                  </span>
                </div>

                {/* Prompts */}
                <div className="text-xs text-muted-foreground line-clamp-2">
                  {shot.image_prompt}
                </div>
              </div>
            ))}
          </div>

          {session.shots.length > 12 && (
            <div className="text-center mt-4 text-muted-foreground">
              And {session.shots.length - 12} more shots...
            </div>
          )}
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
              Generate Thumbnail (
              {showRegenModal === "16:9" ? "Landscape" : "Portrait"})
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
                        <SelectItem value="flux">Flux (Standard)</SelectItem>
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
                          e.target.value === "" ? "" : parseInt(e.target.value),
                        )
                      }
                      placeholder="Random (leave empty)"
                      className="h-8 text-xs"
                    />
                  </div>
                </>
              )}

              <div className="flex justify-end gap-2 mt-6">
                <Button
                  variant="outline"
                  onClick={() => setShowRegenModal(null)}
                >
                  Cancel
                </Button>
                <Button
                  onClick={() => {
                    if (showRegenModal) handleGenerateThumbnail(showRegenModal);
                  }}
                  disabled={Boolean(
                    showRegenModal && generatingThumbnails[showRegenModal],
                  )}
                >
                  {showRegenModal && generatingThumbnails[showRegenModal] ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />{" "}
                      Generating...
                    </>
                  ) : (
                    "Generate"
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
