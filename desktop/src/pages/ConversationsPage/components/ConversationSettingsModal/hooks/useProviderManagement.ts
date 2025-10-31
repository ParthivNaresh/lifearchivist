import { useState, useCallback } from 'react';
import {
  useProviders,
  useAddProvider,
  useDeleteProvider,
  useTestProvider,
  useSetDefaultProvider,
  useCheckProviderUsage,
} from '../../../providers-hooks';
import { useProviderForm } from './useProviderForm';
import { useProviderTestResults } from '../hooks';
import {
  validateProviderForm,
  buildProviderConfig,
  ProviderValidationError,
} from '../services/providerService';

interface DeleteConfirmState {
  providerId: string;
  conversationCount: number;
  sampleConversations: {
    id: string;
    title: string;
    model: string;
  }[];
}

export const useProviderManagement = () => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [providerError, setProviderError] = useState<string | null>(null);
  const [expandedProviders, setExpandedProviders] = useState<Record<string, boolean>>({});
  const [deleteConfirmState, setDeleteConfirmState] = useState<DeleteConfirmState | null>(null);
  const [hasDeletedProvider, setHasDeletedProvider] = useState(false);

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
  const checkUsageMutation = useCheckProviderUsage();

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
      const existingProviderIds = providersData?.providers.map((p) => p.id) ?? [];
      validateProviderForm(formState, existingProviderIds);
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
  }, [formState, addProviderMutation, resetForm, providersData]);

  const handleDeleteProvider = useCallback(
    async (providerId: string) => {
      setProviderError(null);

      try {
        const usage = await checkUsageMutation.mutateAsync(providerId);

        if (usage.conversation_count > 0) {
          setDeleteConfirmState({
            providerId,
            conversationCount: usage.conversation_count,
            sampleConversations: usage.sample_conversations,
          });
        } else {
          clearTestResult(providerId);
          await deleteProviderMutation.mutateAsync({ providerId, updateConversations: false });
        }
      } catch (err) {
        setProviderError(err instanceof Error ? err.message : 'Failed to delete provider');
      }
    },
    [checkUsageMutation, deleteProviderMutation, clearTestResult]
  );

  const confirmDeleteProvider = useCallback(async () => {
    if (!deleteConfirmState) return;

    const { providerId } = deleteConfirmState;
    setProviderError(null);
    clearTestResult(providerId);

    try {
      await deleteProviderMutation.mutateAsync({ providerId, updateConversations: true });
      setDeleteConfirmState(null);
      setHasDeletedProvider(true);
    } catch (err) {
      setProviderError(err instanceof Error ? err.message : 'Failed to delete provider');
    }
  }, [deleteConfirmState, deleteProviderMutation, clearTestResult]);

  const cancelDeleteProvider = useCallback(() => {
    setDeleteConfirmState(null);
  }, []);

  const handleTestProvider = useCallback(
    async (providerId: string) => {
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
    },
    [
      testingProviders,
      testProviderMutation,
      setTestResult,
      setTesting,
      clearTestResult,
      startTestCooldown,
    ]
  );

  const handleSetDefault = useCallback(
    async (providerId: string, defaultModel?: string) => {
      setProviderError(null);
      try {
        await setDefaultMutation.mutateAsync({
          provider_id: providerId,
          default_model: defaultModel,
        });
      } catch (err) {
        setProviderError(err instanceof Error ? err.message : 'Failed to set default provider');
      }
    },
    [setDefaultMutation]
  );

  const toggleProviderExpanded = useCallback((providerId: string) => {
    setExpandedProviders((prev) => ({ ...prev, [providerId]: !prev[providerId] }));
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
    isDeleting: deleteProviderMutation.isPending,
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
  };
};
