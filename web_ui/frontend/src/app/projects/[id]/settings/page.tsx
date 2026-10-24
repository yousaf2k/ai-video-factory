/**
 * Project Settings Page
 */
"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useProject, useUpdateProject } from "@/hooks/useProjects";
import { useDirectors } from "@/hooks/useDirectors";
import { api } from "@/services/api";
import { Save, RefreshCw, ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { MultiDirectorSelector } from "@/components/directors/MultiDirectorSelector";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function ProjectSettingsPage() {
  const params = useParams();
  const projectId = params.id as string;
  const router = useRouter();

  const { data: project, isLoading, error } = useProject(projectId);
  const { data: directors } = useDirectors();
  const updateProjectMutation = useUpdateProject(projectId);

  const [formData, setFormData] = useState({
    idea: "",
    story_director: "default",
    shots_director: "default",
    prompt_mode: "video" as "video" | "motion",
  });

  useEffect(() => {
    if (project) {
      setFormData({
        idea: project.idea || "",
        story_director: project.story_director || "default",
        shots_director: project.shots_director || "default",
        prompt_mode: project.prompt_mode || "video",
      });
    }
  }, [project]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateProjectMutation.mutateAsync(formData);
      toast.success("Project settings updated successfully!");
      router.push(`/projects/${projectId}`);
    } catch (error) {
      console.error("Failed to update project settings:", error);
      toast.error("Failed to update project settings.");
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        Loading project settings...
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="container mx-auto px-4 py-8 text-red-500">
        Error loading project settings.
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <Link
          href={`/projects/${projectId}`}
          className="text-primary hover:underline mb-4 flex items-center gap-1"
        >
          <ChevronLeft className="w-4 h-4" />
          Back to Project
        </Link>
        <h1 className="text-3xl font-bold">Project Settings</h1>
        <p className="text-muted-foreground">
          Configuration for project:{" "}
          <span className="font-mono text-foreground">{projectId}</span>
        </p>
      </div>

      <form onSubmit={handleSubmit} className="max-w-2xl space-y-8">
        {/* Core Settings */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold border-b pb-2">Core Metadata</h2>

          <div>
            <label className="block text-sm font-medium mb-1">Video Idea</label>
            <Textarea
              value={formData.idea}
              onChange={(e) =>
                setFormData({ ...formData, idea: e.target.value })
              }
              className="min-h-[100px]"
              placeholder="Describe your video idea..."
            />
            <p className="text-xs text-muted-foreground mt-1">
              Changing the idea won't automatically regenerate existing content.
            </p>
          </div>
        </section>

        {/* Director Settings */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold border-b pb-2">
            Director Configuration
          </h2>
          <p className="text-sm text-muted-foreground">
            Default directors to use for regeneration steps in this project.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <MultiDirectorSelector
                availableDirectors={directors?.story || []}
                selectedValue={formData.story_director}
                onChange={(val) => setFormData({ ...formData, story_director: val })}
                label="Default Story Building Blocks"
              />
            </div>

            <div>
              <MultiDirectorSelector
                availableDirectors={directors?.shots || []}
                selectedValue={formData.shots_director}
                onChange={(val) => setFormData({ ...formData, shots_director: val })}
                label="Default Shots Building Blocks"
              />
            </div>
          </div>
        </section>

        {/* Video Prompt Style */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold border-b pb-2">
            Video Prompt Style
          </h2>
          <p className="text-sm text-muted-foreground">
            Which prompt to use when generating videos. Shots can override this
            individually.
          </p>

          <div className="max-w-xs">
            <Select
              value={formData.prompt_mode}
              onValueChange={(val) =>
                setFormData({ ...formData, prompt_mode: val as "video" | "motion" })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Select prompt style" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="video">Video Prompt (detailed, timestamped - MiniMax H3)</SelectItem>
                <SelectItem value="motion">Motion Prompt (short - Wan 2.2)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </section>

        <div className="flex justify-end pt-4 gap-3">
          <Link
            href={`/projects/${projectId}`}
            className="px-6 py-2 border rounded-md hover:bg-muted transition-colors"
          >
            Cancel
          </Link>
          <Button
            type="submit"
            disabled={updateProjectMutation.isPending}
            className="flex items-center gap-2"
          >
            {updateProjectMutation.isPending ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Settings
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
