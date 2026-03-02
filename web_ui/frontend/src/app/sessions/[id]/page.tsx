/**
 * Session detail page
 */
'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useSession } from '@/hooks/useSessions';
import { formatDistanceToNow } from 'date-fns';
import { getMediaUrl } from '@/lib/utils';

export default function SessionDetailPage() {
  const params = useParams();
  const sessionId = params.id as string;
  const { data: session, isLoading, error } = useSession(sessionId);

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

  // Calculate progress percentages
  const imageProgress = session.stats.total_shots > 0
    ? (session.stats.images_generated / session.stats.total_shots) * 100
    : 0;
  const videoProgress = session.stats.total_shots > 0
    ? (session.stats.videos_rendered / session.stats.total_shots) * 100
    : 0;

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          href="/sessions"
          className="text-primary hover:underline mb-4 inline-block"
        >
          ← Back to Sessions
        </Link>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold">{session.session_id}</h1>
              <span
                className={`px-3 py-1 text-sm rounded-full ${session.completed
                    ? 'bg-green-100 text-green-800'
                    : 'bg-yellow-100 text-yellow-800'
                  }`}
              >
                {session.completed ? 'Completed' : 'In Progress'}
              </span>
            </div>
            <p className="text-muted-foreground">
              Started {session.started_at ? (() => {
                try {
                  return formatDistanceToNow(new Date(session.started_at), { addSuffix: true });
                } catch (e) {
                  return 'Unknown date';
                }
              })() : 'Unknown date'}
            </p>
          </div>
          <div className="flex gap-2">
            <Link
              href={`/sessions/${sessionId}/settings`}
              className="px-4 py-2 border rounded-md hover:bg-muted transition-colors"
            >
              Settings
            </Link>
            <Link
              href={`/sessions/${sessionId}/edit`}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
            >
              Edit Session
            </Link>
          </div>
        </div>
      </div>

      {/* Session Info */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Idea */}
        <div className="border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-3">Video Idea</h2>
          <p className="text-muted-foreground whitespace-pre-wrap">{session.idea}</p>
        </div>

        {/* Progress */}
        <div className="border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Progress</h2>

          <div className="space-y-4">
            {/* Story */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Story</span>
                <span>{session.steps.story ? '✓' : '○'}</span>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${session.steps.story ? 'bg-green-500' : 'bg-gray-300'
                    }`}
                  style={{ width: session.steps.story ? '100%' : '0%' }}
                />
              </div>
            </div>

            {/* Shots */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Shots</span>
                <span>{session.steps.shots ? '✓' : '○'}</span>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${session.steps.shots ? 'bg-green-500' : 'bg-gray-300'
                    }`}
                  style={{ width: session.steps.shots ? '100%' : '0%' }}
                />
              </div>
            </div>

            {/* Images */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Images ({session.stats.images_generated}/{session.stats.total_shots})</span>
                <span>{Math.round(imageProgress)}%</span>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all"
                  style={{ width: `${imageProgress}%` }}
                />
              </div>
            </div>

            {/* Videos */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Videos ({session.stats.videos_rendered}/{session.stats.total_shots})</span>
                <span>{Math.round(videoProgress)}%</span>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div
                  className="bg-purple-500 h-2 rounded-full transition-all"
                  style={{ width: `${videoProgress}%` }}
                />
              </div>
            </div>

            {/* Narration */}
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Narration</span>
                <span>{session.steps.narration ? '✓' : '○'}</span>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${session.steps.narration ? 'bg-green-500' : 'bg-gray-300'
                    }`}
                  style={{ width: session.steps.narration ? '100%' : '0%' }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Story Section */}
      {session.story && (
        <div className="border rounded-lg p-6 mb-8">
          <h2 className="text-lg font-semibold mb-4">Story</h2>
          <div className="mb-4">
            <h3 className="text-xl font-bold">{session.story.title}</h3>
            <p className="text-muted-foreground">Style: {session.story.style}</p>
          </div>

          {session.story.scenes && session.story.scenes.length > 0 && (
            <div className="space-y-4">
              <h3 className="font-semibold">Scenes ({session.story.scenes.length})</h3>
              {session.story.scenes.map((scene, idx) => (
                <div key={idx} className="border-l-4 border-primary pl-4">
                  <div className="text-sm text-muted-foreground mb-1">Scene {idx + 1}</div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="font-medium">Location:</span> {scene.location}
                    </div>
                    <div>
                      <span className="font-medium">Characters:</span> {scene.characters}
                    </div>
                    <div>
                      <span className="font-medium">Action:</span> {scene.action}
                    </div>
                    <div>
                      <span className="font-medium">Emotion:</span> {scene.emotion}
                    </div>
                    {scene.scene_duration && (
                      <div>
                        <span className="font-medium">Duration:</span> {scene.scene_duration}s
                      </div>
                    )}
                  </div>
                  {scene.narration && (
                    <div className="mt-2 text-sm italic text-muted-foreground">
                      "{scene.narration}"
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Shots Section */}
      {session.shots && session.shots.length > 0 && (
        <div className="border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Shots ({session.shots.length})</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {session.shots.slice(0, 12).map((shot) => (
              <div key={shot.index} className="border rounded p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">Shot {shot.index}</span>
                  <span className="text-xs text-muted-foreground">{shot.camera}</span>
                </div>

                {/* Media Preview */}
                <div className="mb-2 aspect-video bg-muted rounded overflow-hidden relative group flex items-center justify-center">
                  {shot.video_rendered && shot.video_path ? (
                    <video
                      src={getMediaUrl(shot.video_path)}
                      poster={getMediaUrl(shot.image_path)}
                      controls
                      className="w-full h-full object-cover"
                    />
                  ) : shot.image_path ? (
                    <img
                      src={getMediaUrl(shot.image_path)}
                      alt={`Shot ${shot.index}`}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <span className="text-muted-foreground text-xs">No media</span>
                  )}
                </div>

                {/* Status */}
                <div className="flex gap-2 text-xs mb-2">
                  <span className={shot.image_generated ? 'text-green-600' : 'text-gray-400'}>
                    Image: {shot.image_generated ? '✓' : '○'}
                  </span>
                  <span className={shot.video_rendered ? 'text-green-600' : 'text-gray-400'}>
                    Video: {shot.video_rendered ? '✓' : '○'}
                  </span>
                </div>

                {/* Prompts */}
                <div className="text-xs text-muted-foreground line-clamp-2">
                  {shot.image_prompt}
                </div>
              </div>
            ))}
          </div>

          {session.shots.length > 12 && (
            <div className="text-center mt-4 text-muted-foreground">
              And {session.shots.length - 12} more shots...
            </div>
          )}
        </div>
      )}
    </div>
  );
}
