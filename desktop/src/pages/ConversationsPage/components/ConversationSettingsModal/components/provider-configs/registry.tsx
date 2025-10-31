import type { ProviderType } from '../../../../providers-types';
import type { ProviderConfigProps } from './types';
import { OpenAIConfig } from './OpenAIConfig';
import { AnthropicConfig } from './AnthropicConfig';
import { GoogleConfig } from './GoogleConfig';
import { GroqConfig } from './GroqConfig';
import { MistralConfig } from './MistralConfig';
import { OllamaConfig } from './OllamaConfig';

export const PROVIDER_CONFIGS: Record<ProviderType, React.ComponentType<ProviderConfigProps>> = {
  openai: OpenAIConfig,
  anthropic: AnthropicConfig,
  google: GoogleConfig,
  groq: GroqConfig,
  mistral: MistralConfig,
  ollama: OllamaConfig,
};

export const PROVIDER_DISPLAY_NAMES: Record<ProviderType, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic (Claude)',
  google: 'Google (Gemini)',
  groq: 'Groq (Fast Inference)',
  mistral: 'Mistral AI',
  ollama: 'Ollama (Local)',
};
