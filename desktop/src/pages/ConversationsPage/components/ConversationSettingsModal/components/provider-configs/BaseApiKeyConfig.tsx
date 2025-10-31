import { ExternalLink } from 'lucide-react';
import type { ProviderConfigProps } from './types';

interface BaseApiKeyConfigProps extends ProviderConfigProps {
  providerName: string;
  apiKeyPlaceholder: string;
  helpUrl: string;
  helpText?: string;
  showOrganization?: boolean;
}

export const BaseApiKeyConfig: React.FC<BaseApiKeyConfigProps> = ({
  apiKey,
  organization,
  onApiKeyChange,
  onOrganizationChange,
  providerName: _providerName,
  apiKeyPlaceholder,
  helpUrl,
  helpText,
  showOrganization = false,
}) => {
  return (
    <>
      <div>
        <label className="block text-sm font-medium mb-2">
          API Key
          <span className="text-destructive ml-1">*</span>
          <a
            href={helpUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-2 text-xs text-primary hover:underline inline-flex items-center gap-1"
          >
            Get API key
            <ExternalLink className="h-3 w-3" />
          </a>
        </label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => onApiKeyChange(e.target.value)}
          placeholder={apiKeyPlaceholder}
          className="w-full px-3 py-2 border border-input rounded-md bg-background/50 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-primary/50 font-mono text-sm"
        />
        {helpText && <p className="text-xs text-muted-foreground mt-2">{helpText}</p>}
      </div>

      {showOrganization && (
        <div>
          <label className="block text-sm font-medium mb-2 text-muted-foreground">
            Organization ID (Optional)
          </label>
          <input
            type="text"
            value={organization}
            onChange={(e) => onOrganizationChange?.(e.target.value)}
            placeholder="org-..."
            className="w-full px-3 py-2 border border-input rounded-md bg-background/50 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
        </div>
      )}
    </>
  );
};
