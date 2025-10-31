/**
 * Custom hooks for SettingsPage
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useTheme } from '../../contexts/useTheme';
import { type Settings, type SettingKey } from './types';
import { fetchSettings, saveSettingsToServer } from './api';
import { UI_TEXT } from './constants';

/**
 * Hook to manage all settings data and loading state
 */
export const useSettingsData = () => {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [originalSettings, setOriginalSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await fetchSettings();
        setSettings(data);
        setOriginalSettings(data);
      } catch (error) {
        console.error('Failed to fetch settings:', error);
      } finally {
        setLoading(false);
      }
    };

    void loadData();
  }, []);

  return {
    settings,
    originalSettings,
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

  const handleSettingChange = useCallback(
    (key: SettingKey, value: unknown) => {
      if (settings) {
        console.log(`Setting changed: ${key} = ${String(value)}`);
        setSettings({ ...settings, [key]: value as Settings[SettingKey] });
      }
    },
    [settings, setSettings]
  );

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

  const handleThemeChange = useCallback(
    (newTheme: 'light' | 'dark' | 'system') => {
      setTheme(newTheme);

      // Also update the settings state
      if (settings) {
        setSettings({ ...settings, theme: newTheme });
      }
    },
    [settings, setSettings, setTheme]
  );

  return {
    theme,
    resolvedTheme,
    handleThemeChange,
  };
};
