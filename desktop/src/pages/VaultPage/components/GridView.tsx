/**
 * GridView component - renders items in grid layout
 */

import { ThemeCard } from './ThemeCard';
import { type FileSystemItem, type ViewMode } from '../types';
import { THEME_CONFIG } from '../constants';
import { SubthemeCard } from './SubthemeCard';
import { FileCard } from './FileCard';

interface GridViewProps {
  items: FileSystemItem[];
  viewMode: ViewMode;
  searchTerm: string;
  onItemClick: (item: FileSystemItem, viewMode: ViewMode, searchTerm: string) => void;
}

export const GridView: React.FC<GridViewProps> = ({ items, viewMode, searchTerm, onItemClick }) => {
  /**
   * Generate a stable unique key for each item.
   * For folders, use the name which is unique at each level.
   * For files, use documentId if available, otherwise fall back to name (file hash).
   */
  const getItemKey = (item: FileSystemItem): string => {
    if (item.type === 'folder') {
      // Folder names are unique within their hierarchy level
      return `folder-${item.name}`;
    }
    // For files, prefer documentId as it's guaranteed unique
    // Fall back to name (which is the file hash) if documentId is not available
    return item.documentId ? `file-${item.documentId}` : `file-${item.name}`;
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {items.map((item) => {
        const itemKey = getItemKey(item);

        // Folder rendering based on hierarchy level
        if (item.type === 'folder') {
          // Categories and Subclassifications use SubthemeCard (colored cards)
          if (item.useColoredCard) {
            return (
              <SubthemeCard
                key={itemKey}
                item={item}
                onClick={() => onItemClick(item, viewMode, searchTerm)}
              />
            );
          }

          // Themes use ThemeCard (gradient cards)
          const config = THEME_CONFIG[item.name] ??
            THEME_CONFIG.Unclassified ?? {
              icon: '📄',
              description: 'Documents',
              gradient: 'from-gray-500 to-gray-600',
              bgColor: 'bg-gray-50 dark:bg-gray-900/50',
              borderColor: 'border-gray-200 dark:border-gray-700',
            };
          return (
            <ThemeCard
              key={itemKey}
              themeName={item.name}
              displayName={item.displayName}
              icon={config.icon}
              description={config.description}
              itemCount={item.itemCount ?? 0}
              processingCount={item.processingCount}
              size={item.size ?? 0}
              onClick={() => onItemClick(item, viewMode, searchTerm)}
            />
          );
        }

        // File rendering
        return (
          <FileCard
            key={itemKey}
            item={item}
            onClick={() => onItemClick(item, viewMode, searchTerm)}
          />
        );
      })}
    </div>
  );
};
