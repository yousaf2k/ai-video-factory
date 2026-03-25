/**
 * Project Settings Page
 */
"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useProject, useUpdateProject } from "@/hooks/useProjects";
import { useAgents } from "@/hooks/useAgents";
import { api } from "@/services/api";
import { Save, RefreshCw, ChevronLeft, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
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
  const { data: agents } = useAgents();
  const updateProjectMutation = useUpdateProject(projectId);

  const [formData, setFormData] = useState({
    idea: "",
    story_agent: "default",
    shots_agent: "default",
  });
  const [isLaunchingBrowser, setIsLaunchingBrowser] = useState(false);

  useEffect(() => {
    if (project) {
      setFormData({
        idea: project.idea || "",
        story_agent: project.story_agent || "default",
        shots_agent: project.shots_agent || "default",
      });
    }
  }, [project]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateProjectMutation.mutateAsync(formData);
      alert("Project settings updated successfully!");
      router.push(`/projects/${projectId}`);
    } catch (error) {
      console.error("Failed to update project settings:", error);
      alert("Failed to update project settings.");
    }
  };

  const handleLaunchBrowser = async () => {
    console.log("Launching browser...");
    setIsLaunchingBrowser(true);
    try {
      const data = await api.launchBrowser();
      alert(data.message || "Browser launched successfully!");
    } catch (error: any) {
      console.error("Error launching browser:", error);
      const detail = error.response?.data?.detail || error.message;
      alert(`Error launching browser: ${detail}`);
    } finally {
      setIsLaunchingBrowser(false);
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

        {/* Agent Settings */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold border-b pb-2">
            Agent Configuration
          </h2>
          <p className="text-sm text-muted-foreground">
            Default agents to use for regeneration steps in this project.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium mb-1">
                Story Agent
              </label>
              <Select
                value={formData.story_agent}
                onValueChange={(val) =>
                  setFormData({ ...formData, story_agent: val })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select Agent" />
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
                value={formData.shots_agent}
                onValueChange={(val) =>
                  setFormData({ ...formData, shots_agent: val })
                }
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
        </section>

        {/* Browser Setup */}
        <section className="space-y-4">
          <h2 className="text-xl font-semibold border-b pb-2">Browser Setup</h2>
          <p className="text-sm text-muted-foreground">
            If you are having trouble with Google login being blocked, use this
            button to launch a browser with persistent context and stealth
            settings. Once you log in there, Google will recognize your project
            in future automated runs.
          </p>
          <Button
            type="button"
            variant="outline"
            onClick={handleLaunchBrowser}
            disabled={isLaunchingBrowser}
            className="flex items-center gap-2"
          >
            {isLaunchingBrowser ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Launching...
              </>
            ) : (
              <>
                <Globe className="w-4 h-4" />
                Launch Browser for Login
              </>
            )}
          </Button>
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
