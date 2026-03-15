'use client';

import React, { useState } from 'react';
import { Scene } from '@/types';

interface SceneBackgroundManagerProps {
  scene: Scene;
  projectId: string;
  onUpdate?: () => void;
}

export default function SceneBackgroundManager({
  scene,
  projectId,
  onUpdate
}: SceneBackgroundManagerProps) {
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState(false);

  const getMediaUrl = (path: string) => {
    if (!path) return '';
    if (path.startsWith('http')) return path;
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

      // Trigger parent update
      if (onUpdate) {
        onUpdate();
      }

      console.log('Background uploaded:', result.image_path);
    } catch (error) {
      console.error('Error uploading background:', error);
      alert(`Failed to upload background: ${error}`);
    } finally {
      setUploading(false);
    }
  };

  const handleGenerate = async () => {
    if (!scene.set_prompt) {
      alert('Scene must have a set_prompt to generate background');
      return;
    }

    setGenerating(true);

    try {
      const response = await fetch(
        `/api/projects/${projectId}/story/scenes/${scene.scene_id}/generate-background`,
        {
          method: 'POST'
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
      alert(`Failed to generate background: ${error}`);
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

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleUpload(file);
    }
  };

  const hasBackground = !!scene.background_image_path;
  const isGenerated = scene.background_is_generated;

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
        className={`
          relative border-2 border-dashed rounded-lg p-4 text-center
          transition-colors duration-200
          ${uploading || generating
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
              className="w-full h-40 object-cover rounded"
            />
            <div className="flex gap-2 justify-center">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  document.getElementById(`bg-input-${scene.scene_id}`)?.click();
                }}
                className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400"
              >
                Replace Background
              </button>
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
      <div className="flex gap-2">
        <button
          onClick={(e) => {
            e.stopPropagation();
            document.getElementById(`bg-input-${scene.scene_id}`)?.click();
          }}
          disabled={uploading || generating}
          className="flex-1 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700"
        >
          {uploading ? 'Uploading...' : 'Upload'}
        </button>

        <button
          onClick={handleGenerate}
          disabled={generating || !scene.set_prompt}
          className="flex-1 px-3 py-2 text-sm font-medium text-white bg-purple-600 border border-transparent rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-purple-700 dark:hover:bg-purple-800"
        >
          {generating ? 'Generating...' : 'Generate AI'}
        </button>
      </div>

      {!scene.set_prompt && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          ⚠️ Add a set_prompt to enable AI generation
        </p>
      )}
    </div>
  );
}
