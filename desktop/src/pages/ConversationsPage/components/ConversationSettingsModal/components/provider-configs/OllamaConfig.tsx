import type { ProviderConfigProps } from './types';

export const OllamaConfig: React.FC<ProviderConfigProps> = ({ baseUrl, onBaseUrlChange }) => {
  return (
    <>
      <div>
        <label className="block text-sm font-medium mb-2">
          Base URL
          <span className="text-destructive ml-1">*</span>
        </label>
        <input
          type="text"
          value={baseUrl}
          onChange={(e) => onBaseUrlChange?.(e.target.value)}
          placeholder="http://localhost:11434"
          className="w-full px-3 py-2 border border-input rounded-md bg-background/50 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
        />
        <p className="text-xs text-muted-foreground mt-2">
          Make sure Ollama is running locally before adding this provider
        </p>
      </div>

      <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-md">
        <p className="text-sm text-blue-600 dark:text-blue-400">
          <strong>Note:</strong> Ollama runs locally and doesn&apos;t require an API key. Models are
          downloaded and stored on your machine.
        </p>
      </div>
    </>
  );
};
