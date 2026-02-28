/**
 * ShotGrid component - Grid view of shots with thumbnails
 */
import { ShotCard } from './ShotCard';
import { Shot } from '@/types';

interface ShotGridProps {
  shots: Shot[];
  sessionId: string;
}

export function ShotGrid({ shots, sessionId }: ShotGridProps) {
  if (shots.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No shots yet. Generate story and plan shots first.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {shots.map((shot) => (
        <ShotCard
          key={shot.index}
          shot={shot}
          sessionId={sessionId}
        />
      ))}
    </div>
  );
}
