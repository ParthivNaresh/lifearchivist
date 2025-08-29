import React from 'react';
import { Server, Database, Shield, Palette } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

const SettingsPage: React.FC = () => {
  const { theme, setTheme, resolvedTheme } = useTheme();

  const handleThemeChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setTheme(event.target.value as 'light' | 'dark' | 'system');
  };

  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-6">Settings</h1>
        
        <div className="space-y-8">
          {/* Server Settings */}
          <div className="bg-card rounded-lg border p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Server className="h-6 w-6 text-primary" />
              <h2 className="text-lg font-semibold">Server Configuration</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Server URL</label>
                <input
                  type="text"
                  defaultValue="http://localhost:8000"
                  className="w-full px-3 py-2 border border-input rounded-md bg-background"
                />
              </div>
              
              <div className="flex items-center space-x-2">
                <div className="h-3 w-3 bg-green-500 rounded-full"></div>
                <span className="text-sm text-muted-foreground">Connected</span>
              </div>
            </div>
          </div>

          {/* Storage Settings */}
          <div className="bg-card rounded-lg border p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Database className="h-6 w-6 text-primary" />
              <h2 className="text-lg font-semibold">Storage</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Vault Directory</label>
                <div className="flex space-x-2">
                  <input
                    type="text"
                    defaultValue="~/.lifearchivist/vault"
                    className="flex-1 px-3 py-2 border border-input rounded-md bg-background"
                    readOnly
                  />
                  <button className="px-4 py-2 border border-input rounded-md hover:bg-accent">
                    Browse
                  </button>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Documents:</span>
                  <span className="ml-2 font-medium">1,234</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Storage Used:</span>
                  <span className="ml-2 font-medium">2.3 GB</span>
                </div>
              </div>
            </div>
          </div>

          {/* Privacy Settings */}
          <div className="bg-card rounded-lg border p-6">
            <div className="flex items-center space-x-3 mb-4">
              <Shield className="h-6 w-6 text-primary" />
              <h2 className="text-lg font-semibold">Privacy & Security</h2>
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Local-only mode</p>
                  <p className="text-sm text-muted-foreground">
                    Keep all data processing local, no cloud services
                  </p>
                </div>
                <input type="checkbox" defaultChecked className="toggle" />
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Encrypt vault</p>
                  <p className="text-sm text-muted-foreground">
                    Encrypt stored documents with your passphrase
                  </p>
                </div>
                <input type="checkbox" className="toggle" />
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Telemetry</p>
                  <p className="text-sm text-muted-foreground">
                    Send anonymous usage data to improve the product
                  </p>
                </div>
                <input type="checkbox" className="toggle" />
              </div>
            </div>
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
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;