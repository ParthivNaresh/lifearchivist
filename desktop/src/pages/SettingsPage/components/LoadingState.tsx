/**
 * LoadingState component
 */

import { Clock } from 'lucide-react';
import { UI_TEXT } from '../constants';

export const LoadingState: React.FC = () => {
  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Clock className="h-8 w-8 animate-spin mx-auto mb-2" />
            <p className="text-muted-foreground">{UI_TEXT.LOADING}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
