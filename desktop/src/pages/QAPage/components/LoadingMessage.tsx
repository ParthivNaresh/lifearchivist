/**
 * LoadingMessage component - shown while processing
 */

import { Loader2 } from 'lucide-react';
import { UI_TEXT } from '../constants';

export const LoadingMessage: React.FC = () => {
  return (
    <div className="flex justify-start">
      <div className="max-w-3xl mr-auto">
        <div className="glass-card border border-border/30 p-4 rounded-lg">
          <div className="flex items-center space-x-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>{UI_TEXT.MESSAGE.THINKING}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
