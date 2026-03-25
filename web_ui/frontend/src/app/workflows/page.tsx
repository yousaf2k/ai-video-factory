/**
 * Workflows Management Page
 */
"use client";

import { useState, useEffect } from "react";
import {
  useWorkflows,
  useWorkflowContent,
  useUpdateWorkflowContent,
} from "@/hooks/useWorkflows";
import {
  Save,
  RefreshCw,
  FileJson,
  ChevronRight,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export default function WorkflowsPage() {
  const { data: workflows, isLoading: isLoadingWorkflows } = useWorkflows();
  const [selectedWorkflow, setSelectedWorkflow] = useState<{
    category: string;
    filename: string;
  } | null>(null);

  const {
    data: content,
    isLoading: isLoadingContent,
    error: loadError,
  } = useWorkflowContent(
    selectedWorkflow?.category || null,
    selectedWorkflow?.filename || null,
  );

  const [editContent, setEditContent] = useState("");
  const [jsonError, setJsonError] = useState<string | null>(null);

  const updateWorkflowMutation = useUpdateWorkflowContent(
    selectedWorkflow?.category || "",
    selectedWorkflow?.filename || "",
  );

  useEffect(() => {
    if (content !== undefined) {
      setEditContent(content);
      setJsonError(null);
    }
  }, [content]);

  const handleSave = async () => {
    if (!selectedWorkflow) return;

    // Validate JSON before saving
    try {
      JSON.parse(editContent);
      setJsonError(null);
    } catch (e: any) {
      setJsonError(`Invalid JSON: ${e.message}`);
      return;
    }

    try {
      await updateWorkflowMutation.mutateAsync(editContent);
      alert("Workflow JSON updated successfully!");
    } catch (error: any) {
      console.error("Failed to update workflow:", error);
      alert(
        `Failed to update workflow: ${error.response?.data?.detail || error.message}`,
      );
    }
  };

  const formatJson = () => {
    try {
      const parsed = JSON.parse(editContent);
      setEditContent(JSON.stringify(parsed, null, 2));
      setJsonError(null);
    } catch (e: any) {
      setJsonError(`Cannot format: Invalid JSON (${e.message})`);
    }
  };

  if (isLoadingWorkflows) {
    return (
      <div className="container mx-auto px-4 py-8">Loading workflows...</div>
    );
  }

  const categories = Object.keys(workflows || {}).sort();

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">ComfyUI Workflows</h1>
        <p className="text-muted-foreground">
          View and edit the JSON workflow templates for image, video, and voice
          generation
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Sidebar - Workflow List */}
        <div className="lg:col-span-1 border rounded-lg overflow-hidden flex flex-col h-[calc(100vh-250px)]">
          <div className="bg-muted p-3 font-semibold border-b">
            Workflow Categories
          </div>
          <div className="overflow-y-auto flex-1">
            {categories.map((category) => (
              <div key={category} className="mb-2">
                <div className="px-4 py-2 text-xs font-bold uppercase tracking-wider text-muted-foreground bg-card/50">
                  {category}
                </div>
                <div className="space-y-1 p-1">
                  {workflows?.[category]?.map((workflow) => (
                    <button
                      key={workflow.id}
                      onClick={() =>
                        setSelectedWorkflow({
                          category,
                          filename: workflow.filename,
                        })
                      }
                      className={cn(
                        "w-full text-left px-3 py-2 rounded-md text-sm flex items-center justify-between transition-colors",
                        selectedWorkflow?.filename === workflow.filename &&
                          selectedWorkflow?.category === category
                          ? "bg-primary text-primary-foreground"
                          : "hover:bg-muted",
                      )}
                    >
                      <span className="truncate">{workflow.name}</span>
                      <ChevronRight className="w-4 h-4 opacity-50" />
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Main Content - Editor */}
        <div className="lg:col-span-3 border rounded-lg overflow-hidden flex flex-col h-[calc(100vh-250px)]">
          {selectedWorkflow ? (
            <>
              <div className="bg-muted p-3 flex items-center justify-between border-b">
                <div className="flex items-center gap-2">
                  <FileJson className="w-4 h-4 text-blue-500" />
                  <span className="font-semibold">
                    {selectedWorkflow.category} / {selectedWorkflow.filename}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={formatJson}
                    className="px-3 py-1.5 bg-card border rounded-md hover:bg-muted transition-colors text-xs flex items-center gap-1.5"
                  >
                    <Settings className="w-3 h-3" />
                    Format JSON
                  </button>
                  <Button
                    onClick={handleSave}
                    disabled={
                      updateWorkflowMutation.isPending || isLoadingContent
                    }
                    className="flex items-center gap-2"
                  >
                    {updateWorkflowMutation.isPending ? (
                      <>
                        <RefreshCw className="w-3 h-3 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="w-3 h-3" />
                        Save Workflow
                      </>
                    )}
                  </Button>
                </div>
              </div>

              <div className="flex-1 relative">
                {isLoadingContent ? (
                  <div className="absolute inset-0 flex items-center justify-center bg-background/50">
                    <RefreshCw className="w-6 h-6 animate-spin text-primary" />
                  </div>
                ) : (
                  <Textarea
                    value={editContent}
                    onChange={(e) => {
                      setEditContent(e.target.value);
                      if (jsonError) setJsonError(null);
                    }}
                    className={cn(
                      "w-full h-full p-6 font-mono text-sm resize-none focus:outline-none bg-card rounded-none border-0 focus-visible:ring-0",
                      jsonError && "border-red-500 ring-1 ring-red-500",
                    )}
                    placeholder="Paste your workflow JSON here..."
                    spellCheck={false}
                  />
                )}
              </div>

              {jsonError && (
                <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 p-2 text-xs border-t border-red-200 dark:border-red-800">
                  {jsonError}
                </div>
              )}

              <div className="bg-muted/50 p-3 text-xs text-muted-foreground flex justify-between">
                <span>ComfyUI API Format</span>
                <span>Press Format JSON to cleanup indentation</span>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-center flex-col items-center justify-center p-12 text-center text-muted-foreground">
              <FileJson className="w-12 h-12 mb-4 opacity-20" />
              <h3 className="text-lg font-medium mb-2">Select a Workflow</h3>
              <p className="max-w-xs">
                Choose a workflow from the sidebar to view or edit its JSON
                configuration.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
