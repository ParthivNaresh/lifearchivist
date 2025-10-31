import type { ProviderType, AddProviderRequest } from '../../../providers-types';
import type { ProviderFormState } from '../hooks/useProviderForm';
import { validateUrl } from '../utils';

export class ProviderValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ProviderValidationError';
  }
}

export const validateProviderForm = (
  formState: ProviderFormState,
  existingProviderIds?: string[]
): void => {
  const providerId = formState.providerId.trim();

  if (!providerId) {
    throw new ProviderValidationError('Provider ID is required');
  }

  if (!/^[a-zA-Z0-9-_]+$/.test(providerId)) {
    throw new ProviderValidationError(
      'Provider ID can only contain letters, numbers, hyphens, and underscores'
    );
  }

  if (existingProviderIds?.includes(providerId)) {
    throw new ProviderValidationError(
      `Provider ID '${providerId}' already exists. Please choose a unique identifier.`
    );
  }

  switch (formState.providerType) {
    case 'ollama':
      validateOllamaProvider(formState);
      break;
    case 'openai':
    case 'anthropic':
    case 'google':
    case 'groq':
    case 'mistral':
      validateApiKeyProvider(formState);
      break;
    default: {
      const exhaustiveCheck: never = formState.providerType;
      throw new ProviderValidationError(`Unknown provider type: ${exhaustiveCheck as string}`);
    }
  }
};

const validateOllamaProvider = (formState: ProviderFormState): void => {
  if (!formState.baseUrl.trim()) {
    throw new ProviderValidationError('Base URL is required for Ollama');
  }
  if (!validateUrl(formState.baseUrl.trim())) {
    throw new ProviderValidationError('Invalid Base URL format');
  }
};

const validateApiKeyProvider = (formState: ProviderFormState): void => {
  if (!formState.apiKey.trim()) {
    const providerNames: Record<ProviderType, string> = {
      google: 'Google AI',
      openai: 'OpenAI',
      anthropic: 'Anthropic',
      groq: 'Groq',
      mistral: 'Mistral AI',
      ollama: 'Ollama',
    };
    throw new ProviderValidationError(
      `API Key is required for ${providerNames[formState.providerType]}`
    );
  }
};

export const buildProviderConfig = (formState: ProviderFormState): AddProviderRequest => {
  const baseRequest = {
    provider_id: formState.providerId.trim(),
    provider_type: formState.providerType,
    set_as_default: formState.setAsDefault,
  };

  switch (formState.providerType) {
    case 'ollama':
      return {
        ...baseRequest,
        config: { base_url: formState.baseUrl.trim() },
      };

    case 'openai': {
      const config: Record<string, unknown> = {
        api_key: formState.apiKey.trim(),
      };
      if (formState.organization.trim()) {
        config.organization = formState.organization.trim();
      }
      if (formState.baseUrl.trim()) {
        config.base_url = formState.baseUrl.trim();
      }
      return { ...baseRequest, config };
    }

    default: {
      const config: Record<string, unknown> = {
        api_key: formState.apiKey.trim(),
      };
      if (formState.baseUrl.trim()) {
        config.base_url = formState.baseUrl.trim();
      }
      return { ...baseRequest, config };
    }
  }
};
