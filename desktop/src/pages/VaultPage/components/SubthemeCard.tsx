/**
 * SubthemeCard component - renders subtheme folder cards with special styling
 */

import React from 'react';
import { ChevronRight } from 'lucide-react';
import { FileSystemItem } from '../types';
import { formatFileSize, getSubthemeStyles } from '../utils';
import { getSubclassificationConfig } from '../utils';

interface SubthemeCardProps {
  item: FileSystemItem;
  onClick: () => void;
}

export const SubthemeCard: React.FC<SubthemeCardProps> = ({ item, onClick }) => {
  const subclassificationConfig = getSubclassificationConfig(item.displayName);
  const styles = getSubthemeStyles(item.displayName);
  
  return (
    <div
      className="group relative rounded-lg p-4 cursor-pointer transition-all duration-200 hover:scale-[1.02] hover:shadow-md"
      style={{
        backgroundColor: styles.bg,
        border: `2px solid ${styles.border}`,
      }}
      onClick={onClick}
    >
      {/* Header with icon and count */}
      <div className="flex items-center justify-between mb-3">
        <div 
          className="p-2 bg-background/80 backdrop-blur rounded-md"
          style={{ color: styles.icon }}
        >
          {subclassificationConfig.icon}
        </div>
        <div className="text-right">
          <p className="text-lg font-semibold text-foreground/90">{item.itemCount}</p>
          <p className="text-xs text-muted-foreground">
            {item.itemCount === 1 ? 'file' : 'files'}
          </p>
        </div>
      </div>
      
      {/* Subtheme name */}
      <h3 className="font-medium text-sm mb-1 text-foreground">
        {item.displayName}
      </h3>
      
      {/* Description if available */}
      {subclassificationConfig.description && (
        <p className="text-xs text-muted-foreground mb-2 line-clamp-1">
          {subclassificationConfig.description}
        </p>
      )}
      
      {/* Bottom metadata */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{formatFileSize(item.size || 0)}</span>
        <ChevronRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </div>
  );
};