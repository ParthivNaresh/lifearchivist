/**
 * Timeline page hooks
 */

import { useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

/**
 * Hook for managing timeline navigation to document details
 */
export const useTimelineNavigation = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleDocumentClick = useCallback(
    (documentId: string) => {
      // Pass state to indicate we came from timeline
      navigate(`/vault/${documentId}/details`, {
        state: {
          from: 'timeline',
          returnPath: location.pathname,
        },
      });
    },
    [navigate, location.pathname]
  );

  return {
    handleDocumentClick,
  };
};
