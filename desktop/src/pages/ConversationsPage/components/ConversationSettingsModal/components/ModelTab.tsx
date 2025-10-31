import { Loader2, AlertCircle } from 'lucide-react';
import * as Tabs from '@radix-ui/react-tabs';
import type { AvailableModels } from '../types';

interface ModelTabProps {
  availableModels: AvailableModels | null;
  currentModel: string;
  saving: boolean;
  modelError: string | null;
  onModelChange: (model: string) => void;
}

export const ModelTab: React.FC<ModelTabProps> = ({
  availableModels,
  currentModel,
  saving,
  modelError,
  onModelChange,
}) => {
  return (
    <Tabs.Content value="model" className="space-y-4">
      <div className="bg-card/50 backdrop-blur-sm rounded-lg border border-border/30 p-6">
        <h3 className="text-base font-medium mb-4">Language Model</h3>

        {availableModels ? (
          <>
            <select
              value={currentModel}
              onChange={(e) => onModelChange(e.target.value)}
              disabled={saving}
              className="w-full px-4 py-3 border border-input rounded-md bg-background/50 backdrop-blur-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-primary/50"
            >
              {availableModels.llm_models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
            <p className="text-sm text-muted-foreground mt-3">
              Select the language model to use for all conversations. Changes apply immediately.
            </p>
            {saving && (
              <div className="flex items-center gap-2 mt-3 text-sm text-primary">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Saving...</span>
              </div>
            )}
            {modelError && (
              <div className="mt-3 p-3 bg-destructive/10 border border-destructive/20 rounded-md flex items-start gap-2">
                <AlertCircle className="h-4 w-4 text-destructive mt-0.5 flex-shrink-0" />
                <p className="text-sm text-destructive">{modelError}</p>
              </div>
            )}
          </>
        ) : (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Loading models...</span>
          </div>
        )}
      </div>
    </Tabs.Content>
  );
};
