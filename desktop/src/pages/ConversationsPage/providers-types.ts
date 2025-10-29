/**
 * Type definitions for LLM Provider management
 */

export type ProviderType = 'ollama' | 'openai' | 'anthropic' | 'google' | 'groq' | 'mistral';

export interface Provider {
  id: string;
  type: ProviderType;
  name: string;
  is_default: boolean;
  is_healthy: boolean;
  workspace_name?: string;
  is_admin?: boolean;
}

export interface ProviderModel {
  id: string;
  name: string;
  provider: string;
  provider_id: string; // NEW: Specific provider instance ID
  context_window: number;
  max_output_tokens: number;
  supports_streaming: boolean;
  supports_functions: boolean;
  supports_vision: boolean;
  cost_per_1k_input: number | null;
  cost_per_1k_output: number | null;
  metadata: Record<string, unknown>;
}

export interface AddProviderRequest {
  provider_id: string;
  provider_type: ProviderType;
  config: Record<string, unknown>;
  set_as_default?: boolean;
}

export interface UpdateProviderRequest {
  config?: Record<string, unknown>;
  set_as_default?: boolean;
}

export interface ListProvidersResponse {
  success: boolean;
  providers: Provider[];
  total: number;
}

export interface GetProviderResponse {
  success: boolean;
  provider_id: string;
  provider_type: ProviderType;
  is_default: boolean;
  is_initialized: boolean;
  is_healthy: boolean;
  user_id: string;
}

export interface AddProviderResponse {
  success: boolean;
  provider_id: string;
  provider_type: ProviderType;
  is_default: boolean;
  message: string;
}

export interface DeleteProviderResponse {
  success: boolean;
  provider_id: string;
  message: string;
}

export interface TestProviderResponse {
  success: boolean;
  provider_id: string;
  is_valid: boolean;
  message: string;
}

export interface ListModelsResponse {
  success: boolean;
  provider_id: string;
  models: ProviderModel[];
  total: number;
}

export interface SetDefaultProviderRequest {
  provider_id: string;
}

export interface SetDefaultProviderResponse {
  success: boolean;
  provider_id: string;
  message: string;
}

export interface Workspace {
  id: string;
  name: string;
  is_default: boolean;
  metadata?: Record<string, unknown>;
}

export interface ProviderMetadata {
  capabilities?: string[];
  workspaces?: Workspace[];
  [key: string]: unknown;
}

export interface EnrichedProvider extends Provider {
  workspace_name?: string;
}

export interface ApiErrorResponse {
  detail?: string;
  message?: string;
  error?: string;
}

export class ApiError extends Error {
  status?: number;
  response?: { status: number };

  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    if (status) {
      this.response = { status };
    }
  }
}
