/**
 * FileCard component - renders individual file cards in grid view
 */

import { File, Loader2 } from 'lucide-react';
import { type FileSystemItem } from '../types';
import { formatFileSize } from '../utils';

interface FileCardProps {
  item: FileSystemItem;
  onClick: () => void;
}

export const FileCard: React.FC<FileCardProps> = ({ item, onClick }) => {
  return (
    <div
      className="group relative flex flex-col items-center p-4 rounded-lg hover:bg-muted/50 cursor-pointer transition-all duration-200 hover:scale-105 min-w-0"
      onClick={onClick}
      title={item.displayName}
    >
      {/* Icon */}
      <div className="mb-3 flex-shrink-0">
        {item.icon ?? <File className="h-12 w-12 text-gray-500" />}
      </div>

      {/* Name - with proper truncation */}
      <div className="w-full px-2">
        <p className="text-sm font-medium text-center truncate mb-1">{item.displayName}</p>
      </div>

      {/* Info */}
      <p className="text-xs text-muted-foreground">{formatFileSize(item.size ?? 0)}</p>

      {/* Theme confidence indicator */}
      {item.themeConfidence && (
        <p className="text-xs text-muted-foreground mt-1">
          {Math.round(item.themeConfidence * 100)}% confidence
        </p>
      )}

      {/* Status indicator */}
      {item.status === 'ready' && (
        <div className="absolute top-2 right-2 w-2 h-2 bg-green-500 rounded-full" />
      )}
      {item.status === 'processing' && (
        <div className="absolute top-2 right-2">
          <Loader2 className="h-3 w-3 animate-spin text-yellow-600" />
        </div>
      )}
    </div>
  );
};
