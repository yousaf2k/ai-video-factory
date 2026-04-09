import React, { useState, useEffect } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { MediaType } from '@/store/useEditorStore';
import { api } from '@/services/api';
import { Shot } from '@/types';

interface AssetData {
  id: string;
  name: string;
  type: MediaType;
  url: string;
  duration: number;
}

function DraggableAsset({ asset }: { asset: AssetData }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `asset-${asset.id}`,
    data: asset
  });

  const style = transform ? {
    transform: CSS.Translate.toString(transform),
  } : undefined;

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      className={`p-3 bg-slate-800 rounded border cursor-grab active:cursor-grabbing text-sm select-none transition-all ${
        isDragging
          ? 'opacity-30 border-slate-600'
          : 'border-slate-700 hover:border-slate-600'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2 flex-1 min-w-0">
          {/* Simple icon */}
          {asset.type === 'video' && (
            <svg className="w-3 h-3 text-indigo-400 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
              <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14v-4zM5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          )}
          {asset.type === 'audio' && (
            <svg className="w-3 h-3 text-emerald-400 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
              <path d="M9 18V5l12-2v13M9 18a3 3 0 11-6 0 3 3 0 016 0zm12-2a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          )}
          {asset.type === 'image' && (
            <svg className="w-3 h-3 text-purple-400 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
              <path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          )}

          <span className="truncate text-slate-200">{asset.name}</span>
        </div>

        <div className="text-[10px] text-slate-500 flex-shrink-0">
          {asset.duration.toFixed(1)}s
        </div>
      </div>
    </div>
  );
}

export function AssetBrowser({ projectId }: { projectId?: string }) {
  const [activeTab, setActiveTab] = useState<'project' | 'upload' | 'stock'>('project');
  const [assets, setAssets] = useState<AssetData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const fetchAssets = async () => {
    if (!projectId) return;
    setIsLoading(true);
    try {
      const project = await api.getProject(projectId);
      const newAssets: AssetData[] = [];

      if (project.shots) {
        project.shots.forEach((shot: Shot) => {
          if (shot.video_path) {
            newAssets.push({
              id: `v-${shot.index}`,
              name: shot.character_name ? `${shot.character_name}_${shot.index}.mp4` : `Shot_${shot.index}.mp4`,
              type: 'video',
              url: api.getAssetUrl(projectId, 'videos', shot.video_path.split(/[\\/]/).pop() || ''),
              duration: 5
            });
          }
          if (shot.is_flfi2v) {
            if (shot.meeting_video_path) {
              newAssets.push({
                 id: `v-meet-${shot.index}`,
                 name: `Meeting_${shot.character_name}.mp4`,
                 type: 'video',
                 url: api.getAssetUrl(projectId, 'videos', shot.meeting_video_path.split(/[\\/]/).pop() || ''),
                 duration: 5
              });
            }
            if (shot.departure_video_path) {
              newAssets.push({
                 id: `v-dep-${shot.index}`,
                 name: `Departure_${shot.character_name}.mp4`,
                 type: 'video',
                 url: api.getAssetUrl(projectId, 'videos', shot.departure_video_path.split(/[\\/]/).pop() || ''),
                 duration: 5
              });
            }
          }
        });
      }

      // Add narration from scenes
      if (project.story && project.story.scenes) {
        project.story.scenes.forEach((scene, index) => {
          if (scene.narration_path) {
            newAssets.push({
              id: `a-scene-${index}`,
              name: `Narration_Scene_${index + 1}${scene.narration_path.endsWith('.wav') ? '.wav' : '.mp3'}`,
              type: 'audio',
              url: `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/projects/${projectId}/narration/${scene.narration_path.split(/[\\/]/).pop()}`,
              duration: scene.scene_duration || 5
            });
          }
        });
      }

      setAssets(newAssets);
    } catch (error) {
      console.error("Failed to fetch assets:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAssets();
  }, [projectId]);

  const handleFileUpload = async (files: FileList, assetType: 'video' | 'audio' | 'image') => {
    if (!projectId) {
      alert('No project ID available');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        formData.append('file', file);
        formData.append('asset_type', assetType);

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/editor/upload/${projectId}`,
          {
            method: 'POST',
            body: formData
          }
        );

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Upload failed');
        }

        const result = await response.json();
        console.log('Upload successful:', result);

        setUploadProgress(((i + 1) / files.length) * 100);
      }

      // Refresh assets list
      await fetchAssets();

      // Switch back to project tab to see uploaded assets
      setActiveTab('project');

      alert('Assets uploaded successfully!');
    } catch (error) {
      console.error('Upload error:', error);
      alert(`Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 border-slate-800">
      <div className="p-4 border-b border-slate-800 font-semibold text-sm flex items-center justify-between">
        <span>Assets</span>
        {isLoading && <div className="w-3 h-3 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>}
      </div>
      
      <div className="flex border-b border-slate-800 bg-slate-900/50">
        <button
          className={`flex-1 py-3 text-[11px] uppercase tracking-wider font-bold transition-colors ${activeTab === 'project' ? 'text-indigo-400 border-b-2 border-indigo-500 bg-indigo-500/5' : 'text-slate-500 hover:text-slate-300'}`}
          onClick={() => setActiveTab('project')}
        >
          Project Media
        </button>
        <button
          className={`flex-1 py-3 text-[11px] uppercase tracking-wider font-bold transition-colors ${activeTab === 'upload' ? 'text-indigo-400 border-b-2 border-indigo-500 bg-indigo-500/5' : 'text-slate-500 hover:text-slate-300'}`}
          onClick={() => setActiveTab('upload')}
        >
          Upload Assets
        </button>
        <button
          className={`flex-1 py-3 text-[11px] uppercase tracking-wider font-bold transition-colors ${activeTab === 'stock' ? 'text-indigo-400 border-b-2 border-indigo-500 bg-indigo-500/5' : 'text-slate-500 hover:text-slate-300'}`}
          onClick={() => setActiveTab('stock')}
        >
          Stock Sfx
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2 custom-scrollbar">
        {activeTab === 'project' ? (
          assets.length > 0 ? (
            assets.map(asset => (
              <DraggableAsset key={asset.id} asset={asset} />
            ))
          ) : (
             <div className="flex flex-col items-center justify-center h-40 text-slate-500 text-xs italic p-4 text-center">
                {isLoading ? 'Loading assets...' : 'No media found in this project. Generate some images or videos first!'}
             </div>
          )
        ) : activeTab === 'upload' ? (
          <div className="space-y-4">
            {isUploading && (
              <div className="mb-4">
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>Uploading...</span>
                  <span>{uploadProgress.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2">
                  <div
                    className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
              </div>
            )}

            <div className="space-y-3">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Videos</div>
              <label className="block w-full p-4 border-2 border-dashed border-slate-700 rounded-lg hover:border-indigo-500 hover:bg-indigo-500/5 transition cursor-pointer">
                <input
                  type="file"
                  className="hidden"
                  accept="video/*"
                  multiple
                  onChange={(e) => e.target.files && handleFileUpload(e.target.files, 'video')}
                />
                <div className="text-center">
                  <svg className="w-8 h-8 mx-auto mb-2 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14v-4z" />
                  </svg>
                  <div className="text-sm text-slate-400">Drop videos or click to upload</div>
                  <div className="text-xs text-slate-600 mt-1">MP4, MOV, AVI, WebM</div>
                </div>
              </label>

              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mt-4">Audio</div>
              <label className="block w-full p-4 border-2 border-dashed border-slate-700 rounded-lg hover:border-emerald-500 hover:bg-emerald-500/5 transition cursor-pointer">
                <input
                  type="file"
                  className="hidden"
                  accept="audio/*"
                  multiple
                  onChange={(e) => e.target.files && handleFileUpload(e.target.files, 'audio')}
                />
                <div className="text-center">
                  <svg className="w-8 h-8 mx-auto mb-2 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-2v13M9 19a3 3 0 11-6 0 3 3 0 016 0zm12-2a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <div className="text-sm text-slate-400">Drop audio or click to upload</div>
                  <div className="text-xs text-slate-600 mt-1">MP3, WAV, AAC, OGG</div>
                </div>
              </label>

              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mt-4">Images</div>
              <label className="block w-full p-4 border-2 border-dashed border-slate-700 rounded-lg hover:border-purple-500 hover:bg-purple-500/5 transition cursor-pointer">
                <input
                  type="file"
                  className="hidden"
                  accept="image/*"
                  multiple
                  onChange={(e) => e.target.files && handleFileUpload(e.target.files, 'image')}
                />
                <div className="text-center">
                  <svg className="w-8 h-8 mx-auto mb-2 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <div className="text-sm text-slate-400">Drop images or click to upload</div>
                  <div className="text-xs text-slate-600 mt-1">PNG, JPG, WebP, GIF</div>
                </div>
              </label>
            </div>
          </div>
        ) : (
          <div className="text-slate-500 text-xs italic p-4 text-center">
            Stock library coming soon...
          </div>
        )}
      </div>

    </div>
  );
}

