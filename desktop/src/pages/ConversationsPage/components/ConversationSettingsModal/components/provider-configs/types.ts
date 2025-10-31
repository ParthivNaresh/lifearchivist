export interface ProviderConfigProps {
  apiKey: string;
  organization?: string;
  baseUrl?: string;
  projectId?: string;
  location?: string;
  onApiKeyChange: (key: string) => void;
  onOrganizationChange?: (org: string) => void;
  onBaseUrlChange?: (url: string) => void;
  onProjectIdChange?: (id: string) => void;
  onLocationChange?: (location: string) => void;
}

export interface ProviderInfo {
  name: string;
  apiKeyPlaceholder: string;
  apiKeyLabel: string;
  helpUrl: string;
  note?: string;
  noteType?: 'info' | 'warning';
}
