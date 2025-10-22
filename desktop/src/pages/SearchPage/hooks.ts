/**
 * Search page hooks
 */

import { useCallback, useEffect } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom';

/**
 * Hook for managing search navigation to document details
 */
export const useSearchNavigation = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleDocumentClick = useCallback(
    (documentId: string) => {
      // Pass state to indicate we came from search
      navigate(`/vault/${documentId}/details`, {
        state: {
          from: 'search',
          returnPath: location.pathname + location.search, // Include search params
        },
      });
    },
    [navigate, location.pathname, location.search]
  );

  return {
    handleDocumentClick,
  };
};

/**
 * Hook to initialize search state from URL parameters
 */
export const useUrlParams = (
  setQuery: (query: string) => void,
  setSelectedTags: (tags: string[]) => void
) => {
  const [searchParams] = useSearchParams();
  const location = useLocation();

  useEffect(() => {
    // Read query from URL
    const urlQuery = searchParams.get('q');
    if (urlQuery) {
      setQuery(urlQuery);
    } else {
      setQuery(''); // Clear if no query in URL
    }

    // Read tags from URL
    const urlTags = searchParams.get('tags');
    if (urlTags) {
      const tags = urlTags
        .split(',')
        .map((tag) => decodeURIComponent(tag.trim()))
        .filter(Boolean);
      setSelectedTags(tags);
    } else {
      setSelectedTags([]); // Clear if no tags in URL
    }
  }, [location.search, setQuery, setSelectedTags, searchParams]); // Re-run when URL changes
};
