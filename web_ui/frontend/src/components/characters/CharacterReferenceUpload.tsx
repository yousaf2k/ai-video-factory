'use client';

import React, { useState, useCallback } from 'react';
import { Character } from '@/types';

interface CharacterReferenceUploadProps {
  character: Character;
  characterIndex: number;
  sessionId: string;
  onUpdate?: () => void;
}

export default function CharacterReferenceUpload({
  character,
  characterIndex,
  sessionId,
  onUpdate
}: CharacterReferenceUploadProps) {
  const [uploading, setUploading] = useState<{ then: boolean; now: boolean }>({
    then: false,
    now: false
  });
  const [previews, setPreviews] = useState<{
    then: string | null;
    now: string | null;
  }>({
    then: character.then_reference_image_path || null,
    now: character.now_reference_image_path || null
  });

  const getMediaUrl = (path: string) => {
    if (!path) return '';
    if (path.startsWith('http')) return path;
    return `/api/sessions/${sessionId}/media/${path.replace(/^output\//, '')}`;
  };

  const handleUpload = useCallback(async (
    variant: 'then' | 'now',
    file: File
  ) => {
    setUploading(prev => ({ ...prev, [variant]: true }));

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(
        `/api/sessions/${sessionId}/story/characters/${characterIndex}/upload-reference?variant=${variant}`,
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
  }, [sessionId, characterIndex, onUpdate]);

  const handleDrop = useCallback((
    e: React.DragEvent<HTMLDivElement>,
    variant: 'then' | 'now'
  ) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      handleUpload(variant, file);
    }
  }, [handleUpload]);

  const handleFileSelect = useCallback((
    e: React.ChangeEvent<HTMLInputElement>,
    variant: 'then' | 'now'
  ) => {
    const file = e.target.files?.[0];
    if (file) {
      handleUpload(variant, file);
    }
  }, [handleUpload]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
          Reference Photos
        </h4>
        <span className="text-xs text-gray-500">
          Upload photos for facial consistency
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* THEN Reference */}
        <div className="space-y-2">
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
            THEN (Young Version)
          </label>
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => handleDrop(e, 'then')}
            className={`
              relative border-2 border-dashed rounded-lg p-4 text-center
              transition-colors duration-200
              ${uploading.then
                ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20'
                : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
              }
            `}
          >
            {previews.then ? (
              <div className="space-y-2">
                <img
                  src={getMediaUrl(previews.then)}
                  alt="THEN reference"
                  className="w-full h-32 object-cover rounded"
                />
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    document.getElementById(`then-input-${characterIndex}`)?.click();
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
              id={`then-input-${characterIndex}`}
              type="file"
              accept="image/*"
              onChange={(e) => handleFileSelect(e, 'then')}
              className="hidden"
              disabled={uploading.then}
            />
          </div>
        </div>

        {/* NOW Reference */}
        <div className="space-y-2">
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
            NOW (Current Version)
          </label>
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => handleDrop(e, 'now')}
            className={`
              relative border-2 border-dashed rounded-lg p-4 text-center
              transition-colors duration-200
              ${uploading.now
                ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20'
                : 'border-gray-300 dark:border-gray-600 hover:border-gray-400'
              }
            `}
          >
            {previews.now ? (
              <div className="space-y-2">
                <img
                  src={getMediaUrl(previews.now)}
                  alt="NOW reference"
                  className="w-full h-32 object-cover rounded"
                />
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    document.getElementById(`now-input-${characterIndex}`)?.click();
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
              id={`now-input-${characterIndex}`}
              type="file"
              accept="image/*"
              onChange={(e) => handleFileSelect(e, 'now')}
              className="hidden"
              disabled={uploading.now}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
