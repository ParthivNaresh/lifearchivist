/**
 * FileManagementSection component
 */

import React from 'react';
import { FolderOpen } from 'lucide-react';
import { Settings, SettingKey } from '../types';
import { UI_TEXT } from '../constants';

interface FileManagementSectionProps {
  settings: Settings | null;
  onSettingChange: (key: SettingKey, value: any) => void;
}

export const FileManagementSection: React.FC<FileManagementSectionProps> = ({
  settings,
  onSettingChange,
}) => {
  return (
    <div className="bg-card rounded-lg border p-6">
      <div className="flex items-center space-x-3 mb-4">
        <FolderOpen className="h-6 w-6 text-primary" />
        <h2 className="text-lg font-semibold">{UI_TEXT.SECTIONS.FILE_MANAGEMENT}</h2>
      </div>
      
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">Auto-organize by date</p>
            <p className="text-sm text-muted-foreground">
              {UI_TEXT.DESCRIPTIONS.AUTO_ORGANIZE}
            </p>
          </div>
          <input 
            type="checkbox" 
            checked={settings?.auto_organize_by_date || false}
            onChange={(e) => onSettingChange('auto_organize_by_date', e.target.checked)}
            className="toggle" 
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">Duplicate detection</p>
            <p className="text-sm text-muted-foreground">
              {UI_TEXT.DESCRIPTIONS.DUPLICATE_DETECTION}
            </p>
          </div>
          <input 
            type="checkbox" 
            checked={settings?.duplicate_detection || false}
            onChange={(e) => onSettingChange('duplicate_detection', e.target.checked)}
            className="toggle" 
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Default import location</label>
          <div className="flex space-x-2">
            <input
              type="text"
              value={settings?.default_import_location || '~/Documents'}
              onChange={(e) => onSettingChange('default_import_location', e.target.value)}
              className="flex-1 px-3 py-2 border border-input rounded-md bg-background"
            />
            <button className="px-4 py-2 border border-input rounded-md hover:bg-accent">
              Browse
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};