/**
 * Session detail page
 */
"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { useSession } from "@/hooks/useSessions";
import { formatDistanceToNow } from "date-fns";
import { getMediaUrl } from "@/lib/utils";

export default function SessionDetailPage() {
  const params = useParams();
  const sessionId = params.id as string;
  const { data: session, isLoading, error } = useSession(sessionId);

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
                className={`px-3 py-1 text-sm rounded-full ${
                  session.completed
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
              Video Prompt
            </h2>
            <div className="bg-input/50 border border-border/50 rounded-lg p-3 min-h-[120px]">
              <p className="text-sm text-foreground/90 whitespace-pre-wrap">
                {session.idea}
              </p>
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
          </div>
        </div>

        {/* Right Main Canvas (LumeFlow Style "Output" area) */}
        <div className="w-full lg:w-2/3 space-y-6">
          {session.story && (
            <div className="bg-card border border-border rounded-xl p-6 shadow-lg">
              <div className="mb-6 pb-4 border-b border-border/50">
                <h3 className="text-xl font-bold text-foreground mb-1">
                  {session.story.title}
                </h3>
                <span className="inline-block px-2.5 py-0.5 rounded text-xs font-medium bg-secondary text-secondary-foreground">
                  {session.story.style}
                </span>
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
    </div>
  );
}
