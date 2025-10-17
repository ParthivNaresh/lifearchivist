import { useState, useEffect, useRef } from 'react';

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiry: number;
}

const cache = new Map<string, CacheEntry<any>>();

export function useCache<T>(
  key: string,
  fetcher: () => Promise<T>,
  ttl: number = 5 * 60 * 1000 // 5 minutes default TTL
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);
  const fetchingRef = useRef(false);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      // Prevent concurrent fetches (handles React StrictMode double-invoke)
      if (fetchingRef.current) {
        return;
      }

      // Check cache first
      const cached = cache.get(key);
      const now = Date.now();
      
      if (cached && now < cached.expiry) {
        // Use cached data
        setData(cached.data);
        setLoading(false);
        setError(null);
        return;
      }

      // Fetch fresh data
      try {
        fetchingRef.current = true;
        setLoading(true);
        setError(null);
        
        const result = await fetcher();
        
        if (mountedRef.current) {
          setData(result);
          setLoading(false);
          
          // Cache the result
          cache.set(key, {
            data: result,
            timestamp: now,
            expiry: now + ttl
          });
        }
      } catch (err) {
        if (mountedRef.current) {
          setError(err instanceof Error ? err.message : 'An error occurred');
          setLoading(false);
          
          // If we have stale cached data, use it
          if (cached) {
            setData(cached.data);
          }
        }
      } finally {
        // Always reset the fetching flag
        fetchingRef.current = false;
      }
    };

    fetchData();
  }, [key, ttl]);

  const invalidate = () => {
    cache.delete(key);
  };

  const refresh = async () => {
    // Prevent concurrent refreshes
    if (fetchingRef.current) {
      return;
    }

    cache.delete(key);
    setLoading(true);
    setError(null);
    
    try {
      fetchingRef.current = true;
      const result = await fetcher();
      
      if (mountedRef.current) {
        setData(result);
        setLoading(false);
        
        cache.set(key, {
          data: result,
          timestamp: Date.now(),
          expiry: Date.now() + ttl
        });
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : 'An error occurred');
        setLoading(false);
      }
    } finally {
      fetchingRef.current = false;
    }
  };

  return { data, loading, error, refresh, invalidate };
}

export function clearCache() {
  cache.clear();
}

export function clearCacheKey(key: string) {
  cache.delete(key);
}