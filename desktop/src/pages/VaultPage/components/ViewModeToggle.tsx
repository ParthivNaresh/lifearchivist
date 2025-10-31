/**
 * ViewModeToggle component - switches between grid and list view
 */

import { Grid3x3, List } from 'lucide-react';
import { type ViewMode } from '../types';

interface ViewModeToggleProps {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}

export const ViewModeToggle: React.FC<ViewModeToggleProps> = ({ viewMode, onViewModeChange }) => {
  return (
    <div className="flex items-center bg-muted rounded-md">
      <button
        onClick={() => onViewModeChange('grid')}
        className={`p-2 rounded-l-md transition-colors ${
          viewMode === 'grid'
            ? 'bg-primary text-primary-foreground'
            : 'hover:bg-muted-foreground/20'
        }`}
        title="Grid view"
      >
        <Grid3x3 className="h-4 w-4" />
      </button>
      <button
        onClick={() => onViewModeChange('list')}
        className={`p-2 rounded-r-md transition-colors ${
          viewMode === 'list'
            ? 'bg-primary text-primary-foreground'
            : 'hover:bg-muted-foreground/20'
        }`}
        title="List view"
      >
        <List className="h-4 w-4" />
      </button>
    </div>
  );
};
