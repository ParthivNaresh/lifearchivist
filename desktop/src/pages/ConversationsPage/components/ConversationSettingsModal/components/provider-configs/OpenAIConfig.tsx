import type { ProviderConfigProps } from './types';
import { BaseApiKeyConfig } from './BaseApiKeyConfig';

export const OpenAIConfig: React.FC<ProviderConfigProps> = (props) => {
  return (
    <BaseApiKeyConfig
      {...props}
      providerName="OpenAI"
      apiKeyPlaceholder="sk-..."
      helpUrl="https://platform.openai.com/api-keys"
      showOrganization
    />
  );
};