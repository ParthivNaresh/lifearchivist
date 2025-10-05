/**
 * DocumentProcessingSection component
 */

import React from 'react';
import { FileText } from 'lucide-react';
import { Settings, SettingKey } from '../types';
import { FILE_SIZE_OPTIONS, UI_TEXT } from '../constants';

interface DocumentProcessingSectionProps {
  settings: Settings | null;
  onSettingChange: (key: SettingKey, value: any) => void;
}

export const DocumentProcessingSection: React.FC<DocumentProcessingSectionProps> = ({
  settings,
  onSettingChange,
}) => {
  return (
    <div className="bg-card rounded-lg border p-6">
      <div className="flex items-center space-x-3 mb-4">
        <FileText className="h-6 w-6 text-primary" />
        <h2 className="text-lg font-semibold">{UI_TEXT.SECTIONS.DOCUMENT_PROCESSING}</h2>
      </div>
      
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">Auto-extract dates</p>
            <p className="text-sm text-muted-foreground">
              {UI_TEXT.DESCRIPTIONS.AUTO_EXTRACT_DATES}
            </p>
          </div>
          <input 
            type="checkbox" 
            checked={settings?.auto_extract_dates || false}
            onChange={(e) => onSettingChange('auto_extract_dates', e.target.checked)}
            className="toggle" 
          />
        </div>
        
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium">Generate text previews</p>
            <p className="text-sm text-muted-foreground">
              {UI_TEXT.DESCRIPTIONS.GENERATE_PREVIEWS}
            </p>
          </div>
          <input 
            type="checkbox" 
            checked={settings?.generate_text_previews || false}
            onChange={(e) => onSettingChange('generate_text_previews', e.target.checked)}
            className="toggle" 
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Maximum file size (MB)</label>
          <select 
            value={settings?.max_file_size_mb || 100}
            onChange={(e) => onSettingChange('max_file_size_mb', parseInt(e.target.value))}
            className="w-full px-3 py-2 border border-input rounded-md bg-background"
          >
            {FILE_SIZE_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
};