/**
 * API functions for LLM Provider management
 */

import type {
  AddProviderRequest,
  AddProviderResponse,
  DeleteProviderResponse,
  GetProviderResponse,
  ListModelsResponse,
  ListProvidersResponse,
  SetDefaultProviderRequest,
  SetDefaultProviderResponse,
  TestProviderResponse,
  UpdateProviderRequest,
  ApiErrorResponse,
  ProviderMetadata,
} from './providers-types';
import { ApiError } from './providers-types';

const API_BASE = 'http://localhost:8000/api/providers';

async function handleErrorResponse(response: Response, defaultMessage: string): Promise<never> {
  let errorMessage = defaultMessage;

  try {
    const errorData = (await response.json()) as ApiErrorResponse;
    errorMessage = errorData.detail ?? errorData.message ?? errorData.error ?? defaultMessage;
  } catch {
    errorMessage = response.statusText || defaultMessage;
  }

  throw new Error(errorMessage);
}

export const providersApi = {
  /**
   * List all providers
   */
  async list(): Promise<ListProvidersResponse> {
    const response = await fetch(API_BASE);

    if (!response.ok) {
      throw new Error(`Failed to list providers: ${response.statusText}`);
    }

    return response.json() as Promise<ListProvidersResponse>;
  },

  /**
   * Get a specific provider
   */
  async get(providerId: string): Promise<GetProviderResponse> {
    const response = await fetch(`${API_BASE}/${providerId}`);

    if (!response.ok) {
      throw new Error(`Failed to get provider: ${response.statusText}`);
    }

    return response.json() as Promise<GetProviderResponse>;
  },

  /**
   * Add a new provider
   */
  async add(data: AddProviderRequest): Promise<AddProviderResponse> {
    const response = await fetch(API_BASE, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      await handleErrorResponse(response, 'Failed to add provider');
    }

    return response.json() as Promise<AddProviderResponse>;
  },

  /**
   * Update a provider
   */
  async update(providerId: string, data: UpdateProviderRequest): Promise<AddProviderResponse> {
    const response = await fetch(`${API_BASE}/${providerId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      await handleErrorResponse(response, 'Failed to update provider');
    }

    return response.json() as Promise<AddProviderResponse>;
  },

  /**
   * Check provider usage in conversations
   */
  async checkUsage(providerId: string): Promise<{
    success: boolean;
    provider_id: string;
    conversation_count: number;
    sample_conversations: {
      id: string;
      title: string;
      model: string;
    }[];
  }> {
    const response = await fetch(`${API_BASE}/${providerId}/usage-check`);

    if (!response.ok) {
      await handleErrorResponse(response, 'Failed to check provider usage');
    }

    return response.json();
  },

  /**
   * Delete a provider
   */
  async delete(providerId: string, updateConversations = false): Promise<DeleteProviderResponse> {
    const params = updateConversations ? '?update_conversations=true' : '';
    const response = await fetch(`${API_BASE}/${providerId}${params}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      await handleErrorResponse(response, 'Failed to delete provider');
    }

    return response.json() as Promise<DeleteProviderResponse>;
  },

  /**
   * Test provider credentials
   */
  async test(providerId: string): Promise<TestProviderResponse> {
    const response = await fetch(`${API_BASE}/${providerId}/test`, {
      method: 'POST',
    });

    if (!response.ok) {
      await handleErrorResponse(response, 'Failed to test provider');
    }

    return response.json() as Promise<TestProviderResponse>;
  },

  /**
   * List models for a provider
   */
  async listModels(providerId: string): Promise<ListModelsResponse> {
    const response = await fetch(`${API_BASE}/${providerId}/models`);

    if (!response.ok) {
      throw new Error(`Failed to list models: ${response.statusText}`);
    }

    return response.json() as Promise<ListModelsResponse>;
  },

  /**
   * Set default provider
   */
  async setDefault(data: SetDefaultProviderRequest): Promise<SetDefaultProviderResponse> {
    const response = await fetch(`${API_BASE}/default`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      await handleErrorResponse(response, 'Failed to set default provider');
    }

    return response.json() as Promise<SetDefaultProviderResponse>;
  },

  /**
   * Get provider metadata
   */
  async getMetadata(
    providerId: string,
    include: string[] = ['capabilities'],
    startTime?: string,
    endTime?: string
  ): Promise<ProviderMetadata> {
    const params = new URLSearchParams();
    for (const item of include) {
      params.append('include', item);
    }
    if (startTime) params.append('start_time', startTime);
    if (endTime) params.append('end_time', endTime);

    const response = await fetch(`${API_BASE}/${providerId}/metadata?${params.toString()}`);

    if (!response.ok) {
      const error = new ApiError(`Failed to get metadata: ${response.statusText}`, response.status);
      throw error;
    }

    return response.json() as Promise<ProviderMetadata>;
  },
};
