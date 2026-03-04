/**
 * Sessions list page
 */
"use client";

import { useState } from "react";
import Link from "next/link";
import { Trash2, Copy, ImageIcon, RefreshCw, PlaySquare } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import {
  useSessions,
  useCreateSession,
  useDeleteSession,
  useDuplicateSession,
} from "@/hooks/useSessions";
import { useAgents } from "@/hooks/useAgents";
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
import type { CreateSessionRequest } from "@/types";
import { formatDistanceToNow } from "date-fns";

export default function SessionsPage() {
  const queryClient = useQueryClient();
  const { data: sessions, isLoading, error } = useSessions();
  const { data: agents } = useAgents();
  const createSessionMutation = useCreateSession();
  const deleteSessionMutation = useDeleteSession();
  const duplicateSessionMutation = useDuplicateSession();

  const [showNewDialog, setShowNewDialog] = useState(false);
  const [newIdea, setNewIdea] = useState("");
  const [isGeneratingStory, setIsGeneratingStory] = useState(false);

  // Agent selection state
  const [selectedStoryAgent, setSelectedStoryAgent] = useState("default");
  const [selectedShotsAgent, setSelectedShotsAgent] = useState("default");
  const [totalDuration, setTotalDuration] = useState(600);
  const [promptsFile, setPromptsFile] = useState("");
  const [generatingThumbnails, setGeneratingThumbnails] = useState<
    Record<string, boolean>
  >({});

  const handleGenerateThumbnail = async (sessionId: string) => {
    try {
      setGeneratingThumbnails((prev) => ({ ...prev, [sessionId]: true }));
      await api.generateThumbnail(sessionId, "16:9", true);
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    } catch (error) {
      console.error("Failed to generate thumbnail:", error);
    } finally {
      setGeneratingThumbnails((prev) => ({ ...prev, [sessionId]: false }));
    }
  };

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newIdea.trim()) return;

    const request: CreateSessionRequest = {
      idea: newIdea,
      story_agent: selectedStoryAgent,
      shots_agent: selectedShotsAgent,
      total_duration: totalDuration,
      prompts_file: promptsFile.trim() || undefined,
    };

    try {
      setIsGeneratingStory(true);
      const session = await createSessionMutation.mutateAsync(request);

      try {
        // Automatically generate the initial story ONLY if not using a prompts file
        if (!request.prompts_file) {
          await api.regenerateStory(session.session_id, request.story_agent);
        }
      } catch (storyError) {
        console.error("Failed to generate initial story:", storyError);
        // Continue to the session page even if story generation fails
      }

      setShowNewDialog(false);
      setNewIdea("");
      setPromptsFile("");
      // Navigate to the new session
      window.location.href = `/sessions/${session.session_id}`;
    } catch (error) {
      console.error("Failed to create session:", error);
      alert("Failed to create session. Please try again.");
    } finally {
      setIsGeneratingStory(false);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (
      !confirm(
        "Are you sure you want to delete this session? This action cannot be undone.",
      )
    ) {
      return;
    }

    try {
      await deleteSessionMutation.mutateAsync(sessionId);
    } catch (error) {
      console.error("Failed to delete session:", error);
      alert("Failed to delete session. Please try again.");
    }
  };

  const handleDuplicateSession = async (sessionId: string) => {
    try {
      const session = await duplicateSessionMutation.mutateAsync({ sessionId });
      // Navigate to the duplicated session
      window.location.href = `/sessions/${session.session_id}`;
    } catch (error) {
      console.error("Failed to duplicate session:", error);
      alert("Failed to duplicate session. Please try again.");
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading sessions...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-500">Error loading sessions</div>
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
        <Button onClick={() => setShowNewDialog(true)}>New Session</Button>
      </div>

      {/* Sessions Grid */}
      {sessions && sessions.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-y-10 gap-x-4">
          {sessions.map((session) => (
            <div
              key={session.session_id}
              className="group relative flex flex-col gap-3 transition-colors rounded-xl hover:bg-muted/30 p-2 -m-2"
            >
              {/* Thumbnail Container */}
              <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-muted outline outline-1 outline-transparent group-hover:outline-border transition-all">
                {session.thumbnail_url ? (
                  <img
                    src={session.thumbnail_url}
                    alt={session.idea}
                    className="object-cover w-full h-full"
                  />
                ) : (
                  <div className="flex w-full h-full flex-col items-center justify-center bg-card text-muted-foreground relative">
                    <ImageIcon className="w-8 h-8 mb-2 opacity-50" />
                    <span className="text-sm font-medium">Coming Soon</span>
                  </div>
                )}

                {/* Generate Button Overlay */}
                <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-20">
                  <Button
                    variant="secondary"
                    size="sm"
                    className="gap-2 shadow-lg"
                    onClick={(e) => {
                      e.preventDefault();
                      handleGenerateThumbnail(session.session_id);
                    }}
                    disabled={generatingThumbnails[session.session_id]}
                  >
                    {generatingThumbnails[session.session_id] ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <ImageIcon className="w-4 h-4" />
                    )}
                    {generatingThumbnails[session.session_id]
                      ? "Generating..."
                      : "Generate Thumbnail"}
                  </Button>
                </div>

                {/* Duration / Status Badges on Thumbnail */}
                <div className="absolute bottom-1 right-1 px-1.5 py-0.5 text-xs font-medium text-white bg-black/80 rounded z-10">
                  {session.completed ? "Done" : "In Progress"}
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
                    title={session.idea}
                  >
                    {session.story?.title || session.idea}
                  </h3>
                  <div className="text-xs text-muted-foreground mt-1 flex flex-col gap-0.5">
                    <span className="truncate">
                      {session.started_at
                        ? (() => {
                            try {
                              return formatDistanceToNow(
                                new Date(session.started_at),
                                { addSuffix: true },
                              );
                            } catch (e) {
                              return "Unknown date";
                            }
                          })()
                        : "Unknown date"}
                    </span>
                    <span className="truncate">
                      {session.videos_rendered} videos • {session.total_shots}{" "}
                      shots
                    </span>
                  </div>
                </div>
              </div>

              <Link
                href={`/sessions/${session.session_id}`}
                className="absolute inset-0 z-10"
              >
                <span className="sr-only">View Session</span>
              </Link>

              {/* Action Menu overlay in corner */}
              <div className="absolute top-4 right-4 z-30 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                <Button
                  variant="secondary"
                  size="icon"
                  className="w-8 h-8 rounded-full shadow-md bg-background/80 hover:bg-background"
                  onClick={(e) => {
                    e.preventDefault();
                    handleDuplicateSession(session.session_id);
                  }}
                  title="Duplicate session"
                >
                  <Copy className="w-4 h-4" />
                </Button>
                <Button
                  variant="destructive"
                  size="icon"
                  className="w-8 h-8 rounded-full shadow-md"
                  onClick={(e) => {
                    e.preventDefault();
                    handleDeleteSession(session.session_id);
                  }}
                  title="Delete session"
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
            No sessions yet. Create your first session!
          </p>
          <Button onClick={() => setShowNewDialog(true)}>Create Session</Button>
        </div>
      )}

      {/* New Session Dialog */}
      {showNewDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Create New Session</h2>
            <form onSubmit={handleCreateSession}>
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
                    createSessionMutation.isPending || isGeneratingStory
                  }
                >
                  {isGeneratingStory
                    ? "Generating Story..."
                    : createSessionMutation.isPending
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
