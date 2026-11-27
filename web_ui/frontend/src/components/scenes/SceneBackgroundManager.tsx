'use client';

import React, { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Scene, AssetEntry } from '@/types';
import { GenerationDialog, GenerationConfig } from '../shots/GenerationDialog';
import AssetPickerDialog from '../assets/AssetPickerDialog';
import { useProject } from '@/hooks/useProjects';
import { api } from '@/services/api';
import { toast } from 'sonner';
import { ImageLightbox } from '@/components/ui/ImageLightbox';

interface SceneBackgroundManagerProps {
  scene: Scene;
  projectId: string;
  onUpdate?: () => void;
  projectType?: number;
}

export default function SceneBackgroundManager({
  scene,
  projectId,
  onUpdate,
  projectType
}: SceneBackgroundManagerProps) {
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [showGenModal, setShowGenModal] = useState(false);
  const [showAssetPicker, setShowAssetPicker] = useState(false);
  const [attachingAsset, setAttachingAsset] = useState(false);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const { data: project } = useProject(projectId);
  // Backgrounds can be generated from the scene's set_prompt, falling back
  // to the location (backend background_base_text handles the fallback for
  // every project type). The style is chosen in the generation dialog.
  const isR2V = project?.video_generation_type === "r2v";
  const canGenerate = !!scene.set_prompt || !!scene.location;

  const getMediaUrl = (path: string) => {
    if (!path) return '';
    if (path.startsWith('http')) return path;
    const filename = path.split('/').pop();
    if (path.includes('/backgrounds/')) {
      return `/api/projects/${projectId}/backgrounds/${filename}`;
    }
    return `/api/projects/${projectId}/media/${path.replace(/^output\//, '')}`;
  };

  const handleUpload = async (file: File) => {
    setUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(
        `/api/projects/${projectId}/story/scenes/${scene.scene_id}/upload-background`,
        {
          method: 'POST',
          body: formData
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }

      const result = await response.json();

      // Invalidate project query to pull full details with its background path
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });

      console.log('Background uploaded:', result.image_path);
    } catch (error) {
      console.error('Error uploading background:', error);
      toast.error(`Failed to upload background: ${error}`);
    } finally {
      setUploading(false);
    }
  };

  const handleGenerateSubmit = async (config: GenerationConfig) => {
    setShowGenModal(false);

    if (!canGenerate) {
      toast.warning(
        isR2V
          ? 'Scene must have a set_prompt or a location to generate background'
          : 'Scene must have a set_prompt to generate background'
      );
      return;
    }

    setGenerating(true);

    try {
      const requestBody = {
        prompt: config.promptOverride,
        seed: config.seed === "" ? undefined : config.seed,
        workflow: config.workflow === "default" ? undefined : config.workflow,
        image_model: config.mode,
        background_style: config.backgroundStyle,
      };

      const response = await fetch(
        `/api/projects/${projectId}/story/scenes/${scene.scene_id}/generate-background`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Generation failed');
      }

      const result = await response.json();
      console.log('Background generation started:', result);

      // Note: The actual generation happens asynchronously
      // The story will be updated via WebSocket when complete
    } catch (error) {
      console.error('Error generating background:', error);
      toast.error(`Failed to generate background: ${error}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      handleUpload(file);
    }
  };

  const handleAssetPick = async (entry: AssetEntry) => {
    setAttachingAsset(true);
    try {
      const result = await api.useAssetForSceneBackground(projectId, scene.scene_id!, entry.ref);
      // Invalidate project query to pull full details with its background path
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      toast.success(`Attached "${entry.title}" as scene background`);
      console.log('Background attached from asset library:', result.image_path);
    } catch (error) {
      console.error('Error attaching background from asset library:', error);
      toast.error(`Failed to attach background: ${error}`);
    } finally {
      setAttachingAsset(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleUpload(file);
    }
  };

  const hasBackground = !!scene.background_image_path;
  const isGenerated = scene.background_is_generated;
  // Backgrounds are consumed by ThenVsNow (IPAdapter), r2v (reference sheets
  // attached to shots) and i2v/t2v story projects (sync_character_asset_refs
  // attaches each scene's background to that scene's shots). Only ASMR, which
  // manages shots directly without scene images, hides the section.
  const backgroundEnabled =
    projectType === 1 || projectType === 2 || projectType === 3 || isR2V;

  if (!backgroundEnabled && !hasBackground) {
    return null; // Hide empty container where backgrounds aren't used
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
          Scene Background
        </h4>
        {hasBackground && (
          <span className={`text-xs px-2 py-1 rounded ${
            isGenerated
              ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'
              : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
          }`}>
            {isGenerated ? 'AI Generated' : 'Uploaded'}
          </span>
        )}
      </div>

      {/* Background Preview */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => document.getElementById(`bg-input-${scene.scene_id}`)?.click()}
        className={`
          relative border-2 border-dashed rounded-lg p-4 text-center
          transition-colors duration-200 cursor-pointer
          ${uploading || generating || attachingAsset
            ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
          }
        `}
      >
        {hasBackground ? (
          <div className="space-y-2">
            <img
              src={getMediaUrl(scene.background_image_path!)}
              alt="Scene background"
              className="w-full h-40 object-cover rounded cursor-zoom-in"
              onClick={(e) => {
                e.stopPropagation();
                setLightboxSrc(getMediaUrl(scene.background_image_path!));
              }}
            />
            <div className="flex gap-2 justify-center">
              {backgroundEnabled && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    document.getElementById(`bg-input-${scene.scene_id}`)?.click();
                  }}
                  className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400"
                >
                  Replace Background
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              stroke="currentColor"
              fill="none"
              viewBox="0 0 48 48"
            >
              <path
                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Upload or generate background
              </p>
            </div>
          </div>
        )}

        <input
          id={`bg-input-${scene.scene_id}`}
          type="file"
          accept="image/*"
          onChange={handleFileSelect}
          className="hidden"
          disabled={uploading || generating}
        />
      </div>

      {/* Action Buttons */}
      {backgroundEnabled && (
        <div className="flex gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              document.getElementById(`bg-input-${scene.scene_id}`)?.click();
            }}
            disabled={uploading || generating || attachingAsset}
            className="flex-1 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700"
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowAssetPicker(true);
            }}
            disabled={uploading || generating || attachingAsset}
            className="flex-1 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700"
          >
            {attachingAsset ? 'Attaching...' : 'From Assets'}
          </button>

          <button
            onClick={() => setShowGenModal(true)}
            disabled={generating || !canGenerate}
            className="flex-1 px-3 py-2 text-sm font-medium text-white bg-purple-600 border border-transparent rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-purple-700 dark:hover:bg-purple-800"
          >
            {generating ? 'Generating...' : 'Generate AI'}
          </button>
        </div>
      )}

      {!canGenerate && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          {isR2V
            ? '⚠️ Add a set_prompt or a scene location to enable AI generation'
            : '⚠️ Add a set_prompt to enable AI generation'}
        </p>
      )}

      <GenerationDialog
        isOpen={showGenModal}
        onClose={() => setShowGenModal(false)}
        type="image"
        projectId={projectId}
        isPending={generating}
        defaultPromptOverride={scene.set_prompt || undefined}
        onSubmit={handleGenerateSubmit}
        title="Generate Scene Background"
        withReferenceStyle
        styleStorageKey={`background_style_${projectId}`}
        styleLabel="Background Style"
      />

      {showAssetPicker && (
        <AssetPickerDialog
          open={showAssetPicker}
          onClose={() => setShowAssetPicker(false)}
          onSelect={handleAssetPick}
          title={`Choose a background for "${scene.location || 'Scene'}"`}
        />
      )}

      <ImageLightbox
        src={lightboxSrc}
        alt="Scene background"
        onClose={() => setLightboxSrc(null)}
      />
    </div>
  );
}
