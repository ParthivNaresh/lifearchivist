import React, { useState, useEffect } from 'react';
import { 
  Palette, 
  FileText, 
  Brain, 
  FolderOpen, 
  Activity,
  CheckCircle,
  AlertCircle,
  Clock,
  HardDrive,
  Database,
  Save,
  RefreshCw
} from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import axios from 'axios';

interface SystemHealth {
  status: string;
  vault: boolean;
  llamaindex: boolean;
  agents_enabled: boolean;
  websockets_enabled: boolean;
  ui_enabled: boolean;
}

interface VaultStats {
  total_files: number;
  total_size_mb: number;
  vault_path: string;
}

interface Settings {
  auto_extract_dates: boolean;
  generate_text_previews: boolean;
  max_file_size_mb: number;
  llm_model: string;
  embedding_model: string;
  search_results_limit: number;
  auto_organize_by_date: boolean;
  duplicate_detection: boolean;
  default_import_location: string;
  theme: string;
  interface_density: string;
  vault_path: string;
  lifearch_home: string;
}

interface ModelInfo {
  id: string;
  name: string;
  description: string;
  size?: string;
  dimensions?: number;
  performance: string;
}

interface AvailableModels {
  llm_models: ModelInfo[];
  embedding_models: ModelInfo[];
}

