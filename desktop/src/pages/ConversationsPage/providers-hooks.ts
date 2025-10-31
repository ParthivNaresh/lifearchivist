/**
 * React hooks for LLM Provider management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { providersApi } from './providers-api';
import type {
  AddProviderRequest,
  EnrichedProvider,
  ListProvidersResponse,
} from './providers-types';

const PROVIDERS_QUERY_KEY = ['providers'];

interface EnrichedProvidersResponse extends Omit<ListProvidersResponse, 'providers'> {
  providers: EnrichedProvider[];
}

interface ErrorWithStatus {
  response?: { status?: number };
  status?: number;
}

/**
 * Hook to fetch all providers with metadata enrichment
 */
export function useProviders() {
  return useQuery<EnrichedProvidersResponse>({
    queryKey: PROVIDERS_QUERY_KEY,
    queryFn: async () => {
      const response = await providersApi.list();

      const enrichedProviders = await Promise.all(
        response.providers.map(async (provider): Promise<EnrichedProvider> => {
          if (!provider.is_admin) {
            return provider;
          }

          try {
            const capabilitiesMetadata = await providersApi.getMetadata(provider.id, [
              'capabilities',
            ]);

            const enriched: EnrichedProvider = { ...provider };

            const capabilities = capabilitiesMetadata.capabilities ?? [];
            const supportsWorkspaces = capabilities.includes('workspaces');

            if (supportsWorkspaces) {
              try {
                const workspacesMetadata = await providersApi.getMetadata(provider.id, [
                  'workspaces',
                ]);

                if (workspacesMetadata.workspaces && workspacesMetadata.workspaces.length > 0) {
                  const defaultWorkspace = workspacesMetadata.workspaces.find(
                    (ws) => ws.is_default
                  );
                  if (defaultWorkspace) {
                    enriched.workspace_name = defaultWorkspace.name;
                  }
                }
              } catch (workspaceErr) {
                console.warn(
                  `Failed to fetch workspaces for provider ${provider.id}:`,
                  workspaceErr
                );
              }
            }

            return enriched;
          } catch (err) {
            const error = err as ErrorWithStatus;
            const status = error.response?.status ?? error.status;
            if (status === 501) {
              return provider;
            }
            console.warn(`Failed to fetch metadata for provider ${provider.id}:`, err);
            return provider;
          }
        })
      );

      return {
        ...response,
        providers: enrichedProviders,
      };
    },
    staleTime: 30000,
  });
}

/**
 * Hook to add a provider
 */
export function useAddProvider() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AddProviderRequest) => providersApi.add(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PROVIDERS_QUERY_KEY });
    },
  });
}

/**
 * Hook to check provider usage
 */
export function useCheckProviderUsage() {
  return useMutation({
    mutationFn: (providerId: string) => providersApi.checkUsage(providerId),
  });
}

/**
 * Hook to delete a provider
 */
export function useDeleteProvider() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      providerId,
      updateConversations,
    }: {
      providerId: string;
      updateConversations: boolean;
    }) => providersApi.delete(providerId, updateConversations),
    onSuccess: (_, variables) => {
      void queryClient.invalidateQueries({ queryKey: PROVIDERS_QUERY_KEY });

      if (variables.updateConversations) {
        void queryClient.invalidateQueries({ queryKey: ['conversations'] });
        void queryClient.invalidateQueries({ queryKey: ['conversation'] });
      }
    },
  });
}

/**
 * Hook to test provider credentials
 */
export function useTestProvider() {
  return useMutation({
    mutationFn: (providerId: string) => providersApi.test(providerId),
  });
}

/**
 * Hook to set default provider
 */
export function useSetDefaultProvider() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { provider_id: string; default_model?: string }) =>
      providersApi.setDefault(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PROVIDERS_QUERY_KEY });
    },
  });
}

/**
 * Hook to list models for all providers
 */
export function useAllProviderModels() {
  const { data: providersData } = useProviders();
  const providers = providersData?.providers ?? [];
  const providerIds = providers.map((p) => p.id).sort();

  return useQuery({
    queryKey: [...PROVIDERS_QUERY_KEY, 'all-models', providerIds],
    queryFn: async () => {
      const allModels = await Promise.all(
        providers.map(async (provider) => {
          try {
            const response = await providersApi.listModels(provider.id);
            return response.models;
          } catch (err) {
            console.warn(`Failed to load models for provider ${provider.id}:`, err);
            return [];
          }
        })
      );
      return allModels.flat();
    },
    enabled: providers.length > 0,
    staleTime: 300000,
  });
}
