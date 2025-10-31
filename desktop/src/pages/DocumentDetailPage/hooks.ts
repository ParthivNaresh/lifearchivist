/**
 * Custom hooks for DocumentDetailPage
 */

import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { type DocumentAnalysis } from './types';
import { downloadDocumentFile } from './api';

// Error notification state type
export interface NotificationState {
  type: 'error' | 'success' | 'info';
  message: string;
  timestamp: number;
}

/**
 * Hook for managing notifications
 */
export const useNotification = () => {
  const [notification, setNotification] = useState<NotificationState | null>(null);

  const showNotification = useCallback((type: NotificationState['type'], message: string) => {
    setNotification({ type, message, timestamp: Date.now() });
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      setNotification((prev) => (prev?.timestamp === Date.now() ? null : prev));
    }, 5000);
  }, []);

  const clearNotification = useCallback(() => {
    setNotification(null);
  }, []);

  return { notification, showNotification, clearNotification };
};

/**
 * Hook for managing document tags
 */
export const useDocumentTags = (initialTags: string[] = []) => {
  const [tags, setTags] = useState<string[]>(initialTags);
  const [isAddingTag, setIsAddingTag] = useState(false);
  const [newTag, setNewTag] = useState('');

  const handleAddTag = useCallback(() => {
    if (newTag.trim() && !tags.includes(newTag.trim())) {
      setTags((prev) => [...prev, newTag.trim()]);
      setNewTag('');
      setIsAddingTag(false);
      // TODO: Persist tag changes to backend API
    }
  }, [newTag, tags]);

  const handleRemoveTag = useCallback((tagToRemove: string) => {
    setTags((prev) => prev.filter((tag) => tag !== tagToRemove));
    // TODO: Persist tag removal to backend API
  }, []);

  return {
    tags,
    setTags,
    isAddingTag,
    setIsAddingTag,
    newTag,
    setNewTag,
    handleAddTag,
    handleRemoveTag,
  };
};

/**
 * Hook for document download functionality
 */
export const useDocumentDownload = (
  analysis: DocumentAnalysis | undefined,
  onError?: (message: string) => void,
  onSuccess?: (message: string) => void
) => {
  const handleDownload = useCallback(async () => {
    if (!analysis) return;

    try {
      const fileHash = analysis.metadata?.file_hash;
      if (!fileHash || typeof fileHash !== 'string') {
        onError?.('File hash not found. Cannot download.');
        return;
      }

      const blob = await downloadDocumentFile(fileHash);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const fileName =
        analysis.metadata.title && typeof analysis.metadata.title === 'string'
          ? analysis.metadata.title
          : 'document';
      link.setAttribute('download', fileName);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      onSuccess?.(`Downloaded ${fileName}`);
    } catch (error) {
      console.error('Download failed:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to download document';
      onError?.(`Download failed: ${errorMessage}`);
    }
  }, [analysis, onError, onSuccess]);

  return handleDownload;
};

/**
 * Hook for document sharing functionality
 */
export const useDocumentShare = (
  analysis: DocumentAnalysis | undefined,
  onSuccess?: (message: string) => void,
  onError?: (message: string) => void
) => {
  const handleShare = useCallback(async () => {
    if (!analysis) return;

    const metadata = analysis.metadata || {};
    const title = typeof metadata.title === 'string' ? metadata.title : 'Document';
    const shareData = {
      title,
      text: `Check out this document: ${title}`,
      url: window.location.href,
    };

    try {
      if (navigator.share && navigator.canShare(shareData)) {
        await navigator.share(shareData);
        onSuccess?.('Document shared successfully');
      } else {
        // Fallback: Copy link to clipboard
        await navigator.clipboard.writeText(window.location.href);
        onSuccess?.('Link copied to clipboard');
      }
    } catch (error) {
      console.error('Share failed:', error);
      // Fallback: Copy link to clipboard
      try {
        await navigator.clipboard.writeText(window.location.href);
        onSuccess?.('Link copied to clipboard');
      } catch (clipboardError) {
        console.error('Clipboard copy failed:', clipboardError);
        onError?.('Failed to share document. Please copy the URL manually.');
      }
    }
  }, [analysis, onSuccess, onError]);

  return handleShare;
};

/**
 * Hook for page transition animations
 */
export const usePageTransition = () => {
  const [isTransitioning, setIsTransitioning] = useState(false);
  const navigate = useNavigate();

  const navigateWithTransition = useCallback(
    async (path: string) => {
      setIsTransitioning(true);
      window.scrollTo({ top: 0, behavior: 'smooth' });

      await new Promise((resolve) => setTimeout(resolve, 300));
      navigate(path);

      setTimeout(() => setIsTransitioning(false), 100);
    },
    [navigate]
  );

  return { isTransitioning, navigateWithTransition };
};

/**
 * Hook to sync tags from analysis metadata
 */
export const useSyncTags = (
  analysis: DocumentAnalysis | undefined,
  setTags: (tags: string[]) => void
) => {
  useEffect(() => {
    if (analysis?.metadata?.tags) {
      setTags(analysis.metadata.tags);
    }
  }, [analysis, setTags]);
};
