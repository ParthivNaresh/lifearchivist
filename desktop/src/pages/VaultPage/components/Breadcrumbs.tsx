/**
 * Breadcrumbs component - navigation breadcrumbs
 */

import { Fragment } from 'react';
import { Home, ChevronRight } from 'lucide-react';

interface BreadcrumbsProps {
  currentPath: string[];
  onNavigate: (index: number) => void;
}

export const Breadcrumbs = ({ currentPath, onNavigate }: BreadcrumbsProps) => {
  return (
    <div className="glass-card p-3 rounded-lg">
      <div className="flex items-center space-x-2">
        <button
          onClick={() => onNavigate(0)}
          className="flex items-center space-x-1 hover:text-primary transition-colors"
        >
          <Home className="h-4 w-4" />
          <span className="text-sm font-medium">All Documents</span>
        </button>

        {currentPath.slice(1).map((path, index) => {
          const pathKey = currentPath.slice(0, index + 2).join('/');
          return (
            <Fragment key={pathKey}>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
              <button
                onClick={() => onNavigate(index + 1)}
                className="text-sm font-medium hover:text-primary transition-colors"
              >
                {path}
              </button>
            </Fragment>
          );
        })}
      </div>
    </div>
  );
};
