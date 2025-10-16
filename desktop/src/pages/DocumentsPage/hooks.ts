/**
 * Custom hooks for DocumentsPage
 */

import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { DocumentStatus } from './types';

/**
 * Hook for managing document status filter
 */
export const useDocumentFilter = (initialStatus: DocumentStatus = 'all') => {
  const [selectedStatus, setSelectedStatus] = useState<DocumentStatus>(initialStatus);
  
  return {
    selectedStatus,
    setSelectedStatus
  };
};

/**
 * Hook for handling tag navigation
 */
export const useTagNavigation = () => {
  const navigate = useNavigate();
  
  const handleTagClick = useCallback((tag: string) => {
    navigate(`/search?tags=${encodeURIComponent(tag)}`);
  }, [navigate]);
  
  return handleTagClick;
};