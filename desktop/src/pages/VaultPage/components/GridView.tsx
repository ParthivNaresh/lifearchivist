/**
 * GridView component - renders items in grid layout
 */

import React from 'react';
import { ThemeCard } from './ThemeCard';
import { FileSystemItem, ViewMode } from '../types';
import { THEME_CONFIG } from '../constants';
import { SubthemeCard } from './SubthemeCard';
import { FileCard } from './FileCard';

interface GridViewProps {
  items: FileSystemItem[];
  viewMode: ViewMode;
  searchTerm: string;
  onItemClick: (item: FileSystemItem, viewMode: ViewMode, searchTerm: string) => void;
}

export const GridView: React.FC<GridViewProps> = ({ 
  items, 
  viewMode, 
  searchTerm, 
  onItemClick 
}) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {items.map((item, index) => {
        // Folder rendering based on hierarchy level
        if (item.type === 'folder') {
          // Categories and Subclassifications use SubthemeCard (colored cards)
          if (item.useColoredCard) {
            return (
              <SubthemeCard
                key={index}
                item={item}
                onClick={() => onItemClick(item, viewMode, searchTerm)}
              />
            );
          }
          
          // Themes use ThemeCard (gradient cards)
          const config = THEME_CONFIG[item.name] || THEME_CONFIG['Unclassified'];
          return (
            <ThemeCard
              key={index}
              themeName={item.name}
              displayName={item.displayName}
              icon={config.icon}
              description={config.description}
              itemCount={item.itemCount || 0}
              processingCount={item.processingCount}
              size={item.size || 0}
              onClick={() => onItemClick(item, viewMode, searchTerm)}
            />
          );
        }
        
        // File rendering
        return (
          <FileCard
            key={index}
            item={item}
            onClick={() => onItemClick(item, viewMode, searchTerm)}
          />
        );
      })}
    </div>
  );
};