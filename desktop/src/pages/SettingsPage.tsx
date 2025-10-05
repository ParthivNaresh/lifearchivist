import React from 'react';
import {
  useSettingsData,
  useSettingsManager,
  useThemeSettings,
  SettingsHeader,
  DocumentProcessingSection,
  SearchAISection,
  FileManagementSection,
  SystemStatusSection,
  AppearanceSection,
  LoadingState,
} from './SettingsPage/index';

const SettingsPage: React.FC = () => {
  // Use custom hooks for data management
  const {
    systemHealth,
    vaultStats,
    settings,
    originalSettings,
    availableModels,
    loading,
    setSettings,
    setOriginalSettings,
  } = useSettingsData();

  // Use settings manager hook
  const {
    saving,
    saveMessage,
    hasUnsavedChanges,
    handleSettingChange,
    saveSettings,
  } = useSettingsManager(settings, originalSettings, setSettings, setOriginalSettings);

  // Use theme settings hook
  const { theme, resolvedTheme, handleThemeChange } = useThemeSettings(settings, setSettings);

  // Show loading state
  if (loading) {
    return <LoadingState />;
  }

  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <SettingsHeader
          saving={saving}
          saveMessage={saveMessage}
          hasUnsavedChanges={hasUnsavedChanges}
          onSave={saveSettings}
        />
        
        <div className="space-y-8">
          <DocumentProcessingSection
            settings={settings}
            onSettingChange={handleSettingChange}
          />

          <SearchAISection
            settings={settings}
            availableModels={availableModels}
            onSettingChange={handleSettingChange}
          />

          <FileManagementSection
            settings={settings}
            onSettingChange={handleSettingChange}
          />

          <SystemStatusSection
            systemHealth={systemHealth}
            vaultStats={vaultStats}
            loading={loading}
          />

          <AppearanceSection
            settings={settings}
            theme={theme}
            resolvedTheme={resolvedTheme}
            onThemeChange={handleThemeChange}
            onSettingChange={handleSettingChange}
          />
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;