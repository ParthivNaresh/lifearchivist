/**
 * Custom hooks for SettingsPage
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import { 
  SystemHealth, 
  VaultStats, 
  Settings, 
  AvailableModels,
  SettingKey 
} from './types';
import { fetchAllData, saveSettingsToServer } from './api';
import { UI_TEXT } from './constants';

/**
 * Hook to manage all settings data and loading state
 */
export const useSettingsData = () => {
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [vaultStats, setVaultStats] = useState<VaultStats | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [originalSettings, setOriginalSettings] = useState<Settings | null>(null);
  const [availableModels, setAvailableModels] = useState<AvailableModels | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await fetchAllData();
        setSystemHealth(data.systemHealth);
        setVaultStats(data.vaultStats);
        setSettings(data.settings);
        setOriginalSettings(data.settings);
        setAvailableModels(data.availableModels);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  return {
    systemHealth,
    vaultStats,
    settings,
    originalSettings,
    availableModels,
    loading,
    setSettings,
    setOriginalSettings,
  };
};

/**
 * Hook to manage settings changes and saving
 */
export const useSettingsManager = (
  settings: Settings | null,
  originalSettings: Settings | null,
  setSettings: (settings: Settings) => void,
  setOriginalSettings: (settings: Settings) => void
) => {
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const hasUnsavedChanges = useMemo(() => {
    if (!settings || !originalSettings) return false;
    return JSON.stringify(settings) !== JSON.stringify(originalSettings);
  }, [settings, originalSettings]);

  const handleSettingChange = useCallback((key: SettingKey, value: any) => {
    if (settings) {
      console.log(`Setting changed: ${key} = ${value}`);
      setSettings({ ...settings, [key]: value });
    }
  }, [settings, setSettings]);

  const saveSettings = useCallback(async () => {
    if (!settings) return;
    
    setSaving(true);
    setSaveMessage(null);
    
    try {
      const response = await saveSettingsToServer(settings);
      
      if (response.success) {
        setSaveMessage(UI_TEXT.SAVE_SUCCESS);
        setOriginalSettings(settings);
        setTimeout(() => setSaveMessage(null), 3000);
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
      setSaveMessage(UI_TEXT.SAVE_ERROR);
      setTimeout(() => setSaveMessage(null), 5000);
    } finally {
      setSaving(false);
    }
  }, [settings, setOriginalSettings]);

  const resetSettings = useCallback(() => {
    if (originalSettings) {
      setSettings(originalSettings);
    }
  }, [originalSettings, setSettings]);

  return {
    saving,
    saveMessage,
    hasUnsavedChanges,
    handleSettingChange,
    saveSettings,
    resetSettings,
  };
};

/**
 * Hook to manage theme settings
 */
export const useThemeSettings = (
  settings: Settings | null,
  setSettings: (settings: Settings) => void
) => {
  const { theme, setTheme, resolvedTheme } = useTheme();

  const handleThemeChange = useCallback((newTheme: 'light' | 'dark' | 'system') => {
    setTheme(newTheme);
    
    // Also update the settings state
    if (settings) {
      setSettings({ ...settings, theme: newTheme });
    }
  }, [settings, setSettings, setTheme]);

  return {
    theme,
    resolvedTheme,
    handleThemeChange,
  };
};