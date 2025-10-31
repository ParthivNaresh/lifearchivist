import { useState, useCallback } from 'react';
import type { ProviderType } from '../../../providers-types';

export interface ProviderFormState {
  providerType: ProviderType;
  providerId: string;
  apiKey: string;
  organization: string;
  baseUrl: string;
  projectId: string;
  location: string;
  setAsDefault: boolean;
}

const getInitialState = (): ProviderFormState => ({
  providerType: 'openai',
  providerId: '',
  apiKey: '',
  organization: '',
  baseUrl: '',
  projectId: '',
  location: 'us-central1',
  setAsDefault: false,
});

const getDefaultBaseUrl = (providerType: ProviderType): string => {
  switch (providerType) {
    case 'ollama':
      return 'http://localhost:11434';
    default:
      return '';
  }
};

export const useProviderForm = () => {
  const [formState, setFormState] = useState<ProviderFormState>(getInitialState);

  const updateField = useCallback(
    <K extends keyof ProviderFormState>(field: K, value: ProviderFormState[K]) => {
      setFormState((prev) => {
        const newState = { ...prev, [field]: value };

        if (field === 'providerType' && value !== prev.providerType) {
          const providerType = value as ProviderType;
          const defaultBaseUrl = getDefaultBaseUrl(providerType);

          if (defaultBaseUrl && !prev.baseUrl) {
            newState.baseUrl = defaultBaseUrl;
          }

          if (providerType === 'ollama') {
            newState.apiKey = '';
            newState.organization = '';
            newState.projectId = '';
          } else if (prev.providerType === 'ollama') {
            newState.baseUrl = '';
          }
        }

        return newState;
      });
    },
    []
  );

  const resetForm = useCallback(() => {
    setFormState(getInitialState());
  }, []);

  return {
    formState,
    updateField,
    resetForm,
  };
};
