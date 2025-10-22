/**
 * RecentActivity - Activity feed component
 *
 * Displays recent system events with timestamps
 */

import { Activity } from 'lucide-react';
import { type ActivityEvent } from '../../../hooks/useActivityFeed';
import { formatTimestamp, formatActivityMessage } from '../utils';

interface RecentActivityProps {
  events: ActivityEvent[];
  isLoading?: boolean;
  onViewAll?: () => void;
}

export const RecentActivity: React.FC<RecentActivityProps> = ({
  events,
  isLoading = false,
  onViewAll,
}) => {
  // Determine content to render based on state
  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="text-center py-8 text-muted-foreground">
          <Activity className="h-12 w-12 mx-auto mb-3 opacity-50 animate-pulse" />
          <p>Loading activity...</p>
        </div>
      );
    }

    if (events.length === 0) {
      return (
        <div className="text-center py-8 text-muted-foreground">
          <Activity className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p>No recent activity</p>
          <p className="text-sm mt-1">Upload documents to get started</p>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        {events.map((event) => (
          <div
            key={event.id}
            className="flex items-center justify-between p-3 rounded-lg hover:bg-accent/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 rounded-full bg-primary" />
              <span className="text-sm">{formatActivityMessage(event)}</span>
            </div>
            <span className="text-xs text-muted-foreground">
              {formatTimestamp(event.timestamp)}
            </span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="glass-card rounded-xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          Recent Activity
        </h2>
        {onViewAll && (
          <button onClick={onViewAll} className="text-sm text-primary hover:underline">
            View all
          </button>
        )}
      </div>

      {/* Content */}
      {renderContent()}
    </div>
  );
};
