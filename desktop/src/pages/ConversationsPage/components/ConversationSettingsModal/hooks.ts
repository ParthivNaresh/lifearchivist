import { useState, useEffect } from 'react';
import { settingsApi } from './api';
import type { AvailableModels } from './types';

export const useModelSettings = (open: boolean) => {
  const [availableModels, setAvailableModels] = useState<AvailableModels | null>(null);
  const [currentModel, setCurrentModel] = useState<string>('llama3.2:1b');
  const [saving, setSaving] = useState(false);
  const [modelError, setModelError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      Promise.all([settingsApi.getModels(), settingsApi.getSettings()])
        .then(([modelsRes, settingsRes]) => {
          setAvailableModels(modelsRes.data);
          setCurrentModel(settingsRes.data.llm_model || 'llama3.2:1b');
        })
        .catch((err) => {
          console.error('Failed to fetch models:', err);
          setModelError('Failed to load models');
        });
    }
  }, [open]);

  const handleModelChange = async (newModel: string) => {
    setSaving(true);
    setModelError(null);
    try {
      await settingsApi.updateModel(newModel);
      setCurrentModel(newModel);
    } catch (err) {
      console.error('Failed to update model:', err);
      setModelError('Failed to update model. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return {
    availableModels,
    currentModel,
    saving,
    modelError,
    handleModelChange,
  };
};

export const useProviderTestResults = () => {
  const [testResults, setTestResults] = useState<
    Record<string, { success: boolean; message: string; isExiting?: boolean } | null>
  >({});
  const [testingProviders, setTestingProviders] = useState<Record<string, boolean>>({});

  const setTestResult = (
    providerId: string,
    result: { success: boolean; message: string; isExiting?: boolean } | null
  ) => {
    setTestResults((prev) => ({ ...prev, [providerId]: result }));
  };

  const setTesting = (providerId: string, isTesting: boolean) => {
    setTestingProviders((prev) => ({ ...prev, [providerId]: isTesting }));
  };

  const clearTestResult = (providerId: string) => {
    setTestResults((prev) => {
      const newResults = { ...prev };
      delete newResults[providerId];
      return newResults;
    });
  };

  const startTestCooldown = (providerId: string) => {
    setTimeout(() => {
      setTestingProviders((prev) => {
        const newState = { ...prev };
        delete newState[providerId];
        return newState;
      });
    }, 3000);
  };

  return {
    testResults,
    testingProviders,
    setTestResult,
    setTesting,
    clearTestResult,
    startTestCooldown,
  };
};
