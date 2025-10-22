/**
 * SettingsHeader component - displays page title and save button
 */

import { Save, RefreshCw } from 'lucide-react';
import { UI_TEXT } from '../constants';

interface SettingsHeaderProps {
  saving: boolean;
  saveMessage: string | null;
  hasUnsavedChanges: boolean;
  onSave: () => void;
}

export const SettingsHeader: React.FC<SettingsHeaderProps> = ({
  saving,
  saveMessage,
  hasUnsavedChanges,
  onSave,
}) => {
  return (
    <div className="flex items-center justify-between mb-6">
      <h1 className="text-2xl font-bold">{UI_TEXT.PAGE_TITLE}</h1>

      {/* Save Button */}
      <div className="flex items-center space-x-3">
        {saveMessage && (
          <span
            className={`text-sm ${
              saveMessage.includes('success') ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {saveMessage}
          </span>
        )}
        <button
          onClick={onSave}
          disabled={saving || !hasUnsavedChanges}
          className="flex items-center space-x-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
        >
          {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          <span>{saving ? UI_TEXT.SAVING_BUTTON : UI_TEXT.SAVE_BUTTON}</span>
        </button>
      </div>
    </div>
  );
};
