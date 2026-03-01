/**
 * Sessions list page
 */
'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useSessions, useCreateSession, useDeleteSession, useDuplicateSession } from '@/hooks/useSessions';
import { useAgents } from '@/hooks/useAgents';
import { api } from '@/services/api';
import type { CreateSessionRequest } from '@/types';
import { formatDistanceToNow } from 'date-fns';

export default function SessionsPage() {
  const { data: sessions, isLoading, error } = useSessions();
  const { data: agents } = useAgents();
  const createSessionMutation = useCreateSession();
  const deleteSessionMutation = useDeleteSession();
  const duplicateSessionMutation = useDuplicateSession();

  const [showNewDialog, setShowNewDialog] = useState(false);
  const [newIdea, setNewIdea] = useState('');
  
  // Agent selection state
  const [selectedStoryAgent, setSelectedStoryAgent] = useState('default');
  const [selectedImageAgent, setSelectedImageAgent] = useState('default');
  const [selectedVideoAgent, setSelectedVideoAgent] = useState('default');

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newIdea.trim()) return;

    const request: CreateSessionRequest = {
      idea: newIdea,
      story_agent: selectedStoryAgent,
      image_agent: selectedImageAgent,
      video_agent: selectedVideoAgent,
    };

    try {
      const session = await createSessionMutation.mutateAsync(request);
      setShowNewDialog(false);
      setNewIdea('');
      // Navigate to the new session
      window.location.href = `/sessions/${session.session_id}`;
    } catch (error) {
      console.error('Failed to create session:', error);
      alert('Failed to create session. Please try again.');
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    if (!confirm('Are you sure you want to delete this session? This action cannot be undone.')) {
      return;
    }

    try {
      await deleteSessionMutation.mutateAsync(sessionId);
    } catch (error) {
      console.error('Failed to delete session:', error);
      alert('Failed to delete session. Please try again.');
    }
  };

  const handleDuplicateSession = async (sessionId: string) => {
    try {
      const session = await duplicateSessionMutation.mutateAsync({ sessionId });
      // Navigate to the duplicated session
      window.location.href = `/sessions/${session.session_id}`;
    } catch (error) {
      console.error('Failed to duplicate session:', error);
      alert('Failed to duplicate session. Please try again.');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading sessions...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-red-500">Error loading sessions</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">AI Video Factory</h1>
          <p className="text-muted-foreground mt-1">Generate cinematic videos from text ideas</p>
        </div>
        <button
          onClick={() => setShowNewDialog(true)}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
        >
          New Session
        </button>
      </div>

      {/* Sessions Grid */}
      {sessions && sessions.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sessions.map((session) => (
            <div
              key={session.session_id}
              className="border rounded-lg p-6 hover:shadow-lg transition-shadow"
            >
              {/* Status Badge */}
              <div className="flex items-center justify-between mb-4">
                <span
                  className={`px-2 py-1 text-xs rounded-full ${
                    session.completed
                      ? 'bg-green-100 text-green-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}
                >
                  {session.completed ? 'Completed' : 'In Progress'}
                </span>
                <span className="text-xs text-muted-foreground">
                  {session.started_at ? (() => {
                    try {
                      return formatDistanceToNow(new Date(session.started_at), { addSuffix: true });
                    } catch (e) {
                      return 'Unknown date';
                    }
                  })() : 'Unknown date'}
                </span>
              </div>

              {/* Title */}
              <h3 className="text-lg font-semibold mb-2 line-clamp-2">{session.idea}</h3>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-4 mb-4 text-sm">
                <div>
                  <div className="text-muted-foreground">Shots</div>
                  <div className="font-medium">{session.total_shots}</div>
                </div>
                <div>
                  <div className="text-muted-foreground">Images</div>
                  <div className="font-medium">
                    {session.images_generated}/{session.total_shots}
                  </div>
                </div>
                <div>
                  <div className="text-muted-foreground">Videos</div>
                  <div className="font-medium">
                    {session.videos_rendered}/{session.total_shots}
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <Link
                  href={`/sessions/${session.session_id}`}
                  className="flex-1 px-3 py-2 text-center bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors text-sm"
                >
                  View
                </Link>
                <button
                  onClick={() => handleDuplicateSession(session.session_id)}
                  className="px-3 py-2 border rounded-md hover:bg-muted transition-colors text-sm"
                  title="Duplicate session"
                >
                  Duplicate
                </button>
                <button
                  onClick={() => handleDeleteSession(session.session_id)}
                  className="px-3 py-2 border border-red-200 text-red-600 rounded-md hover:bg-red-50 transition-colors text-sm"
                  title="Delete session"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">No sessions yet. Create your first session!</p>
          <button
            onClick={() => setShowNewDialog(true)}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            Create Session
          </button>
        </div>
      )}

      {/* New Session Dialog */}
      {showNewDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Create New Session</h2>
            <form onSubmit={handleCreateSession}>
              <div className="mb-4">
                <label htmlFor="idea" className="block text-sm font-medium mb-2">
                  Video Idea
                </label>
                <textarea
                  id="idea"
                  value={newIdea}
                  onChange={(e) => setNewIdea(e.target.value)}
                  className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary min-h-[100px] mb-4"
                  placeholder="Describe your video idea..."
                  required
                />
              </div>

              <div className="grid grid-cols-1 gap-4 mb-6">
                <div>
                  <label className="block text-sm font-medium mb-1">Story Agent</label>
                  <select 
                    value={selectedStoryAgent}
                    onChange={(e) => setSelectedStoryAgent(e.target.value)}
                    className="w-full border rounded-md p-2 text-sm"
                  >
                    {!agents?.story.length && <option value="default">Default</option>}
                    {agents?.story.map(agent => (
                      <option key={agent.id} value={agent.id}>{agent.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Image Agent</label>
                  <select 
                    value={selectedImageAgent}
                    onChange={(e) => setSelectedImageAgent(e.target.value)}
                    className="w-full border rounded-md p-2 text-sm"
                  >
                    {!agents?.image.length && <option value="default">Default</option>}
                    {agents?.image.map(agent => (
                      <option key={agent.id} value={agent.id}>{agent.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Video Agent</label>
                  <select 
                    value={selectedVideoAgent}
                    onChange={(e) => setSelectedVideoAgent(e.target.value)}
                    className="w-full border rounded-md p-2 text-sm"
                  >
                    {!agents?.video.length && <option value="default">Default</option>}
                    {agents?.video.map(agent => (
                      <option key={agent.id} value={agent.id}>{agent.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  onClick={() => setShowNewDialog(false)}
                  className="px-4 py-2 border rounded-md hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createSessionMutation.isPending}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  {createSessionMutation.isPending ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
