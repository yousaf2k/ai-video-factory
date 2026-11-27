'use client';

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Prop, AssetEntry } from '@/types';
import { Sparkles, RefreshCw, Save, FolderOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ImageLightbox } from '@/components/ui/ImageLightbox';
import { GenerationDialog } from '../shots/GenerationDialog';
import AssetPickerDialog from '../assets/AssetPickerDialog';
import { api } from '@/services/api';
import { toast } from 'sonner';

interface PropReferenceUploadProps {
  prop: Prop;
  propIndex: number;
  projectId: string;
  onUpdate?: () => void;
  onPromptChange?: (promptKey: string, newPrompt: string) => void;
  onSavePrompt?: (promptKey: string, newPrompt: string) => Promise<void>;
  onBeforeUpload?: () => Promise<void>;
}

export default function PropReferenceUpload({
  prop,
  propIndex,
  projectId,
  onUpdate,
  onPromptChange,
  onSavePrompt,
  onBeforeUpload
}: PropReferenceUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [savingPrompt, setSavingPrompt] = useState(false);
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);

  // Baseline prompt as of last persist — lets us show a Save button only
  // when the textarea actually differs from what's in story.json.
  const promptBaseline = useRef<string>('');
  const [promptDirty, setPromptDirty] = useState(false);
  useEffect(() => {
    if (promptBaseline.current === '') {
      promptBaseline.current = prop.image_prompt || '';
    }
  }, [prop]);

  const handleSavePrompt = async () => {
    if (!onSavePrompt) return;
    setSavingPrompt(true);
    try {
      await onSavePrompt('image_prompt', prop.image_prompt || '');
      promptBaseline.current = prop.image_prompt || '';
      setPromptDirty(false);
      toast.success('Prompt saved');
    } catch (error) {
      console.error('Failed to save prop prompt:', error);
      toast.error(`Failed to save prompt: ${error}`);
    } finally {
      setSavingPrompt(false);
    }
  };

  // Use local state for optimistic updates during upload, but sync with props
  const [preview, setPreview] = useState<string | null>(prop.reference_image_path || null);

  useEffect(() => {
    setPreview(prop.reference_image_path || null);
  }, [prop]);

  const [showGenerationDialog, setShowGenerationDialog] = useState(false);
  const [showAssetPicker, setShowAssetPicker] = useState(false);
  const [attachingAsset, setAttachingAsset] = useState(false);

  const handleAssetPick = async (entry: AssetEntry) => {
    if (onBeforeUpload) {
      try {
        await onBeforeUpload();
      } catch (err) {
        console.error("Error in onBeforeUpload before attaching asset:", err);
        return;
      }
    }
    setAttachingAsset(true);
    try {
      const result = await api.useAssetForPropReference(projectId, propIndex, entry.ref);
      setPreview(result.image_path);
      if (onUpdate) onUpdate();
      toast.success(`Attached "${entry.title}" as prop reference`);
    } catch (error) {
      console.error("Failed to attach library asset:", error);
      toast.error(`Failed to attach library asset: ${error}`);
    } finally {
      setAttachingAsset(false);
    }
  };

  const getMediaUrl = (path: string) => {
    if (!path) return '';
    if (path.startsWith('http')) return path;
    const filename = path.split('/').pop();
    if (path.includes('/references/')) {
      return `/api/projects/${projectId}/references/${filename}`;
    }
    return `/api/projects/${projectId}/images/${filename}`;
  };

  const handleUpload = useCallback(async (file: File) => {
    if (onBeforeUpload) {
      try {
        await onBeforeUpload();
      } catch (err) {
        console.error("Error in onBeforeUpload before uploading:", err);
        return;
      }
    }

    setUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(
        `/api/projects/${projectId}/story/props/${propIndex}/upload-reference`,
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

      // Update preview
      setPreview(result.image_path);

      // Trigger parent update
      if (onUpdate) {
        onUpdate();
      }

      console.log(`Prop reference uploaded:`, result.image_path);
    } catch (error) {
      console.error(`Error uploading prop reference:`, error);
      toast.error(`Failed to upload prop reference: ${error}`);
    } finally {
      setUploading(false);
    }
  }, [projectId, propIndex, onUpdate]);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      handleUpload(file);
    }
  }, [handleUpload]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleUpload(file);
    }
  }, [handleUpload]);

  const handleGenerate = async (options: any) => {
    if (onBeforeUpload) {
      try {
        await onBeforeUpload();
      } catch (err) {
        console.error("Error in onBeforeUpload before generating:", err);
        return;
      }
    }
    try {
      await api.generatePropReferenceImage(projectId, propIndex, {
        prompt_override: options.promptOverride,
        image_mode: options.mode,
        image_workflow: options.workflow,
        seed: options.seed ? Number(options.seed) : undefined,
        gemini_mode: options.gemini_mode,
        gemini_model: options.gemini_model,
        gemini_thinking: options.gemini_thinking,
        background_style: options.backgroundStyle
      });
      setShowGenerationDialog(false);
      if (onUpdate) onUpdate();
    } catch (error) {
      console.error("Failed to generate prop image:", error);
      toast.error(`Failed to generate prop image: ${error}`);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
          Reference Sheet
        </h4>
        <span className="text-xs text-gray-500">
          Upload or generate a sheet for prop consistency
        </span>
      </div>

      <div className="space-y-2">
        <div className="flex justify-between items-start h-6 mb-2">
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
            Prop Reference
          </label>
          <div className="flex items-center gap-1 shrink-0">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 whitespace-nowrap"
              onClick={() => setShowAssetPicker(true)}
              disabled={attachingAsset}
              title="Pick an image from the Asset Library"
            >
              <><FolderOpen className="w-3 h-3 mr-1" /> {attachingAsset ? 'Attaching…' : 'From Assets'}</>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 whitespace-nowrap"
              onClick={() => setShowGenerationDialog(true)}
              title={preview ? 'Generate a new version of this reference sheet' : 'Generate reference sheet'}
            >
              {preview ? (
                <><RefreshCw className="w-3 h-3 mr-1" /> Regenerate</>
              ) : (
                <><Sparkles className="w-3 h-3 mr-1" /> Generate</>
              )}
            </Button>
          </div>
        </div>

        <div className="mb-2">
          <textarea
            className="w-full text-[10px] text-muted-foreground leading-tight p-2 border border-border rounded-md bg-transparent focus:bg-background focus:ring-1 focus:ring-primary focus:outline-none min-h-[48px] resize-y"
            value={prop.image_prompt || ""}
            onChange={(e) => {
              onPromptChange && onPromptChange('image_prompt', e.target.value);
              setPromptDirty(e.target.value !== (promptBaseline.current ?? ''));
            }}
            placeholder="Enter prompt for this prop reference sheet..."
            disabled={!onPromptChange}
          />
          <div className="flex justify-end mt-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs text-muted-foreground hover:text-primary disabled:opacity-40 disabled:pointer-events-none"
              disabled={!onSavePrompt || !promptDirty || savingPrompt}
              onClick={handleSavePrompt}
              title="Persist this prompt to the project story"
            >
              <Save className="w-3 h-3 mr-1" /> {savingPrompt ? 'Saving…' : 'Save prompt'}
            </Button>
          </div>
        </div>

        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => document.getElementById(`prop-input-${propIndex}`)?.click()}
          className={`
            relative border-2 border-dashed rounded-lg p-4 text-center
            transition-colors duration-200 cursor-pointer
            ${uploading
              ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20'
              : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
            }
          `}
        >
          {preview ? (
            <div className="space-y-2">
              <img
                src={getMediaUrl(preview)}
                alt="prop reference"
                className="w-full h-32 object-cover rounded cursor-zoom-in"
                onClick={(e) => {
                  e.stopPropagation();
                  setLightboxSrc(getMediaUrl(preview!));
                }}
              />
              <div className="flex justify-center gap-3">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    document.getElementById(`prop-input-${propIndex}`)?.click();
                  }}
                  className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400"
                >
                  Replace Photo
                </button>
                <span className="text-xs text-border">|</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowGenerationDialog(true);
                  }}
                  className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 flex items-center gap-1"
                >
                  <RefreshCw className="w-3 h-3" /> Regenerate
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <svg
                className="mx-auto h-8 w-8 text-gray-400"
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
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Drag & drop or click to upload
              </p>
            </div>
          )}

          <input
            id={`prop-input-${propIndex}`}
            type="file"
            accept="image/*"
            onChange={handleFileSelect}
            className="hidden"
            disabled={uploading}
          />
        </div>
      </div>

      {showGenerationDialog && (
        <GenerationDialog
          isOpen={showGenerationDialog}
          onClose={() => setShowGenerationDialog(false)}
          onSubmit={handleGenerate}
          projectId={projectId}
          type="image"
          defaultPromptOverride={prop.image_prompt || ""}
          withReferenceStyle
        />
      )}

      {showAssetPicker && (
        <AssetPickerDialog
          open={showAssetPicker}
          onClose={() => setShowAssetPicker(false)}
          onSelect={handleAssetPick}
          title={`Choose a reference for "${prop.name || 'Prop'}"`}
        />
      )}

      <ImageLightbox
        src={lightboxSrc}
        alt="Prop reference"
        onClose={() => setLightboxSrc(null)}
      />
    </div>
  );
}
