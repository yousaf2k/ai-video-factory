/**
 * Session editor page - Story and shot editing
 */
'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useSession } from '@/hooks/useSessions';
import { useUpdateStory } from '@/hooks/useStory';
import { SceneList } from '@/components/scenes/SceneList';
import { Scene, Story } from '@/types';
import { Save, RefreshCw } from 'lucide-react';

export default function SessionEditPage() {
  const params = useParams();
  const sessionId = params.id as string;
  const { data: session, isLoading, error } = useSession(sessionId);
  const updateStoryMutation = useUpdateStory(sessionId);

  // Local state for story editing
  const [story, setStory] = useState<Story | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  // Initialize story when session loads
  if (session && session.story && !story) {
    setStory(session.story);
  }

  const handleUpdateScene = (index: number, updatedScene: Scene) => {
    if (!story) return;

    const newScenes = [...story.scenes];
    newScenes[index] = updatedScene;

    setStory({
      ...story,
      scenes: newScenes,
    });
    setHasChanges(true);
  };

  const handleDeleteScene = (index: number) => {
    if (!story) return;
    if (!confirm('Are you sure you want to delete this scene?')) return;

    const newScenes = story.scenes.filter((_, i) => i !== index);

    setStory({
      ...story,
      scenes: newScenes,
    });
    setHasChanges(true);
  };

  const handleReorderScenes = (newScenes: Scene[]) => {
    if (!story) return;

    setStory({
      ...story,
      scenes: newScenes,
    });
    setHasChanges(true);
  };

  const handleAddScene = () => {
    if (!story) return;

    const newScene: Scene = {
      location: 'New Location',
      characters: 'Characters',
      action: 'Action happening',
      emotion: 'Emotional tone',
      narration: 'Narration text',
      scene_duration: 30,
    };

    setStory({
      ...story,
      scenes: [...story.scenes, newScene],
    });
    setHasChanges(true);
  };

  const handleSaveStory = async () => {
    if (!story) return;

    try {
      await updateStoryMutation.mutateAsync(story);
      setHasChanges(false);
      alert('Story updated successfully!');
    } catch (error) {
      console.error('Failed to update story:', error);
      alert('Failed to update story. Please try again.');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading session...</div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-500">Error loading session</div>
      </div>
    );
  }

  if (!story) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-12">
          <h2 className="text-xl font-semibold mb-4">No Story Found</h2>
          <p className="text-muted-foreground mb-6">
            This session doesn't have a story yet. Generate a story first.
          </p>
          <Link
            href={`/sessions/${sessionId}`}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            Back to Session
          </Link>
        </div>
      </div>
    );
  }

  // Calculate total duration
  const totalDuration = story.scenes.reduce((sum, scene) => sum + (scene.scene_duration || 0), 0);

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          href={`/sessions/${sessionId}`}
          className="text-primary hover:underline mb-4 inline-block"
        >
          ← Back to Session
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Edit Story</h1>
            <p className="text-muted-foreground">
              {story.title} • {story.style}
            </p>
          </div>
          <div className="flex gap-2">
            {hasChanges && (
              <button
                onClick={handleSaveStory}
                disabled={updateStoryMutation.isPending}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <Save className="w-4 h-4" />
                {updateStoryMutation.isPending ? 'Saving...' : 'Save Changes'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Story Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="border rounded-lg p-4">
          <div className="text-sm text-muted-foreground">Total Scenes</div>
          <div className="text-2xl font-bold">{story.scenes.length}</div>
        </div>
        <div className="border rounded-lg p-4">
          <div className="text-sm text-muted-foreground">Total Duration</div>
          <div className="text-2xl font-bold">{Math.floor(totalDuration / 60)}:{(totalDuration % 60).toString().padStart(2, '0')}</div>
        </div>
        <div className="border rounded-lg p-4">
          <div className="text-sm text-muted-foreground">Status</div>
          <div className="text-2xl font-bold">
            {hasChanges ? 'Unsaved' : 'Saved'}
          </div>
        </div>
      </div>

      {/* Scenes Editor */}
      <div className="border rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">Scenes</h2>
        <SceneList
          scenes={story.scenes}
          onUpdate={handleUpdateScene}
          onDelete={handleDeleteScene}
          onReorder={handleReorderScenes}
          onAdd={handleAddScene}
        />
      </div>

      {/* Instructions */}
      <div className="mt-8 p-4 bg-muted rounded-lg">
        <h3 className="font-semibold mb-2">Tips for editing scenes:</h3>
        <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
          <li>Drag scenes to reorder them in the story</li>
          <li>Click the edit icon to modify scene details</li>
          <li>Adjust scene durations to control pacing</li>
          <li>Click "Save Changes" to persist your edits</li>
        </ul>
      </div>
    </div>
  );
}
