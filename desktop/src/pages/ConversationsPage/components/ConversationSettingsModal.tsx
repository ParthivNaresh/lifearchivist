/**
 * Conversation Settings Modal
 */

import { useEffect, useState } from 'react';
import { X, Trash2, Brain, AlertCircle } from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import axios from 'axios';

interface LLMModel {
  id: string;
  name: string;
  performance: string;
}

interface AvailableModels {
  llm_models: LLMModel[];
}

interface SettingsResponse {
  llm_model: string;
  embedding_model?: string;
  whisper_model?: string;
  ocr_lang?: string;
  [key: string]: unknown;
}

interface ConversationSettingsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeleteAllConversations: () => void;
}

export const ConversationSettingsModal: React.FC<ConversationSettingsModalProps> = ({
  open,
  onOpenChange,
  onDeleteAllConversations,
}) => {
  const [availableModels, setAvailableModels] = useState<AvailableModels | null>(null);
  const [currentModel, setCurrentModel] = useState<string>('llama3.2:1b');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    if (open) {
      // Fetch available models and current settings
      Promise.all([
        axios.get<AvailableModels>('http://localhost:8000/api/settings/models'),
        axios.get<SettingsResponse>('http://localhost:8000/api/settings'),
      ])
        .then(([modelsRes, settingsRes]) => {
          setAvailableModels(modelsRes.data);
          setCurrentModel(settingsRes.data.llm_model || 'llama3.2:1b');
        })
        .catch((err) => {
          console.error('Failed to fetch models:', err);
        });
    }
  }, [open]);

  const handleModelChange = async (newModel: string) => {
    setSaving(true);
    try {
      await axios.put('http://localhost:8000/api/settings', {
        llm_model: newModel,
      });
      setCurrentModel(newModel);
      setError(null);
    } catch (err) {
      console.error('Failed to update model:', err);
      setError('Failed to update model. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAll = () => {
    setShowDeleteConfirm(true);
  };

  const confirmDeleteAll = () => {
    onDeleteAllConversations();
    onOpenChange(false);
    setShowDeleteConfirm(false);
  };

  const cancelDeleteAll = () => {
    setShowDeleteConfirm(false);
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-background/95 backdrop-blur-xl border border-border/50 rounded-xl shadow-2xl w-full max-w-2xl z-50 p-8">
          <div className="flex items-center justify-between mb-6">
            <Dialog.Title className="text-xl font-semibold">Conversation Settings</Dialog.Title>
            <Dialog.Close asChild>
              <button
                className="p-2 rounded-md hover:bg-accent transition-colors"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </Dialog.Close>
          </div>

          <div className="space-y-8">
            {/* Model Selection */}
            <div className="bg-card/50 backdrop-blur-sm rounded-lg border border-border/30 p-6">
              <div className="flex items-center space-x-3 mb-4">
                <Brain className="h-5 w-5 text-primary" />
                <h3 className="text-base font-medium">Language Model</h3>
              </div>

              {availableModels ? (
                <>
                  <select
                    value={currentModel}
                    onChange={(e) => void handleModelChange(e.target.value)}
                    disabled={saving}
                    className="w-full px-4 py-3 border border-input rounded-md bg-background/50 backdrop-blur-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {availableModels.llm_models.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.name} ({model.performance})
                      </option>
                    ))}
                  </select>
                  <p className="text-sm text-muted-foreground mt-3">
                    Select the language model to use for all conversations. Changes apply
                    immediately.
                  </p>
                  {saving && <p className="text-sm text-primary mt-2">Saving...</p>}
                  {error && (
                    <div className="mt-3 p-3 bg-destructive/10 border border-destructive/20 rounded-md flex items-start gap-2">
                      <AlertCircle className="h-4 w-4 text-destructive mt-0.5 flex-shrink-0" />
                      <p className="text-sm text-destructive">{error}</p>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm text-muted-foreground">Loading models...</p>
              )}
            </div>

            {/* Delete All Conversations */}
            <div className="bg-destructive/5 backdrop-blur-sm rounded-lg border border-destructive/20 p-6">
              <h3 className="text-base font-medium mb-2 text-destructive flex items-center space-x-2">
                <Trash2 className="h-5 w-5" />
                <span>Danger Zone</span>
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                Permanently delete all conversations. This action cannot be undone.
              </p>
              <button
                onClick={handleDeleteAll}
                className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90 transition-colors font-medium"
              >
                <Trash2 className="h-4 w-4" />
                <span>Delete All Conversations</span>
              </button>
            </div>
          </div>

          {/* Delete All Confirmation Dialog */}
          {showDeleteConfirm && (
            <div className="absolute inset-0 bg-background/80 backdrop-blur-sm rounded-xl flex items-center justify-center p-6">
              <div className="bg-card border border-border rounded-lg shadow-xl max-w-md w-full p-6">
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-destructive/10 rounded-full">
                    <Trash2 className="h-6 w-6 text-destructive" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold mb-2">Delete All Conversations</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                      This will permanently delete ALL your conversations and cannot be undone. Are
                      you absolutely sure?
                    </p>
                    <div className="flex gap-3 justify-end">
                      <button
                        onClick={cancelDeleteAll}
                        className="px-4 py-2 text-sm border border-border rounded-md hover:bg-accent transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={confirmDeleteAll}
                        className="px-4 py-2 text-sm bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90 transition-colors"
                      >
                        Delete All
                      </button>
                    </div>
                  </div>
                  <button
                    onClick={cancelDeleteAll}
                    className="p-1 hover:bg-accent rounded-md transition-colors"
                    aria-label="Close"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
