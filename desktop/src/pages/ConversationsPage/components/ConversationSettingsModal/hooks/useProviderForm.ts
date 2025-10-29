import { useState, useCallback, useEffect } from 'react';
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

const initialState: ProviderFormState = {
  providerType: 'openai',
  providerId: '',
  apiKey: '',
  organization: '',
  baseUrl: '',
  projectId: '',
  location: 'us-central1',
  setAsDefault: false,
};

export const useProviderForm = () => {
  const [formState, setFormState] = useState<ProviderFormState>(initialState);

  useEffect(() => {
    if (formState.providerType === 'ollama' && !formState.baseUrl) {
      setFormState(prev => ({ ...prev, baseUrl: 'http://localhost:11434' }));
    }
  }, [formState.providerType, formState.baseUrl]);

  const updateField = useCallback(<K extends keyof ProviderFormState>(
    field: K,
    value: ProviderFormState[K]
  ) => {
    setFormState(prev => ({ ...prev, [field]: value }));
  }, []);

  const resetForm = useCallback(() => {
    setFormState(initialState);
  }, []);

  return {
    formState,
    updateField,
    resetForm,
  };
};