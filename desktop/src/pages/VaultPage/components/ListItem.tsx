/**
 * ListItem component - renders items in list view
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Folder, File, ChevronRight, Clock, Eye, Loader2 } from 'lucide-react';
import { FileSystemItem } from '../types';
import { formatFileSize, formatDate, getSubclassificationConfig, getSubthemeCategoryConfig } from '../utils';
import { THEME_CONFIG } from '../constants';

interface ListItemProps {
  item: FileSystemItem;
  onClick: () => void;
}

export const ListItem: React.FC<ListItemProps> = ({ item, onClick }) => {
  const navigate = useNavigate();
  
  const renderFolderIcon = () => {
    // Categories and Subclassifications use their specific configs
    if (item.useColoredCard) {
      const config = item.hierarchyLevel === 'category' 
        ? getSubthemeCategoryConfig(item.displayName)
        : getSubclassificationConfig(item.displayName);
      
      return (
        <div className="p-2 bg-background/80 backdrop-blur rounded-md">
          {config.icon}
        </div>
      );
    }
    
    // Themes use THEME_CONFIG
    return THEME_CONFIG[item.name]?.icon || <Folder className="h-8 w-8 text-gray-500" />;
  };
  
  return (
    <div
      className="group flex items-center justify-between p-4 rounded-lg hover:bg-muted/50 cursor-pointer transition-all duration-200"
      onClick={onClick}
    >
      <div className="flex items-center space-x-4">
        {/* Icon */}
        <div className="flex-shrink-0">
          {item.type === 'folder' ? (
            renderFolderIcon()
          ) : (
            item.icon || <File className="h-8 w-8 text-gray-500" />
          )}
        </div>
        
        {/* Name and details */}
        <div>
          <p className="text-sm font-medium">{item.displayName}</p>
          {item.type === 'folder' && (
            <>
              <p className="text-xs text-muted-foreground mt-1">
                {item.itemCount} {item.itemCount === 1 ? 'document' : 'documents'} • {formatFileSize(item.size || 0)}
              </p>
              {item.processingCount && item.processingCount > 0 && (
                <p className="text-xs text-yellow-600">
                  {item.processingCount} still processing
                </p>
              )}
            </>
          )}
          {item.type === 'file' && (
            <>
              {item.wordCount && (
                <p className="text-xs text-muted-foreground mt-1">
                  {item.wordCount.toLocaleString()} words
                </p>
              )}
              {item.themes && item.themes.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Themes: {item.themes.join(', ')}
                </p>
              )}
            </>
          )}
        </div>
      </div>
      
      {/* Right side metadata */}
      <div className="flex items-center space-x-6">
        {item.type === 'file' && (
          <>
            <span className="text-sm text-muted-foreground">
              {formatFileSize(item.size || 0)}
            </span>
            <div className="flex items-center space-x-1 text-sm text-muted-foreground">
              <Clock className="h-3 w-3" />
              <span>{formatDate(item.created || '')}</span>
            </div>
            {item.status === 'processing' && (
              <Loader2 className="h-4 w-4 animate-spin text-yellow-600" />
            )}
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (item.documentId) navigate(`/vault/${item.documentId}/details`);
              }}
              className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-muted rounded"
              title="View details"
            >
              <Eye className="h-4 w-4" />
            </button>
          </>
        )}
        {item.type === 'folder' && (
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
        )}
      </div>
    </div>
  );
};