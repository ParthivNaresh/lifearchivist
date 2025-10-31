import { X, Check, Loader2, AlertCircle } from 'lucide-react';
import type { ProviderType } from '../../../providers-types';
import { PROVIDER_CONFIGS, PROVIDER_DISPLAY_NAMES } from './provider-configs/registry';

interface AddProviderFormProps {
  providerType: ProviderType;
  providerId: string;
  apiKey: string;
  organization: string;
  baseUrl: string;
  projectId: string;
  location: string;
  setAsDefault: boolean;
  error: string | null;
  isSubmitting: boolean;
  onProviderTypeChange: (type: ProviderType) => void;
  onProviderIdChange: (id: string) => void;
  onApiKeyChange: (key: string) => void;
  onOrganizationChange: (org: string) => void;
  onBaseUrlChange: (url: string) => void;
  onProjectIdChange: (id: string) => void;
  onLocationChange: (location: string) => void;
  onSetAsDefaultChange: (value: boolean) => void;
  onSubmit: () => void;
  onCancel: () => void;
}

export const AddProviderForm: React.FC<AddProviderFormProps> = ({
  providerType,
  providerId,
  apiKey,
  organization,
  baseUrl,
  projectId,
  location,
  setAsDefault,
  error,
  isSubmitting,
  onProviderTypeChange,
  onProviderIdChange,
  onApiKeyChange,
  onOrganizationChange,
  onBaseUrlChange,
  onProjectIdChange,
  onLocationChange,
  onSetAsDefaultChange,
  onSubmit,
  onCancel,
}) => {
  const ProviderConfig = PROVIDER_CONFIGS[providerType];

  return (
    <div className="p-6 bg-background/80 backdrop-blur-md rounded-lg border border-border/50 space-y-4 shadow-lg">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-semibold">New Provider</h4>
        <button onClick={onCancel} className="p-1 hover:bg-accent rounded-md transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">Provider Type</label>
          <select
            value={providerType}
            onChange={(e) => onProviderTypeChange(e.target.value as ProviderType)}
            className="w-full px-3 py-2 border border-input rounded-md bg-background/50 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            {Object.entries(PROVIDER_DISPLAY_NAMES).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">
            Provider ID
            <span className="text-muted-foreground ml-1">(unique name)</span>
          </label>
          <input
            type="text"
            value={providerId}
            onChange={(e) => onProviderIdChange(e.target.value)}
            placeholder={`my-${providerType}`}
            pattern="[a-zA-Z0-9-_]+"
            className="w-full px-3 py-2 border border-input rounded-md bg-background/50 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
          />
          <p className="text-xs text-muted-foreground mt-1">
            Must be unique. Use letters, numbers, hyphens, and underscores only.
          </p>
        </div>
      </div>

      <ProviderConfig
        apiKey={apiKey}
        organization={organization}
        baseUrl={baseUrl}
        projectId={projectId}
        location={location}
        onApiKeyChange={onApiKeyChange}
        onOrganizationChange={onOrganizationChange}
        onBaseUrlChange={onBaseUrlChange}
        onProjectIdChange={onProjectIdChange}
        onLocationChange={onLocationChange}
      />

      <div className="flex items-center gap-2 pt-2">
        <input
          type="checkbox"
          id="set-default"
          checked={setAsDefault}
          onChange={(e) => onSetAsDefaultChange(e.target.checked)}
          className="rounded border-input"
        />
        <label htmlFor="set-default" className="text-sm cursor-pointer">
          Set as default provider
        </label>
      </div>

      {error && (
        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md flex items-start gap-2">
          <AlertCircle className="h-4 w-4 text-destructive mt-0.5 flex-shrink-0" />
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      <div className="flex gap-3 pt-2">
        <button
          onClick={onSubmit}
          disabled={isSubmitting}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-sm"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Adding...
            </>
          ) : (
            <>
              <Check className="h-4 w-4" />
              Add Provider
            </>
          )}
        </button>
        <button
          onClick={onCancel}
          disabled={isSubmitting}
          className="px-4 py-2.5 border border-border rounded-lg hover:bg-accent transition-colors disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
};
