import { useState, useMemo, useEffect } from 'react';
import { X, Settings, Trash2 } from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import * as Tabs from '@radix-ui/react-tabs';
import { useProviderManagement } from './hooks/useProviderManagement';
import { useAllProviderModels } from '../../providers-hooks';
import { DangerZoneTab, DeleteConfirmDialog } from './components';
import { ProvidersTabWrapper } from './components/ProvidersTabWrapper';
import { ProviderDeleteConfirmDialog } from './components/ProviderDeleteConfirmDialog';
import type { ConversationSettingsModalProps } from './types';

export const ConversationSettingsModal: React.FC<ConversationSettingsModalProps> = ({
  open,
  onOpenChange,
  onDeleteAllConversations,
  onProvidersChanged,
}) => {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const {
    providers,
    providersLoading,
    showAddForm,
    formState,
    providerError,
    expandedProviders,
    testResults,
    testingProviders,
    isSubmitting,
    isSettingDefault,
    isDeleting,
    deleteConfirmState,
    hasDeletedProvider,
    setHasDeletedProvider,
    updateField,
    handleShowAddForm,
    handleHideAddForm,
    handleAddProvider,
    handleDeleteProvider,
    confirmDeleteProvider,
    cancelDeleteProvider,
    handleTestProvider,
    handleSetDefault,
    toggleProviderExpanded,
  } = useProviderManagement();

  const { data: allModels } = useAllProviderModels();

  const defaultProviderInfo = useMemo(() => {
    if (!deleteConfirmState) return undefined;
    
    const currentDefault = providers.find(p => p.is_default);
    
    if (currentDefault?.id === deleteConfirmState.providerId) {
      const ollamaProvider = providers.find(p => p.id === 'ollama-default');
      if (ollamaProvider) {
        const ollamaModels = allModels?.filter(m => m.provider_id === 'ollama-default') ?? [];
        const firstModel = ollamaModels[0];
        return {
          id: 'ollama-default',
          name: 'Ollama',
          model: firstModel?.id || 'llama3.2:1b',
        };
      }
      return {
        id: 'ollama-default',
        name: 'Ollama',
        model: 'llama3.2:1b',
      };
    }
    
    if (!currentDefault) return undefined;

    const providerModels = allModels?.filter(m => m.provider_id === currentDefault.id) ?? [];
    const firstModel = providerModels[0];

    return {
      id: currentDefault.id,
      name: currentDefault.name || currentDefault.type,
      model: firstModel?.id || 'llama3.2:1b',
    };
  }, [providers, allModels, deleteConfirmState]);

  useEffect(() => {
    if (!open && hasDeletedProvider && onProvidersChanged) {
      onProvidersChanged();
      setHasDeletedProvider(false);
    }
  }, [open, hasDeletedProvider, onProvidersChanged, setHasDeletedProvider]);

  const confirmDeleteAll = () => {
    onDeleteAllConversations();
    onOpenChange(false);
    setShowDeleteConfirm(false);
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-background/95 backdrop-blur-xl border border-border/50 rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] overflow-y-auto z-50 p-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <Dialog.Title className="text-xl font-semibold">Conversation Settings</Dialog.Title>
              <Dialog.Description className="text-sm text-muted-foreground mt-1">
                Configure models, providers, and conversation preferences
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <button
                className="p-2 rounded-md hover:bg-accent transition-colors"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </Dialog.Close>
          </div>

          <Tabs.Root defaultValue="providers" className="w-full">
            <Tabs.List className="flex gap-2 border-b border-border mb-6">
              <Tabs.Trigger
                value="providers"
                className="px-4 py-2 text-sm font-medium border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:text-primary transition-colors"
              >
                <Settings className="h-4 w-4 inline mr-2" />
                Providers
              </Tabs.Trigger>
              <Tabs.Trigger
                value="danger"
                className="px-4 py-2 text-sm font-medium border-b-2 border-transparent data-[state=active]:border-destructive data-[state=active]:text-destructive transition-colors"
              >
                <Trash2 className="h-4 w-4 inline mr-2" />
                Danger Zone
              </Tabs.Trigger>
            </Tabs.List>

            <ProvidersTabWrapper
              providers={providers}
              isLoading={providersLoading}
              showAddForm={showAddForm}
              formState={formState}
              providerError={providerError}
              isSubmitting={isSubmitting}
              expandedProviders={expandedProviders}
              testingProviders={testingProviders}
              testResults={testResults}
              isSettingDefault={isSettingDefault}
              onFormUpdate={updateField}
              onShowAddForm={handleShowAddForm}
              onHideAddForm={handleHideAddForm}
              onSubmitProvider={() => void handleAddProvider()}
              onToggleExpand={toggleProviderExpanded}
              onSetDefault={(id) => void handleSetDefault(id)}
              onTestProvider={(id) => void handleTestProvider(id)}
              onDeleteProvider={(id) => void handleDeleteProvider(id)}
            />

            <DangerZoneTab onDeleteAll={() => setShowDeleteConfirm(true)} />
          </Tabs.Root>

          {showDeleteConfirm && (
            <DeleteConfirmDialog
              onConfirm={confirmDeleteAll}
              onCancel={() => setShowDeleteConfirm(false)}
            />
          )}

          {deleteConfirmState && (
            <ProviderDeleteConfirmDialog
              isOpen
              providerId={deleteConfirmState.providerId}
              conversationCount={deleteConfirmState.conversationCount}
              sampleConversations={deleteConfirmState.sampleConversations}
              defaultProvider={defaultProviderInfo}
              isDeleting={isDeleting}
              onConfirm={confirmDeleteProvider}
              onCancel={cancelDeleteProvider}
            />
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};