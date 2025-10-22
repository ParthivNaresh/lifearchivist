/**
 * useCache hook - wrapper around TanStack Query for consistent API
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';

export function useCache<T>(key: string, fetcher: () => Promise<T>, ttl: number = 5 * 60 * 1000) {
  const queryClient = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: [key],
    queryFn: fetcher,
    staleTime: ttl,
    gcTime: ttl * 2,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  return {
    data,
    loading: isLoading,
    error: error?.message ?? null,
    refresh: async () => {
      await refetch();
    },
    invalidate: async () => {
      await queryClient.invalidateQueries({ queryKey: [key] });
    },
  };
}
