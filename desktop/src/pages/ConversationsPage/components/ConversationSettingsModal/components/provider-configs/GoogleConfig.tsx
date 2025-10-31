import type { ProviderConfigProps } from './types';
import { BaseApiKeyConfig } from './BaseApiKeyConfig';

export const GoogleConfig: React.FC<ProviderConfigProps> = (props) => {
  return (
    <BaseApiKeyConfig
      {...props}
      providerName="Google AI"
      apiKeyPlaceholder="AIzaSy..."
      helpUrl="https://aistudio.google.com/app/apikey"
      helpText="Simple API key authentication for Google AI Studio"
    />
  );
};
