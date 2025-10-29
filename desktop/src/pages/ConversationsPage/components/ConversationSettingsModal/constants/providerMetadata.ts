import type { ProviderType } from '../../../providers-types';

export interface ProviderMetadata {
  name: string;
  description: string;
  apiKeyPrefix?: string;
  apiKeyPlaceholder: string;
  helpUrl: string;
  features: {
    streaming: boolean;
    functions: boolean;
    vision: boolean;
    fastInference?: boolean;
    localOption?: boolean;
  };
  pricing?: {
    type: 'usage' | 'free' | 'local';
    note?: string;
  };
}

export const PROVIDER_METADATA: Record<ProviderType, ProviderMetadata> = {
  openai: {
    name: 'OpenAI',
    description: 'GPT-4, GPT-3.5, and other models',
    apiKeyPrefix: 'sk-',
    apiKeyPlaceholder: 'sk-...',
    helpUrl: 'https://platform.openai.com/api-keys',
    features: {
      streaming: true,
      functions: true,
      vision: true,
    },
    pricing: {
      type: 'usage',
      note: 'Pay per token',
    },
  },
  anthropic: {
    name: 'Anthropic',
    description: 'Claude 3 models with advanced reasoning',
    apiKeyPrefix: 'sk-ant-',
    apiKeyPlaceholder: 'sk-ant-...',
    helpUrl: 'https://console.anthropic.com/settings/keys',
    features: {
      streaming: true,
      functions: true,
      vision: true,
    },
    pricing: {
      type: 'usage',
      note: 'Pay per token',
    },
  },
  google: {
    name: 'Google AI',
    description: 'Gemini models with multimodal capabilities',
    apiKeyPrefix: 'AIza',
    apiKeyPlaceholder: 'AIzaSy...',
    helpUrl: 'https://aistudio.google.com/app/apikey',
    features: {
      streaming: true,
      functions: true,
      vision: true,
    },
    pricing: {
      type: 'usage',
      note: 'Free tier available',
    },
  },
  groq: {
    name: 'Groq',
    description: 'Ultra-fast inference with optimized hardware',
    apiKeyPrefix: 'gsk_',
    apiKeyPlaceholder: 'gsk_...',
    helpUrl: 'https://console.groq.com/keys',
    features: {
      streaming: true,
      functions: false,
      vision: false,
      fastInference: true,
    },
    pricing: {
      type: 'usage',
      note: 'Optimized for speed',
    },
  },
  mistral: {
    name: 'Mistral AI',
    description: 'Efficient models with strong multilingual support',
    apiKeyPrefix: 'sk-',
    apiKeyPlaceholder: 'sk-...',
    helpUrl: 'https://console.mistral.ai/api-keys',
    features: {
      streaming: true,
      functions: true,
      vision: false,
    },
    pricing: {
      type: 'usage',
      note: 'Competitive pricing',
    },
  },
  ollama: {
    name: 'Ollama',
    description: 'Run models locally on your machine',
    apiKeyPlaceholder: '',
    helpUrl: 'https://ollama.ai',
    features: {
      streaming: true,
      functions: false,
      vision: true,
      localOption: true,
    },
    pricing: {
      type: 'local',
      note: 'Free, runs on your hardware',
    },
  },
};

export const getProviderMetadata = (type: ProviderType): ProviderMetadata => {
  return PROVIDER_METADATA[type];
};

export const validateApiKey = (type: ProviderType, apiKey: string): boolean => {
  const metadata = PROVIDER_METADATA[type];
  if (!metadata.apiKeyPrefix) return true;
  return apiKey.startsWith(metadata.apiKeyPrefix);
};