const SettingsPage: React.FC = () => {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [vaultStats, setVaultStats] = useState<VaultStats | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [availableModels, setAvailableModels] = useState<AvailableModels | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [originalSettings, setOriginalSettings] = useState<Settings | null>(null);

  const handleThemeChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const newTheme = event.target.value as 'light' | 'dark' | 'system';
    setTheme(newTheme);
    
    // Also update the settings state
    if (settings) {
      setSettings({ ...settings, theme: newTheme });
    }
  };

  const handleSettingChange = (key: keyof Settings, value: any) => {
    if (settings) {
      console.log(`Setting changed: ${key} = ${value}`);
      setSettings({ ...settings, [key]: value });
    }
  };

  const saveSettings = async () => {
    if (!settings) return;
    
    setSaving(true);
    setSaveMessage(null);
    
    try {
      const updateData = {
        auto_extract_dates: settings.auto_extract_dates,
        generate_text_previews: settings.generate_text_previews,
        max_file_size_mb: settings.max_file_size_mb,
        llm_model: settings.llm_model,
        embedding_model: settings.embedding_model,
        search_results_limit: settings.search_results_limit,
        auto_organize_by_date: settings.auto_organize_by_date,
        duplicate_detection: settings.duplicate_detection,
        default_import_location: settings.default_import_location,
        theme: settings.theme,
        interface_density: settings.interface_density,
      };

      const response = await axios.put('http://localhost:8000/api/settings', updateData);
      
      if (response.data.success) {
        setSaveMessage('Settings saved successfully!');
        setTimeout(() => setSaveMessage(null), 3000);
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
      setSaveMessage('Failed to save settings. Please try again.');
      setTimeout(() => setSaveMessage(null), 5000);
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    const fetchAllData = async () => {
      try {
        const [healthResponse, vaultResponse, settingsResponse, modelsResponse] = await Promise.all([
          axios.get<SystemHealth>('http://localhost:8000/health'),
          axios.get<VaultStats>('http://localhost:8000/api/vault/info'),
          axios.get<Settings>('http://localhost:8000/api/settings'),
          axios.get<AvailableModels>('http://localhost:8000/api/settings/models')
        ]);
        
        setSystemHealth(healthResponse.data);
        setVaultStats(vaultResponse.data);
        setSettings(settingsResponse.data);
        setAvailableModels(modelsResponse.data);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAllData();
  }, []);

  const getStatusIcon = (status: boolean) => {
    return status ? (
      <CheckCircle className="h-4 w-4 text-green-500" />
    ) : (
      <AlertCircle className="h-4 w-4 text-red-500" />
    );
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <Clock className="h-8 w-8 animate-spin mx-auto mb-2" />
              <p className="text-muted-foreground">Loading settings...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Settings</h1>
          
          {/* Save Button */}
          <div className="flex items-center space-x-3">
            {saveMessage && (
              <span className={`text-sm ${saveMessage.includes('success') ? 'text-green-600' : 'text-red-600'}`}>
                {saveMessage}
              </span>
            )}
            <button
              onClick={saveSettings}
              disabled={saving}
              className="flex items-center space-x-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              {saving ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              <span>{saving ? 'Saving...' : 'Save Settings'}</span>
            </button>
          </div>
        </div>
        
        <div className="space-y-8">
          {/* Document Processing Settings */}
          <div className="bg-card rounded-lg border p-6">
            <div className="flex items-center space-x-3 mb-4">
              <FileText className="h-6 w-6 text-primary" />
              <h2 className="text-lg font-semibold">Document Processing</h2>
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Auto-extract dates</p>
                  <p className="text-sm text-muted-foreground">
                    Automatically detect and extract document dates using AI
                  </p>
                </div>
                <input 
                  type="checkbox" 
                  checked={settings?.auto_extract_dates || false}
                  onChange={(e) => handleSettingChange('auto_extract_dates', e.target.checked)}
                  className="toggle" 
                />
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Generate text previews</p>
                  <p className="text-sm text-muted-foreground">
                    Create searchable text previews for documents
                  </p>
                </div>
                <input 
                  type="checkbox" 
                  checked={settings?.generate_text_previews || false}
                  onChange={(e) => handleSettingChange('generate_text_previews', e.target.checked)}
                  className="toggle" 
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Maximum file size (MB)</label>
                <select 
                  value={settings?.max_file_size_mb || 100}
                  onChange={(e) => handleSettingChange('max_file_size_mb', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background"
                >
                  <option value="50">50 MB</option>
                  <option value="100">100 MB</option>
                  <option value="200">200 MB</option>
                  <option value="500">500 MB</option>
                </select>
              </div>
            </div>
          </div>

          {/* Search & AI Settings */}
          <div className="bg-card rounded-lg border p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Brain className="h-6 w-6 text-primary" />
              <h2 className="text-lg font-semibold">Search & AI</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Language Model</label>
                <select 
                  value={settings?.llm_model || 'llama3.2:1b'}
                  onChange={(e) => handleSettingChange('llm_model', e.target.value)}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background"
                >
                  {availableModels?.llm_models.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name} ({model.performance})
                    </option>
                  ))}
                </select>
                <p className="text-xs text-muted-foreground mt-1">
                  Used for date extraction and document analysis
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Embedding Model</label>
                <select 
                  value={settings?.embedding_model || 'all-MiniLM-L6-v2'}
                  onChange={(e) => handleSettingChange('embedding_model', e.target.value)}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background"
                >
                  {availableModels?.embedding_models.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name} ({model.performance})
                    </option>
                  ))}
                </select>
                <p className="text-xs text-muted-foreground mt-1">
                  Used for semantic search and document similarity
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Search results limit</label>
                <select 
                  value={settings?.search_results_limit || 25}
                  onChange={(e) => handleSettingChange('search_results_limit', parseInt(e.target.value))}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background"
                >
                  <option value="10">10 results</option>
                  <option value="25">25 results</option>
                  <option value="50">50 results</option>
                  <option value="100">100 results</option>
                </select>
              </div>
            </div>
          </div>

          {/* File Management Settings */}
          <div className="bg-card rounded-lg border p-6">
            <div className="flex items-center space-x-3 mb-4">
              <FolderOpen className="h-6 w-6 text-primary" />
              <h2 className="text-lg font-semibold">File Management</h2>
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Auto-organize by date</p>
                  <p className="text-sm text-muted-foreground">
                    Automatically organize documents by extracted dates
                  </p>
                </div>
                <input 
                  type="checkbox" 
                  checked={settings?.auto_organize_by_date || false}
                  onChange={(e) => handleSettingChange('auto_organize_by_date', e.target.checked)}
                  className="toggle" 
                />
              </div>

              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Duplicate detection</p>
                  <p className="text-sm text-muted-foreground">
                    Skip importing files that already exist in your vault
                  </p>
                </div>
                <input 
                  type="checkbox" 
                  checked={settings?.duplicate_detection || false}
                  onChange={(e) => handleSettingChange('duplicate_detection', e.target.checked)}
                  className="toggle" 
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Default import location</label>
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={settings?.default_import_location || '~/Documents'}
                    onChange={(e) => handleSettingChange('default_import_location', e.target.value)}
                    className="flex-1 px-3 py-2 border border-input rounded-md bg-background"
                  />
                  <button className="px-4 py-2 border border-input rounded-md hover:bg-accent">
                    Browse
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* System Status */}
          <div className="bg-card rounded-lg border p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Activity className="h-6 w-6 text-primary" />
              <h2 className="text-lg font-semibold">System Status</h2>
            </div>
            
            {loading ? (
              <div className="flex items-center space-x-2">
                <Clock className="h-4 w-4 animate-spin" />
                <span className="text-sm text-muted-foreground">Loading system status...</span>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-md">
                    <div className="flex items-center space-x-2">
                      <HardDrive className="h-4 w-4" />
                      <span className="text-sm font-medium">Vault</span>
                    </div>
                    {getStatusIcon(systemHealth?.vault || false)}
                  </div>
                  
                  <div className="flex items-center justify-between p-3 bg-muted/30 rounded-md">
                    <div className="flex items-center space-x-2">
                      <Database className="h-4 w-4" />
                      <span className="text-sm font-medium">LlamaIndex</span>
                    </div>
                    {getStatusIcon(systemHealth?.llamaindex || false)}
                  </div>
                </div>

                {vaultStats && (
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Documents:</span>
                      <span className="ml-2 font-medium">{vaultStats.total_files.toLocaleString()}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Storage Used:</span>
                      <span className="ml-2 font-medium">{vaultStats.total_size_mb.toFixed(1)} MB</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Status:</span>
                      <span className="ml-2 font-medium text-green-600">Healthy</span>
                    </div>
                  </div>
                )}

                <div className="pt-2 border-t">
                  <p className="text-xs text-muted-foreground">
                    Vault location: {vaultStats?.vault_path || '~/.lifearchivist/vault'}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Appearance Settings */}
          <div className="bg-card rounded-lg border p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Palette className="h-6 w-6 text-primary" />
              <h2 className="text-lg font-semibold">Appearance</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Theme</label>
                <select 
                  value={theme}
                  onChange={handleThemeChange}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background transition-colors"
                >
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                  <option value="system">System</option>
                </select>
                <p className="text-xs text-muted-foreground mt-1">
                  Current theme: {resolvedTheme === 'dark' ? 'Dark' : 'Light'}
                  {theme === 'system' && ' (following system preference)'}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Interface density</label>
                <select 
                  value={settings?.interface_density || 'comfortable'}
                  onChange={(e) => handleSettingChange('interface_density', e.target.value)}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background"
                >
                  <option value="compact">Compact</option>
                  <option value="comfortable">Comfortable</option>
                  <option value="spacious">Spacious</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;