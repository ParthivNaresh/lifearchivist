import type { ProviderConfigProps } from './types';
import { BaseApiKeyConfig } from './BaseApiKeyConfig';

export const AnthropicConfig: React.FC<ProviderConfigProps> = (props) => {
  return (
    <BaseApiKeyConfig
      {...props}
      providerName="Anthropic"
      apiKeyPlaceholder="sk-ant-..."
      helpUrl="https://console.anthropic.com/settings/keys"
    />
  );
};
