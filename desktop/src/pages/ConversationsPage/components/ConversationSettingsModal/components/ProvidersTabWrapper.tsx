import React from 'react';
import { ProvidersTab } from './ProvidersTab';
import type { Provider } from '../../../providers-types';
import type { ProviderFormState } from '../hooks/useProviderForm';


interface ProvidersTabWrapperProps {
  providers: Provider[];
  isLoading: boolean;
  showAddForm: boolean;
  formState: ProviderFormState;
  providerError: string | null;
  isSubmitting: boolean;
  expandedProviders: Record<string, boolean>;
  testingProviders: Record<string, boolean>;
  testResults: Record<string, { success: boolean; message: string; isExiting?: boolean } | null>;
  isSettingDefault: boolean;
  onFormUpdate: <K extends keyof ProviderFormState>(field: K, value: ProviderFormState[K]) => void;
  onShowAddForm: () => void;
  onHideAddForm: () => void;
  onSubmitProvider: () => void;
  onToggleExpand: (providerId: string) => void;
  onSetDefault: (providerId: string) => void;
  onTestProvider: (providerId: string) => void;
  onDeleteProvider: (providerId: string) => void;
}

export const ProvidersTabWrapper: React.FC<ProvidersTabWrapperProps> = ({
  providers,
  isLoading,
  showAddForm,
  formState,
  providerError,
  isSubmitting,
  expandedProviders,
  testingProviders,
  testResults,
  isSettingDefault,
  onFormUpdate,
  onShowAddForm,
  onHideAddForm,
  onSubmitProvider,
  onToggleExpand,
  onSetDefault,
  onTestProvider,
  onDeleteProvider,
}) => {
  return (
    <ProvidersTab
      providers={providers}
      isLoading={isLoading}
      showAddForm={showAddForm}
      newProviderType={formState.providerType}
      newProviderId={formState.providerId}
      newProviderApiKey={formState.apiKey}
      newProviderOrg={formState.organization}
      newProviderBaseUrl={formState.baseUrl}
      newProviderProjectId={formState.projectId}
      newProviderLocation={formState.location}
      setAsDefault={formState.setAsDefault}
      providerError={providerError}
      isSubmitting={isSubmitting}
      expandedProviders={expandedProviders}
      testingProviders={testingProviders}
      testResults={testResults}
      isSettingDefault={isSettingDefault}
      onShowAddForm={onShowAddForm}
      onHideAddForm={onHideAddForm}
      onProviderTypeChange={(type) => onFormUpdate('providerType', type)}
      onProviderIdChange={(id) => onFormUpdate('providerId', id)}
      onApiKeyChange={(key) => onFormUpdate('apiKey', key)}
      onOrganizationChange={(org) => onFormUpdate('organization', org)}
      onBaseUrlChange={(url) => onFormUpdate('baseUrl', url)}
      onProjectIdChange={(id) => onFormUpdate('projectId', id)}
      onLocationChange={(location) => onFormUpdate('location', location)}
      onSetAsDefaultChange={(value) => onFormUpdate('setAsDefault', value)}
      onSubmitProvider={onSubmitProvider}
      onToggleExpand={onToggleExpand}
      onSetDefault={onSetDefault}
      onTestProvider={onTestProvider}
      onDeleteProvider={onDeleteProvider}
    />
  );
};