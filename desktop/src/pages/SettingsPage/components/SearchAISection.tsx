/**
 * SearchAISection component
 */

import React from 'react';
import { Brain } from 'lucide-react';
import { Settings, SettingKey, AvailableModels } from '../types';
import { SEARCH_LIMIT_OPTIONS, UI_TEXT } from '../constants';

interface SearchAISectionProps {
  settings: Settings | null;
  availableModels: AvailableModels | null;
  onSettingChange: (key: SettingKey, value: any) => void;
}

export const SearchAISection: React.FC<SearchAISectionProps> = ({
  settings,
  availableModels,
  onSettingChange,
}) => {
  return (
    <div className="bg-card rounded-lg border p-6">
      <div className="flex items-center space-x-3 mb-4">
        <Brain className="h-6 w-6 text-primary" />
        <h2 className="text-lg font-semibold">{UI_TEXT.SECTIONS.SEARCH_AI}</h2>
      </div>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">Language Model</label>
          <select 
            value={settings?.llm_model || 'llama3.2:1b'}
            onChange={(e) => onSettingChange('llm_model', e.target.value)}
            className="w-full px-3 py-2 border border-input rounded-md bg-background"
          >
            {availableModels?.llm_models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name} ({model.performance})
              </option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground mt-1">
            {UI_TEXT.DESCRIPTIONS.LLM_MODEL}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Embedding Model</label>
          <select 
            value={settings?.embedding_model || 'all-MiniLM-L6-v2'}
            onChange={(e) => onSettingChange('embedding_model', e.target.value)}
            className="w-full px-3 py-2 border border-input rounded-md bg-background"
          >
            {availableModels?.embedding_models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name} ({model.performance})
              </option>
            ))}
          </select>
          <p className="text-xs text-muted-foreground mt-1">
            {UI_TEXT.DESCRIPTIONS.EMBEDDING_MODEL}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Search results limit</label>
          <select 
            value={settings?.search_results_limit || 25}
            onChange={(e) => onSettingChange('search_results_limit', parseInt(e.target.value))}
            className="w-full px-3 py-2 border border-input rounded-md bg-background"
          >
            {SEARCH_LIMIT_OPTIONS.map(option => (
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