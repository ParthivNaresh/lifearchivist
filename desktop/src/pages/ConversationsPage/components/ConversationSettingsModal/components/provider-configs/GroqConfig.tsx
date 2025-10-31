import type { ProviderConfigProps } from './types';
import { BaseApiKeyConfig } from './BaseApiKeyConfig';

export const GroqConfig: React.FC<ProviderConfigProps> = (props) => {
  return (
    <BaseApiKeyConfig
      {...props}
      providerName="Groq"
      apiKeyPlaceholder="gsk_..."
      helpUrl="https://console.groq.com/keys"
      helpText="Fast inference with Groq's optimized hardware"
    />
  );
};
