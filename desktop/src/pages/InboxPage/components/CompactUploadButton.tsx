/**
 * CompactUploadButton - Compact header upload button with dropdown
 * 
 * Provides upload functionality without dominating the page.
 * Includes: Upload Files, Upload Folder, Watch Folder
 */

import React, { useState, useRef, useEffect } from 'react';
import { Upload, FolderOpen, Eye, ChevronDown, Settings } from 'lucide-react';
import { cn } from '../../../utils/cn';

interface CompactUploadButtonProps {
  onUploadFiles: () => void;
  onUploadFolder: () => void;
  onWatchFolder: () => void;
  onManageWatchedFolders?: () => void;
  disabled?: boolean;
  watchedFolderPath?: string | null;
  watchedFolderPending?: number;
}

export const CompactUploadButton: React.FC<CompactUploadButtonProps> = ({
  onUploadFiles,
  onUploadFolder,
  onWatchFolder,
  onManageWatchedFolders,
  disabled = false,
  watchedFolderPath = null,
  watchedFolderPending = 0,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  // Close dropdown on Escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen]);

  const handleAction = (action: () => void) => {
    action();
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Main Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className={cn(
          'flex items-center gap-2 px-4 py-2 rounded-lg',
          'bg-primary text-primary-foreground',
          'hover:bg-primary/90 transition-all',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'font-medium text-sm shadow-sm'
        )}
      >
        <Upload className="h-4 w-4" />
        <span>Upload</span>
        <ChevronDown 
          className={cn(
            'h-3 w-3 transition-transform',
            isOpen && 'rotate-180'
          )} 
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full right-0 mt-2 w-64 bg-popover border border-border rounded-lg shadow-xl z-50 overflow-hidden">
          {/* Upload Files */}
          <button
            onClick={() => handleAction(onUploadFiles)}
            className="w-full flex items-center gap-3 px-4 py-3 hover:bg-accent transition-colors text-left"
          >
            <Upload className="h-4 w-4 text-muted-foreground" />
            <div className="flex-1">
              <div className="font-medium text-sm">Upload Files</div>
              <div className="text-xs text-muted-foreground">Select individual files</div>
            </div>
            <kbd className="px-2 py-1 text-xs bg-muted rounded">⌘O</kbd>
          </button>

          {/* Upload Folder */}
          <button
            onClick={() => handleAction(onUploadFolder)}
            className="w-full flex items-center gap-3 px-4 py-3 hover:bg-accent transition-colors text-left"
          >
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
            <div className="flex-1">
              <div className="font-medium text-sm">Upload Folder</div>
              <div className="text-xs text-muted-foreground">Upload all files from a folder</div>
            </div>
            <kbd className="px-2 py-1 text-xs bg-muted rounded">⌘⇧O</kbd>
          </button>

          {/* Divider */}
          <div className="border-t border-border my-1" />

          {/* Watch Folder */}
          <button
            onClick={() => handleAction(onWatchFolder)}
            className="w-full flex items-center gap-3 px-4 py-3 hover:bg-accent transition-colors text-left"
          >
            <Eye className="h-4 w-4 text-muted-foreground" />
            <div className="flex-1">
              <div className="font-medium text-sm">Watch Folder</div>
              <div className="text-xs text-muted-foreground">Auto-sync new files</div>
            </div>
          </button>

          {/* Watched Folder Status */}
          {watchedFolderPath && (
            <>
              <div className="border-t border-border my-1" />
              <div className="px-4 py-3 bg-secondary/30">
                <div className="flex items-center gap-2 mb-1">
                  <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-xs font-medium">Watching Folder</span>
                </div>
                <div className="text-xs text-muted-foreground truncate" title={watchedFolderPath}>
                  {watchedFolderPath.split('/').slice(-2).join('/')}
                </div>
                {watchedFolderPending > 0 && (
                  <div className="text-xs text-muted-foreground mt-1">
                    {watchedFolderPending} file{watchedFolderPending !== 1 ? 's' : ''} pending
                  </div>
                )}
                {onManageWatchedFolders && (
                  <button
                    onClick={() => handleAction(onManageWatchedFolders)}
                    className="flex items-center gap-1 text-xs text-primary hover:underline mt-2"
                  >
                    <Settings className="h-3 w-3" />
                    Manage
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};
