import { useState, useEffect } from 'react';
import { Sliders, Zap, MessageSquare, History, Clock, Loader2 } from 'lucide-react';
import { settingsApi } from '../api';
import type { SettingsResponse, SettingsUpdateRequest } from '../types';

interface AdvancedSettings {
  temperature: number;
  maxOutputTokens: number;
  responseFormat: 'verbose' | 'concise';
  contextWindowSize: number;
  responseTimeout: number;
}

export const AdvancedSettingsTab: React.FC = () => {
  const [settings, setSettings] = useState<AdvancedSettings>({
    temperature: 0.7,
    maxOutputTokens: 2048,
    responseFormat: 'concise',
    contextWindowSize: 10,
    responseTimeout: 30,
  });

  const [tempInput, setTempInput] = useState(settings.temperature.toFixed(2));
  const [tokensInput, setTokensInput] = useState(settings.maxOutputTokens.toString());
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    void fetchSettings();
  }, []);

  const fetchSettings = async (): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await settingsApi.getSettings();
      const data: SettingsResponse = response.data;

      const newSettings: AdvancedSettings = {
        temperature: data.temperature,
        maxOutputTokens: data.max_output_tokens,
        responseFormat: data.response_format,
        contextWindowSize: data.context_window_size,
        responseTimeout: data.response_timeout,
      };

      setSettings(newSettings);
      setTempInput(newSettings.temperature.toFixed(2));
      setTokensInput(newSettings.maxOutputTokens.toString());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setIsLoading(false);
    }
  };

  const saveSettings = async (): Promise<void> => {
    try {
      setIsSaving(true);
      setError(null);
      setSuccessMessage(null);

      const updateRequest: SettingsUpdateRequest = {
        temperature: settings.temperature,
        max_output_tokens: settings.maxOutputTokens,
        response_format: settings.responseFormat,
        context_window_size: settings.contextWindowSize,
        response_timeout: settings.responseTimeout,
      };

      await settingsApi.updateSettings(updateRequest);

      setSuccessMessage('Settings saved successfully');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  const handleTemperatureChange = (value: number) => {
    const clampedValue = Math.max(0, Math.min(2, value));
    setSettings((prev) => ({ ...prev, temperature: clampedValue }));
    setTempInput(clampedValue.toFixed(2));
  };

  const handleTemperatureInputChange = (value: string) => {
    setTempInput(value);
    const num = parseFloat(value);
    if (!isNaN(num) && num >= 0 && num <= 2) {
      setSettings((prev) => ({ ...prev, temperature: num }));
    }
  };

  const handleTemperatureInputBlur = () => {
    const num = parseFloat(tempInput);
    if (isNaN(num) || num < 0 || num > 2) {
      setTempInput(settings.temperature.toFixed(2));
    } else {
      handleTemperatureChange(num);
    }
  };

  const handleMaxTokensChange = (value: number) => {
    const clampedValue = Math.max(1, value);
    setSettings((prev) => ({ ...prev, maxOutputTokens: clampedValue }));
    setTokensInput(clampedValue.toString());
  };

  const handleMaxTokensInputChange = (value: string) => {
    setTokensInput(value);
    const num = parseInt(value, 10);
    if (!isNaN(num) && num > 0) {
      setSettings((prev) => ({ ...prev, maxOutputTokens: num }));
    }
  };

  const handleMaxTokensInputBlur = () => {
    const num = parseInt(tokensInput, 10);
    if (isNaN(num) || num <= 0) {
      setTokensInput(settings.maxOutputTokens.toString());
    } else {
      handleMaxTokensChange(num);
    }
  };

  const handleResponseFormatChange = (format: 'verbose' | 'concise') => {
    setSettings((prev) => ({ ...prev, responseFormat: format }));
  };

  const handleContextWindowChange = (value: string) => {
    const num = parseInt(value, 10);
    if (!isNaN(num) && num >= 0) {
      setSettings((prev) => ({ ...prev, contextWindowSize: num }));
    }
  };

  const handleTimeoutChange = (value: string) => {
    const num = parseInt(value, 10);
    if (!isNaN(num) && num > 0) {
      setSettings((prev) => ({ ...prev, responseTimeout: num }));
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6 pr-4">
      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-foreground">Advanced Settings</h3>
        <p className="text-sm text-muted-foreground">
          Fine-tune conversation behavior and performance parameters
        </p>
      </div>

      <div className="space-y-8">
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 backdrop-blur-sm">
              <Sliders className="h-4 w-4 text-primary" />
            </div>
            <div className="flex-1">
              <label className="text-sm font-medium text-foreground">Temperature</label>
              <p className="text-xs text-muted-foreground">
                Controls randomness: 0 = focused, 2 = creative
              </p>
            </div>
            <input
              type="text"
              value={tempInput}
              onChange={(e) => handleTemperatureInputChange(e.target.value)}
              onBlur={handleTemperatureInputBlur}
              className="w-16 text-sm font-mono bg-background/50 px-2 py-1 rounded-md border border-border/50 
                       text-center focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
            />
          </div>
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-pink-500/10 rounded-lg blur-xl" />
            <div className="relative bg-background/40 backdrop-blur-md border border-border/50 rounded-lg p-4">
              <input
                type="range"
                min="0"
                max="2"
                step="0.01"
                value={settings.temperature}
                onChange={(e) => handleTemperatureChange(parseFloat(e.target.value))}
                className="w-full h-2 bg-gradient-to-r from-blue-500 to-pink-500 rounded-lg appearance-none cursor-pointer
                         [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                         [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:shadow-lg
                         [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-primary
                         [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:bg-white
                         [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:shadow-lg [&::-moz-range-thumb]:cursor-pointer
                         [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-primary [&::-moz-range-thumb]:border-none"
              />
              <div className="flex justify-between mt-2">
                <span className="text-xs text-muted-foreground">Focused</span>
                <span className="text-xs text-muted-foreground">Balanced</span>
                <span className="text-xs text-muted-foreground">Creative</span>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 backdrop-blur-sm">
              <Zap className="h-4 w-4 text-primary" />
            </div>
            <div className="flex-1">
              <label className="text-sm font-medium text-foreground">Max Output Tokens</label>
              <p className="text-xs text-muted-foreground">Maximum length of generated responses</p>
            </div>
            <input
              type="text"
              value={tokensInput}
              onChange={(e) => handleMaxTokensInputChange(e.target.value)}
              onBlur={handleMaxTokensInputBlur}
              className="w-20 text-sm font-mono bg-background/50 px-2 py-1 rounded-md border border-border/50 
                       text-center focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
            />
          </div>
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/10 via-teal-500/10 to-cyan-500/10 rounded-lg blur-xl" />
            <div className="relative bg-background/40 backdrop-blur-md border border-border/50 rounded-lg p-4">
              <input
                type="range"
                min="100"
                max="32000"
                step="20"
                value={Math.min(settings.maxOutputTokens, 32000)}
                onChange={(e) => handleMaxTokensChange(parseInt(e.target.value))}
                className="w-full h-2 bg-gradient-to-r from-emerald-500 to-cyan-500 rounded-lg appearance-none cursor-pointer
                         [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                         [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:shadow-lg
                         [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-primary
                         [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:bg-white
                         [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:shadow-lg [&::-moz-range-thumb]:cursor-pointer
                         [&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-primary [&::-moz-range-thumb]:border-none"
              />
              <div className="flex justify-between mt-2">
                <span className="text-xs text-muted-foreground">Short</span>
                <span className="text-xs text-muted-foreground">Medium</span>
                <span className="text-xs text-muted-foreground">Long</span>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-primary/10 backdrop-blur-sm">
              <MessageSquare className="h-4 w-4 text-primary" />
            </div>
            <div>
              <label className="text-sm font-medium text-foreground">Response Format</label>
              <p className="text-xs text-muted-foreground">
                Choose between detailed or concise responses
              </p>
            </div>
          </div>
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-violet-500/10 to-indigo-500/10 rounded-lg blur-xl" />
            <div className="relative bg-background/40 backdrop-blur-md border border-border/50 rounded-lg p-1 flex gap-1">
              <button
                onClick={() => handleResponseFormatChange('concise')}
                className={`flex-1 px-4 py-2.5 rounded-md text-sm font-medium transition-all duration-200
                          ${
                            settings.responseFormat === 'concise'
                              ? 'bg-primary text-primary-foreground shadow-lg'
                              : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
                          }`}
              >
                Concise
              </button>
              <button
                onClick={() => handleResponseFormatChange('verbose')}
                className={`flex-1 px-4 py-2.5 rounded-md text-sm font-medium transition-all duration-200
                          ${
                            settings.responseFormat === 'verbose'
                              ? 'bg-primary text-primary-foreground shadow-lg'
                              : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
                          }`}
              >
                Verbose
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-primary/10 backdrop-blur-sm">
                <History className="h-4 w-4 text-primary" />
              </div>
              <div>
                <label className="text-sm font-medium text-foreground">Context Window</label>
                <p className="text-xs text-muted-foreground">Messages to include</p>
              </div>
            </div>
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-amber-500/10 to-orange-500/10 rounded-lg blur-xl" />
              <div className="relative bg-background/40 backdrop-blur-md border border-border/50 rounded-lg">
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={settings.contextWindowSize}
                  onChange={(e) => handleContextWindowChange(e.target.value)}
                  className="w-full px-4 py-2.5 bg-transparent text-sm rounded-lg focus:outline-none focus:ring-2 
                           focus:ring-primary/50 transition-all duration-200"
                  placeholder="10"
                />
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-primary/10 backdrop-blur-sm">
                <Clock className="h-4 w-4 text-primary" />
              </div>
              <div>
                <label className="text-sm font-medium text-foreground">Response Timeout</label>
                <p className="text-xs text-muted-foreground">Seconds to wait</p>
              </div>
            </div>
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-rose-500/10 to-red-500/10 rounded-lg blur-xl" />
              <div className="relative bg-background/40 backdrop-blur-md border border-border/50 rounded-lg">
                <input
                  type="number"
                  min="5"
                  max="120"
                  value={settings.responseTimeout}
                  onChange={(e) => handleTimeoutChange(e.target.value)}
                  className="w-full px-4 py-2.5 bg-transparent text-sm rounded-lg focus:outline-none focus:ring-2 
                           focus:ring-primary/50 transition-all duration-200"
                  placeholder="30"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-border/30 space-y-3">
          {error && (
            <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg text-sm text-destructive">
              {error}
            </div>
          )}
          {successMessage && (
            <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-lg text-sm text-green-500">
              {successMessage}
            </div>
          )}
          <button
            onClick={() => void saveSettings()}
            disabled={isSaving}
            className="w-full px-4 py-2.5 bg-primary text-primary-foreground rounded-lg font-medium
                     hover:bg-primary/90 transition-all duration-200 shadow-lg disabled:opacity-50
                     disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isSaving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              'Save Advanced Settings'
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
