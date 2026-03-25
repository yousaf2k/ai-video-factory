/**
 * SceneCard component - Individual scene in the story editor
 */
import { useState } from "react";
import { GripVertical, Trash2, Edit3, Check, Mic, Play, Pause, X, Loader2, ChevronDown, CheckCircle2 } from "lucide-react";
import { Scene } from "@/types";
import { cn } from "@/lib/utils";
import SceneBackgroundManager from "@/components/scenes/SceneBackgroundManager";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useGenerateSceneNarration, useSelectSceneNarration, useCancelSceneNarration } from "@/hooks/useShots";
import { useParams } from "next/navigation";
import { Progress } from "@/components/ui/progress";

interface SceneCardProps {
  scene: Scene;
  index: number;
  isDragging?: boolean;
  onUpdate?: (index: number, scene: Scene) => void;
  onDelete?: (index: number) => void;
  progress?: number;
  projectType?: number;
}

export function SceneCard({
  scene,
  index,
  isDragging,
  onUpdate,
  onDelete,
  progress,
  projectType,
}: SceneCardProps) {
  const params = useParams();
  const projectId = params.id as string;
  const [isEditing, setIsEditing] = useState(false);
  const [editedScene, setEditedScene] = useState<Scene>(scene);
  const [isGenDialogOpen, setIsGenDialogOpen] = useState(false);

  // Generation Settings
  const [ttsMethod, setTtsMethod] = useState("local");
  const [ttsWorkflow, setTtsWorkflow] = useState("default");
  const [voice, setVoice] = useState("en-US-AriaNeural");

  const generateNarration = useGenerateSceneNarration(projectId!);
  const selectNarration = useSelectSceneNarration(projectId!);
  const cancelNarration = useCancelSceneNarration(projectId!);

  const handleSave = () => {
    onUpdate?.(index, editedScene);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedScene(scene);
    setIsEditing(false);
  };

  const handleGenerate = () => {
    generateNarration.mutate({
      sceneIndex: index,
      config: {
        tts_method: ttsMethod,
        tts_workflow: ttsMethod === "comfyui" ? ttsWorkflow : undefined,
        voice: voice
      }
    });
    setIsGenDialogOpen(false);
  };

  const isGenerating = progress !== undefined && progress >= 0;

  if (isEditing) {
    return (
      <div
        className={cn(
          "border rounded-lg p-4 bg-background shadow-sm",
          isDragging && "opacity-50",
        )}
      >
        <div className="flex items-start gap-3 mb-3">
          <GripVertical className="mt-1 text-muted-foreground cursor-move" />
          <div className="flex-1 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-muted-foreground">
                Scene {index + 1}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleCancel}
                  className="h-8 w-8"
                >
                  <X className="w-4 h-4" />
                </Button>
                <Button
                  size="icon"
                  onClick={handleSave}
                  className="h-8 w-8"
                >
                  <Check className="w-4 h-4" />
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-muted-foreground">Location</label>
                <Input
                  value={editedScene.location}
                  onChange={(e) => setEditedScene({ ...editedScene, location: e.target.value })}
                  className="mt-1 h-8 text-sm"
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground">Characters</label>
                <Input
                  value={editedScene.characters}
                  onChange={(e) => setEditedScene({ ...editedScene, characters: e.target.value })}
                  className="mt-1 h-8 text-sm"
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground">Action</label>
                <Input
                  value={editedScene.action}
                  onChange={(e) => setEditedScene({ ...editedScene, action: e.target.value })}
                  className="mt-1 h-8 text-sm"
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground">Emotion</label>
                <Input
                  value={editedScene.emotion}
                  onChange={(e) => setEditedScene({ ...editedScene, emotion: e.target.value })}
                  className="mt-1 h-8 text-sm"
                />
              </div>

              <div className="md:col-span-2">
                <label className="text-xs text-muted-foreground">Narration</label>
                <Textarea
                  value={editedScene.narration}
                  onChange={(e) => setEditedScene({ ...editedScene, narration: e.target.value })}
                  className="mt-1 min-h-[60px] text-sm"
                />
              </div>

              <div className="md:col-span-2">
                <label className="text-xs text-muted-foreground">Set Prompt (for background generation)</label>
                <Textarea
                  value={editedScene.set_prompt || ""}
                  onChange={(e) => setEditedScene({ ...editedScene, set_prompt: e.target.value })}
                  className="mt-1 min-h-[40px] text-sm"
                  placeholder="Describe the background explicitly..."
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground">Duration (seconds)</label>
                <Input
                  type="number"
                  value={editedScene.scene_duration || ""}
                  onChange={(e) => setEditedScene({
                    ...editedScene,
                    scene_duration: e.target.value ? parseInt(e.target.value) : undefined
                  })}
                  className="mt-1 h-8 text-sm"
                  min="5"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "border rounded-lg p-4 bg-background hover:shadow-md transition-all group",
        isDragging && "opacity-50",
        isGenerating && "border-primary/50 bg-primary/5"
      )}
    >
      <div className="flex items-start gap-3">
        <GripVertical className="mt-1 text-muted-foreground cursor-move" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-primary">
                SCENE {index + 1}
              </span>
              {scene.narration_path && (
                <CheckCircle2 className="w-4 h-4 text-green-500" />
              )}
            </div>

            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <Dialog open={isGenDialogOpen} onOpenChange={setIsGenDialogOpen}>
                <DialogTrigger asChild>
                  <Button variant="ghost" size="sm" className="h-8 gap-1 text-xs" disabled={isGenerating}>
                    <Mic className="w-3.5 h-3.5" />
                    Narration
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Generate Narration</DialogTitle>
                    <DialogDescription>
                      Configure Text-to-Speech settings for Scene {index + 1}.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                      <label className="text-right text-sm">Method</label>
                      <Select value={ttsMethod} onValueChange={setTtsMethod}>
                        <SelectTrigger className="col-span-3">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="local">Local TTS (Edge)</SelectItem>
                          <SelectItem value="elevenlabs">ElevenLabs API</SelectItem>
                          <SelectItem value="comfyui">ComfyUI Workflow</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {ttsMethod === "comfyui" && (
                      <div className="grid grid-cols-4 items-center gap-4">
                        <label className="text-right text-sm">Workflow</label>
                        <Select value={ttsWorkflow} onValueChange={setTtsWorkflow}>
                          <SelectTrigger className="col-span-3">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="default">Default TTS</SelectItem>
                            {/* Dynamically list from config if possible, or leave as default */}
                          </SelectContent>
                        </Select>
                      </div>
                    )}

                    <div className="grid grid-cols-4 items-center gap-4">
                      <label className="text-right text-sm">Voice</label>
                      <Select value={voice} onValueChange={setVoice}>
                        <SelectTrigger className="col-span-3">
                          <SelectValue placeholder="Select Voice" />
                        </SelectTrigger>
                        <SelectContent>
                          {ttsMethod === "local" ? (
                            <>
                              <SelectItem value="en-US-AriaNeural">Aria (Female)</SelectItem>
                              <SelectItem value="en-US-GuyNeural">Guy (Male)</SelectItem>
                              <SelectItem value="en-GB-SoniaNeural">Sonia (UK Female)</SelectItem>
                              <SelectItem value="en-GB-RyanNeural">Ryan (UK Male)</SelectItem>
                            </>
                          ) : ttsMethod === "elevenlabs" ? (
                            <>
                              <SelectItem value="premade/adam">Adam (Deep Engine)</SelectItem>
                              <SelectItem value="premade/antoni">Antoni (Soothing)</SelectItem>
                              <SelectItem value="premade/bella">Bella (Soft)</SelectItem>
                            </>
                          ) : (
                            <>
                              <SelectItem value="default_female.wav">Default Female</SelectItem>
                              <SelectItem value="default_male.wav">Default Male</SelectItem>
                            </>
                          )}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button variant="outline" onClick={() => setIsGenDialogOpen(false)}>Cancel</Button>
                    <Button onClick={handleGenerate} disabled={generateNarration.isPending}>
                      {generateNarration.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                      Generate
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsEditing(true)}
                className="h-8 w-8"
                title="Edit scene"
              >
                <Edit3 className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDelete?.(index)}
                className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                title="Delete scene"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 mb-3">
            <div className="text-sm">
              <span className="text-muted-foreground font-medium">Location:</span> {scene.location}
            </div>
            <div className="text-sm">
              <span className="text-muted-foreground font-medium">Emotion:</span> {scene.emotion}
            </div>
          </div>

          <div className="bg-muted/50 rounded p-2 mb-3">
            <p className="text-sm italic text-foreground leading-relaxed italic">
              "{scene.narration}"
            </p>
          </div>

          <div className="mb-4 pt-2 border-t border-border/30">
             <SceneBackgroundManager
                scene={scene}
                projectId={projectId}
                onUpdate={() => onUpdate?.(index, scene)} 
                projectType={projectType}
             />
          </div>

          {isGenerating ? (
            <div className="mt-4 space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="flex items-center gap-2">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Generating narration...
                </span>
                <span>{progress}%</span>
              </div>
              <div className="flex items-center gap-2">
                <Progress value={progress} className="h-1.5 flex-1" />
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-[10px]"
                  onClick={() => cancelNarration.mutate(index)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-3">
              {scene.narration_path && (
                <div className="flex items-center gap-2 bg-secondary/30 rounded-full px-3 py-1 border border-secondary">
                  <Play className="w-3 h-3 text-primary fill-primary" />
                  <span className="text-xs font-medium truncate max-w-[150px]">
                    {scene.narration_path.split('/').pop()}
                  </span>
                  <audio
                    src={`/api/projects/${projectId}/narration/${scene.narration_path.split('/').pop()}`}
                    controls
                    className="hidden"
                    id={`audio-scene-${index}`}
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-5 w-5 rounded-full"
                    onClick={() => {
                      const audio = document.getElementById(`audio-scene-${index}`) as HTMLAudioElement;
                      if (audio) audio.play();
                    }}
                  >
                    <Play className="w-2.5 h-2.5" />
                  </Button>
                </div>
              )}

              {scene.narration_paths && scene.narration_paths.length > 1 && (
                <Select
                  value={scene.narration_path}
                  onValueChange={(val) => selectNarration.mutate({ sceneIndex: index, narrationPath: val })}
                >
                  <SelectTrigger className="h-8 w-auto min-w-[120px] text-xs py-0 px-2 rounded-full">
                    <SelectValue placeholder="Variations" />
                  </SelectTrigger>
                  <SelectContent>
                    {scene.narration_paths.map((path) => (
                      <SelectItem key={path} value={path} className="text-xs">
                        {path.split('_').pop()?.split('.')[0] || path}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
