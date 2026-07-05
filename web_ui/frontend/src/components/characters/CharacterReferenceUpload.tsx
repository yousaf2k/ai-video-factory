'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { Character } from '@/types';
import { Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { GenerationDialog } from '../shots/GenerationDialog';
import { api } from '@/services/api';

interface CharacterReferenceUploadProps {
  character: Character;
  characterIndex: number;
  projectId: string;
  onUpdate?: () => void;
  onPromptChange?: (promptKey: string, newPrompt: string) => void;
  onBeforeUpload?: () => Promise<void>;
}

export default function CharacterReferenceUpload({
  character,
  characterIndex,
  projectId,
  onUpdate,
  onPromptChange,
  onBeforeUpload
}: CharacterReferenceUploadProps) {
  const [uploading, setUploading] = useState<Record<string, boolean>>({});
  
  // Use local state for optimistic updates during upload, but sync with props
  const [previews, setPreviews] = useState<Record<string, string | null>>({
    then: character.then_reference_image_path || null,
    now: character.now_reference_image_path || null,
    character: character.character_reference_image_path || null
  });

  useEffect(() => {
    setPreviews({
      then: character.then_reference_image_path || null,
      now: character.now_reference_image_path || null,
      character: character.character_reference_image_path || null
    });
  }, [character]);

  const [showGenerationDialog, setShowGenerationDialog] = useState(false);
  const [selectedVariant, setSelectedVariant] = useState<string | null>(null);

  const getMediaUrl = (path: string) => {
    if (!path) return '';
    if (path.startsWith('http')) return path;
    const filename = path.split('/').pop();
    if (path.includes('/references/')) {
      return `/api/projects/${projectId}/references/${filename}`;
    }
    return `/api/projects/${projectId}/images/${filename}`;
  };

  const handleUpload = useCallback(async (
    variant: string,
    file: File
  ) => {
    if (onBeforeUpload) {
      try {
        await onBeforeUpload();
      } catch (err) {
        console.error("Error in onBeforeUpload before uploading:", err);
        return;
      }
    }

    setUploading(prev => ({ ...prev, [variant]: true }));

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(
        `/api/projects/${projectId}/story/characters/${characterIndex}/upload-reference?variant=${variant}`,
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
      setPreviews(prev => ({
        ...prev,
        [variant]: result.image_path
      }));

      // Trigger parent update
      if (onUpdate) {
        onUpdate();
      }

      console.log(`${variant.toUpperCase()} reference uploaded:`, result.image_path);
    } catch (error) {
      console.error(`Error uploading ${variant} reference:`, error);
      alert(`Failed to upload ${variant.toUpperCase()} reference: ${error}`);
    } finally {
      setUploading(prev => ({ ...prev, [variant]: false }));
    }
  }, [projectId, characterIndex, onUpdate]);

  const handleDrop = useCallback((
    e: React.DragEvent<HTMLDivElement>,
    variant: string
  ) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      handleUpload(variant, file);
    }
  }, [handleUpload]);

  const handleFileSelect = useCallback((
    e: React.ChangeEvent<HTMLInputElement>,
    variant: string
  ) => {
    const file = e.target.files?.[0];
    if (file) {
      handleUpload(variant, file);
    }
  }, [handleUpload]);

  const handleGenerate = async (options: any) => {
    if (!selectedVariant) return;
    if (onBeforeUpload) {
      try {
        await onBeforeUpload();
      } catch (err) {
        console.error("Error in onBeforeUpload before generating:", err);
        return;
      }
    }
    try {
      await api.generateCharacterReferenceImage(projectId, characterIndex, {
        variant: selectedVariant,
        prompt_override: options.promptOverride,
        image_mode: options.mode,
        image_workflow: options.workflow,
        seed: options.seed ? Number(options.seed) : undefined,
        gemini_mode: options.gemini_mode
      });
      setShowGenerationDialog(false);
      setSelectedVariant(null);
      if (onUpdate) onUpdate();
    } catch (error) {
      console.error("Failed to generate character image:", error);
      alert(`Failed to generate character image: ${error}`);
    }
  };

  const isThenVsNow = !!character.then_prompt || !!character.now_prompt;
  const variants = isThenVsNow 
    ? [
        { key: 'then', label: 'THEN (Young Version)', prompt: character.then_prompt, promptKey: 'then_prompt', ref: previews.then },
        { key: 'now', label: 'NOW (Current Version)', prompt: character.now_prompt, promptKey: 'now_prompt', ref: previews.now }
      ]
    : [
        { 
          key: 'character', 
          label: 'Character Reference', 
          prompt: character.image_prompt || "", 
          promptKey: 'image_prompt', 
          ref: previews.character
        }
      ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
          Reference Photos
        </h4>
        <span className="text-xs text-gray-500">
          Upload or generate photos for character consistency
        </span>
      </div>

      {/* Age Display */}
      {(character.then_age || character.now_age) && (
        <div className="flex gap-2">
          {character.then_age && (
            <div className="text-xs font-medium px-2 py-1 rounded bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800">
              Then: {character.then_age} years
            </div>
          )}
          {character.now_age && (
            <div className="text-xs font-medium px-2 py-1 rounded bg-green-50 text-green-700 border border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800">
              Now: {character.now_age} years
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        {variants.map(v => (
          <div key={v.key} className="space-y-2">
            <div className="flex justify-between items-start h-6 mb-2">
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 truncate pr-2" title={v.label}>
                {v.label}
              </label>
              {v.prompt && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="h-6 px-2 text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 whitespace-nowrap shrink-0"
                  onClick={() => { setSelectedVariant(v.key); setShowGenerationDialog(true); }}
                >
                  <Sparkles className="w-3 h-3 mr-1" /> Generate
                </Button>
              )}
            </div>
            
            {v.prompt !== undefined && (
              <div className="mb-2">
                <textarea
                  className="w-full text-[10px] text-muted-foreground leading-tight p-2 border border-border rounded-md bg-transparent focus:bg-background focus:ring-1 focus:ring-primary focus:outline-none min-h-[48px] resize-y"
                  value={v.prompt}
                  onChange={(e) => onPromptChange && onPromptChange(v.promptKey, e.target.value)}
                  placeholder="Enter prompt for this character reference..."
                  disabled={!onPromptChange}
                />
              </div>
            )}

            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => handleDrop(e, v.key)}
              onClick={() => document.getElementById(`${v.key}-input-${characterIndex}`)?.click()}
              className={`
                relative border-2 border-dashed rounded-lg p-4 text-center
                transition-colors duration-200 cursor-pointer
                ${uploading[v.key]
                  ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
                }
              `}
            >
              {v.ref ? (
                <div className="space-y-2">
                  <img
                    src={getMediaUrl(v.ref)}
                    alt={`${v.key} reference`}
                    className="w-full h-32 object-cover rounded"
                  />
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      document.getElementById(`${v.key}-input-${characterIndex}`)?.click();
                    }}
                    className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400"
                  >
                    Replace Photo
                  </button>
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
                id={`${v.key}-input-${characterIndex}`}
                type="file"
                accept="image/*"
                onChange={(e) => handleFileSelect(e, v.key)}
                className="hidden"
                disabled={uploading[v.key]}
              />
            </div>
          </div>
        ))}
      </div>

      {showGenerationDialog && selectedVariant && (
        <GenerationDialog
          isOpen={showGenerationDialog}
          onClose={() => { setShowGenerationDialog(false); setSelectedVariant(null); }}
          onSubmit={handleGenerate}
          projectId={projectId}
          type="image"
          defaultPromptOverride={variants.find(v => v.key === selectedVariant)?.prompt || ""}
        />
      )}
    </div>
  );
}
