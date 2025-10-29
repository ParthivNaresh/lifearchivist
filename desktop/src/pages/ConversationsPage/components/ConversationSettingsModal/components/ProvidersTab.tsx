import { Plus, Settings, Loader2 } from 'lucide-react';
import * as Tabs from '@radix-ui/react-tabs';
import * as Tooltip from '@radix-ui/react-tooltip';
import { AddProviderForm } from './AddProviderForm';
import { ProviderCard } from './ProviderCard';
import type { Provider, ProviderType } from '../../../providers-types';

interface ProvidersTabProps {
  providers: Provider[];
  isLoading: boolean;
  showAddForm: boolean;
  newProviderType: ProviderType;
  newProviderId: string;
  newProviderApiKey: string;
  newProviderOrg: string;
  newProviderBaseUrl: string;
  newProviderProjectId: string;
  newProviderLocation: string;
  setAsDefault: boolean;
  providerError: string | null;
  isSubmitting: boolean;
  expandedProviders: Record<string, boolean>;
  testingProviders: Record<string, boolean>;
  testResults: Record<string, { success: boolean; message: string; isExiting?: boolean } | null>;
  isSettingDefault: boolean;
  onShowAddForm: () => void;
  onHideAddForm: () => void;
  onProviderTypeChange: (type: ProviderType) => void;
  onProviderIdChange: (id: string) => void;
  onApiKeyChange: (key: string) => void;
  onOrganizationChange: (org: string) => void;
  onBaseUrlChange: (url: string) => void;
  onProjectIdChange: (id: string) => void;
  onLocationChange: (location: string) => void;
  onSetAsDefaultChange: (value: boolean) => void;
  onSubmitProvider: () => void;
  onToggleExpand: (providerId: string) => void;
  onSetDefault: (providerId: string) => void;
  onTestProvider: (providerId: string) => void;
  onDeleteProvider: (providerId: string) => void;
}

export const ProvidersTab: React.FC<ProvidersTabProps> = ({
  providers,
  isLoading,
  showAddForm,
  newProviderType,
  newProviderId,
  newProviderApiKey,
  newProviderOrg,
  newProviderBaseUrl,
  newProviderProjectId,
  newProviderLocation,
  setAsDefault,
  providerError,
  isSubmitting,
  expandedProviders,
  testingProviders,
  testResults,
  isSettingDefault,
  onShowAddForm,
  onHideAddForm,
  onProviderTypeChange,
  onProviderIdChange,
  onApiKeyChange,
  onOrganizationChange,
  onBaseUrlChange,
  onProjectIdChange,
  onLocationChange,
  onSetAsDefaultChange,
  onSubmitProvider,
  onToggleExpand,
  onSetDefault,
  onTestProvider,
  onDeleteProvider,
}) => {
  return (
    <Tabs.Content value="providers" className="space-y-4">
      <div className="bg-card/50 backdrop-blur-sm rounded-lg border border-border/30 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-base font-medium">LLM Providers</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Connect your own API keys to use remote LLM services
            </p>
          </div>
          {!showAddForm && (
            <button
              onClick={onShowAddForm}
              className="flex items-center gap-2 px-4 py-2 text-sm bg-primary/10 text-primary border border-primary/20 rounded-lg hover:bg-primary/20 transition-all backdrop-blur-sm"
            >
              <Plus className="h-4 w-4" />
              Add Provider
            </button>
          )}
        </div>

        {showAddForm ? (
          <AddProviderForm
            providerType={newProviderType}
            providerId={newProviderId}
            apiKey={newProviderApiKey}
            organization={newProviderOrg}
            baseUrl={newProviderBaseUrl}
            projectId={newProviderProjectId}
            location={newProviderLocation}
            setAsDefault={setAsDefault}
            error={providerError}
            isSubmitting={isSubmitting}
            onProviderTypeChange={onProviderTypeChange}
            onProviderIdChange={onProviderIdChange}
            onApiKeyChange={onApiKeyChange}
            onOrganizationChange={onOrganizationChange}
            onBaseUrlChange={onBaseUrlChange}
            onProjectIdChange={onProjectIdChange}
            onLocationChange={onLocationChange}
            onSetAsDefaultChange={onSetAsDefaultChange}
            onSubmit={onSubmitProvider}
            onCancel={onHideAddForm}
          />
        ) : isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : providers.length === 0 ? (
          <div className="text-center py-12">
            <Settings className="h-12 w-12 text-muted-foreground/50 mx-auto mb-3" />
            <p className="text-sm text-muted-foreground">No providers configured yet</p>
            <p className="text-xs text-muted-foreground mt-1">
              Add a provider to connect to remote LLM services
            </p>
          </div>
        ) : (
          <Tooltip.Provider delayDuration={300}>
            <div className="space-y-3">
              {providers.map((provider) => (
                <ProviderCard
                  key={provider.id}
                  provider={provider}
                  isExpanded={expandedProviders[provider.id] ?? false}
                  isTesting={testingProviders[provider.id] ?? false}
                  testResult={testResults[provider.id] ?? null}
                  onToggleExpand={() => onToggleExpand(provider.id)}
                  onSetDefault={() => onSetDefault(provider.id)}
                  onTest={() => onTestProvider(provider.id)}
                  onDelete={() => onDeleteProvider(provider.id)}
                  isSettingDefault={isSettingDefault}
                  isDeletable={provider.id !== 'ollama-default'}
                />
              ))}
            </div>
          </Tooltip.Provider>
        )}
      </div>
    </Tabs.Content>
  );
};
