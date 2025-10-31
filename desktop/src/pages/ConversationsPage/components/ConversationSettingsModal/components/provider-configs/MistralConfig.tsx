import type { ProviderConfigProps } from './types';
import { BaseApiKeyConfig } from './BaseApiKeyConfig';

export const MistralConfig: React.FC<ProviderConfigProps> = (props) => {
  return (
    <BaseApiKeyConfig
      {...props}
      providerName="Mistral"
      apiKeyPlaceholder="sk-..."
      helpUrl="https://console.mistral.ai/api-keys"
      helpText="Advanced models with strong multilingual capabilities"
    />
  );
};
