import { useState, useCallback } from 'react';
import {
  useProviders,
  useAddProvider,
  useDeleteProvider,
  useTestProvider,
  useSetDefaultProvider,
} from '../../../providers-hooks';
import { useProviderForm } from './useProviderForm';
import { useProviderTestResults } from '../hooks';
import { validateProviderForm, buildProviderConfig, ProviderValidationError } from '../services/providerService';

export const useProviderManagement = () => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [providerError, setProviderError] = useState<string | null>(null);
  const [expandedProviders, setExpandedProviders] = useState<Record<string, boolean>>({});

  const { formState, updateField, resetForm } = useProviderForm();
  const {
    testResults,
    testingProviders,
    setTestResult,
    setTesting,
    clearTestResult,
    startTestCooldown,
  } = useProviderTestResults();

  const { data: providersData, isLoading: providersLoading } = useProviders();
  const addProviderMutation = useAddProvider();
  const deleteProviderMutation = useDeleteProvider();
  const testProviderMutation = useTestProvider();
  const setDefaultMutation = useSetDefaultProvider();

  const handleShowAddForm = useCallback(() => {
    setShowAddForm(true);
    setProviderError(null);
  }, []);

  const handleHideAddForm = useCallback(() => {
    setShowAddForm(false);
    resetForm();
    setProviderError(null);
  }, [resetForm]);

  const handleAddProvider = useCallback(async () => {
    setProviderError(null);

    try {
      validateProviderForm(formState);
      const request = buildProviderConfig(formState);
      
      await addProviderMutation.mutateAsync(request);
      resetForm();
      setShowAddForm(false);
    } catch (err) {
      if (err instanceof ProviderValidationError) {
        setProviderError(err.message);
      } else if (err instanceof Error) {
        setProviderError(err.message);
      } else {
        setProviderError('Failed to add provider');
      }
    }
  }, [formState, addProviderMutation, resetForm]);

  const handleDeleteProvider = useCallback(async (providerId: string) => {
    setProviderError(null);
    clearTestResult(providerId);

    try {
      await deleteProviderMutation.mutateAsync(providerId);
    } catch (err) {
      setProviderError(err instanceof Error ? err.message : 'Failed to delete provider');
    }
  }, [deleteProviderMutation, clearTestResult]);

  const handleTestProvider = useCallback(async (providerId: string) => {
    if (testingProviders[providerId]) {
      return;
    }

    setProviderError(null);
    setTestResult(providerId, null);
    setTesting(providerId, true);

    try {
      const result = await testProviderMutation.mutateAsync(providerId);
      setTestResult(providerId, { success: result.is_valid, message: result.message });

      if (result.is_valid) {
        setTimeout(() => {
          setTestResult(providerId, { success: true, message: result.message, isExiting: true });
          setTimeout(() => clearTestResult(providerId), 300);
        }, 2700);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Connection test failed';
      setTestResult(providerId, { success: false, message: errorMessage });
    } finally {
      startTestCooldown(providerId);
    }
  }, [testingProviders, testProviderMutation, setTestResult, setTesting, clearTestResult, startTestCooldown]);

  const handleSetDefault = useCallback(async (providerId: string) => {
    setProviderError(null);
    try {
      await setDefaultMutation.mutateAsync(providerId);
    } catch (err) {
      setProviderError(err instanceof Error ? err.message : 'Failed to set default provider');
    }
  }, [setDefaultMutation]);

  const toggleProviderExpanded = useCallback((providerId: string) => {
    setExpandedProviders(prev => ({ ...prev, [providerId]: !prev[providerId] }));
  }, []);

  return {
    providers: providersData?.providers ?? [],
    providersLoading,
    showAddForm,
    formState,
    providerError,
    expandedProviders,
    testResults,
    testingProviders,
    isSubmitting: addProviderMutation.isPending,
    isSettingDefault: setDefaultMutation.isPending,
    updateField,
    handleShowAddForm,
    handleHideAddForm,
    handleAddProvider,
    handleDeleteProvider,
    handleTestProvider,
    handleSetDefault,
    toggleProviderExpanded,
  };
};