import {
  useSettingsData,
  useSettingsManager,
  useThemeSettings,
  SettingsHeader,
  AppearanceSection,
  LoadingState,
} from './SettingsPage/index';

const SettingsPage: React.FC = () => {
  // Use custom hooks for data management
  const { settings, originalSettings, loading, setSettings, setOriginalSettings } =
    useSettingsData();

  // Use settings manager hook
  const { saving, saveMessage, hasUnsavedChanges, handleSettingChange, saveSettings } =
    useSettingsManager(settings, originalSettings, setSettings, setOriginalSettings);

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
          onSave={() => void saveSettings()}
        />

        <div className="space-y-8">
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
