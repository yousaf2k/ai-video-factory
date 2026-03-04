/**
 * Agents Management Page
 */
"use client";

import { useState, useEffect } from "react";
import {
  useAgents,
  useAgentContent,
  useUpdateAgentContent,
} from "@/hooks/useAgents";
import {
  Save,
  RefreshCw,
  FileText,
  ChevronRight,
  Eye,
  Code,
} from "lucide-react";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export default function AgentsPage() {
  const { data: agents, isLoading: isLoadingAgents } = useAgents();
  const [selectedAgent, setSelectedAgent] = useState<{
    type: string;
    id: string;
  } | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  const { data: content, isLoading: isLoadingContent } = useAgentContent(
    selectedAgent?.type || null,
    selectedAgent?.id || null,
  );

  const [editContent, setEditContent] = useState("");
  const updateAgentMutation = useUpdateAgentContent(
    selectedAgent?.type || "",
    selectedAgent?.id || "",
  );

  useEffect(() => {
    if (content !== undefined) {
      setEditContent(content);
    }
  }, [content]);

  // Reset preview when changing agent
  useEffect(() => {
    setShowPreview(false);
  }, [selectedAgent]);

  const handleSave = async () => {
    if (!selectedAgent) return;
    try {
      await updateAgentMutation.mutateAsync(editContent);
      alert("Agent prompt updated successfully!");
    } catch (error) {
      console.error("Failed to update agent:", error);
      alert("Failed to update agent.");
    }
  };

  if (isLoadingAgents) {
    return <div className="container mx-auto px-4 py-8">Loading agents...</div>;
  }

  const agentTypes = ["story", "image", "video", "narration"];

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">AI Agents</h1>
        <p className="text-muted-foreground">
          View and edit the system prompts for your AI agents
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Sidebar - Agent List */}
        <div className="lg:col-span-1 border rounded-lg overflow-hidden flex flex-col h-[calc(100vh-250px)]">
          <div className="bg-muted p-3 font-semibold border-b">
            Available Agents
          </div>
          <div className="overflow-y-auto flex-1">
            {agentTypes.map((type) => (
              <div key={type} className="mb-2">
                <div className="px-4 py-2 text-xs font-bold uppercase tracking-wider text-muted-foreground bg-card/50">
                  {type}
                </div>
                <div className="space-y-1 p-1">
                  {agents?.[type as keyof typeof agents]?.map((agent) => (
                    <button
                      key={agent.id}
                      onClick={() => setSelectedAgent({ type, id: agent.id })}
                      className={cn(
                        "w-full text-left px-3 py-2 rounded-md text-sm flex items-center justify-between transition-colors",
                        selectedAgent?.id === agent.id &&
                          selectedAgent?.type === type
                          ? "bg-primary text-primary-foreground"
                          : "hover:bg-muted",
                      )}
                    >
                      <span className="truncate">{agent.name}</span>
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
          {selectedAgent ? (
            <>
              <div className="bg-muted p-2 flex items-center justify-between border-b">
                <div className="flex items-center gap-2 px-2">
                  <FileText className="w-4 h-4" />
                  <span className="font-semibold text-sm">
                    {selectedAgent.type} / {selectedAgent.id}.md
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex bg-card border rounded-md p-1 mr-2">
                    <button
                      onClick={() => setShowPreview(false)}
                      className={cn(
                        "px-3 py-1 text-xs rounded-sm flex items-center gap-1.5 transition-colors",
                        !showPreview
                          ? "bg-muted text-foreground"
                          : "text-muted-foreground hover:bg-muted/50",
                      )}
                    >
                      <Code className="w-3.5 h-3.5" />
                      Edit
                    </button>
                    <button
                      onClick={() => setShowPreview(true)}
                      className={cn(
                        "px-3 py-1 text-xs rounded-sm flex items-center gap-1.5 transition-colors",
                        showPreview
                          ? "bg-muted text-foreground"
                          : "text-muted-foreground hover:bg-muted/50",
                      )}
                    >
                      <Eye className="w-3.5 h-3.5" />
                      Preview
                    </button>
                  </div>
                  <Button
                    onClick={handleSave}
                    disabled={updateAgentMutation.isPending || isLoadingContent}
                    className="flex items-center gap-2"
                  >
                    {updateAgentMutation.isPending ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="w-3.5 h-3.5" />
                        Save Changes
                      </>
                    )}
                  </Button>
                </div>
              </div>

              <div className="flex-1 relative overflow-hidden flex flex-col">
                {isLoadingContent ? (
                  <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10">
                    <RefreshCw className="w-6 h-6 animate-spin text-primary" />
                  </div>
                ) : showPreview ? (
                  <div className="flex-1 overflow-y-auto p-8 bg-card">
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {editContent}
                      </ReactMarkdown>
                    </div>
                  </div>
                ) : (
                  <Textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="flex-1 w-full p-6 font-mono text-sm resize-none focus:outline-none bg-card rounded-none border-0 focus-visible:ring-0"
                    placeholder="Paste your agent prompt here..."
                    spellCheck={false}
                  />
                )}
              </div>

              <div className="bg-muted/50 p-3 text-xs text-muted-foreground flex justify-between border-t">
                <span>
                  Tip: Use {"{USER_INPUT}"} as a placeholder for the user's
                  request.
                </span>
                <span>{showPreview ? "Preview mode" : "Markdown editor"}</span>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-center flex-col items-center justify-center p-12 text-center text-muted-foreground">
              <FileText className="w-12 h-12 mb-4 opacity-20" />
              <h3 className="text-lg font-medium mb-2">Select an Agent</h3>
              <p className="max-w-xs">
                Choose an agent from the sidebar to view or edit its system
                prompt.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
