/**
 * AppearanceSection component
 */

import React from 'react';
import { Palette } from 'lucide-react';
import { Settings, SettingKey } from '../types';
import { THEME_OPTIONS, DENSITY_OPTIONS, UI_TEXT } from '../constants';

interface AppearanceSectionProps {
  settings: Settings | null;
  theme: string;
  resolvedTheme: string | undefined;
  onThemeChange: (theme: 'light' | 'dark' | 'system') => void;
  onSettingChange: (key: SettingKey, value: any) => void;
}

export const AppearanceSection: React.FC<AppearanceSectionProps> = ({
  settings,
  theme,
  resolvedTheme,
  onThemeChange,
  onSettingChange,
}) => {
  return (
    <div className="bg-card rounded-lg border p-6">
      <div className="flex items-center space-x-3 mb-4">
        <Palette className="h-6 w-6 text-primary" />
        <h2 className="text-lg font-semibold">{UI_TEXT.SECTIONS.APPEARANCE}</h2>
      </div>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Theme</label>
          <select 
            value={theme}
            onChange={(e) => onThemeChange(e.target.value as 'light' | 'dark' | 'system')}
            className="w-full px-3 py-2 border border-input rounded-md bg-background transition-colors"
          >
            {THEME_OPTIONS.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground mt-1">
            {UI_TEXT.DESCRIPTIONS.THEME_CURRENT} {resolvedTheme === 'dark' ? 'Dark' : 'Light'}
            {theme === 'system' && ` ${UI_TEXT.DESCRIPTIONS.THEME_SYSTEM}`}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Interface density</label>
          <select 
            value={settings?.interface_density || 'comfortable'}
            onChange={(e) => onSettingChange('interface_density', e.target.value)}
            className="w-full px-3 py-2 border border-input rounded-md bg-background"
          >
            {DENSITY_OPTIONS.map(option => (
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