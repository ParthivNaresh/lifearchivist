/**
 * ListView component - renders items in list layout
 */

import { type FileSystemItem, type ViewMode } from '../types';
import { ListItem } from './ListItem';

interface ListViewProps {
  items: FileSystemItem[];
  viewMode: ViewMode;
  searchTerm: string;
  onItemClick: (item: FileSystemItem, viewMode: ViewMode, searchTerm: string) => void;
}

export const ListView: React.FC<ListViewProps> = ({ items, viewMode, searchTerm, onItemClick }) => {
  return (
    <div className="space-y-1">
      {items.map((item) => {
        const itemKey =
          item.type === 'folder' ? `folder-${item.name}` : `file-${item.documentId ?? item.name}`;
        return (
          <ListItem
            key={itemKey}
            item={item}
            onClick={() => onItemClick(item, viewMode, searchTerm)}
          />
        );
      })}
    </div>
  );
};
