/**
 * Custom hooks for DocumentDetailPage
 */

import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { DocumentAnalysis } from './types';
import { downloadDocumentFile } from './api';

/**
 * Hook for managing document tags
 */
export const useDocumentTags = (initialTags: string[] = []) => {
  const [tags, setTags] = useState<string[]>(initialTags);
  const [isAddingTag, setIsAddingTag] = useState(false);
  const [newTag, setNewTag] = useState('');

  const handleAddTag = useCallback(() => {
    if (newTag.trim() && !tags.includes(newTag.trim())) {
      setTags(prev => [...prev, newTag.trim()]);
      setNewTag('');
      setIsAddingTag(false);
      // TODO: Persist tag changes to backend API
    }
  }, [newTag, tags]);

  const handleRemoveTag = useCallback((tagToRemove: string) => {
    setTags(prev => prev.filter(tag => tag !== tagToRemove));
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
    handleRemoveTag
  };
};

/**
 * Hook for document download functionality
 */
export const useDocumentDownload = (analysis: DocumentAnalysis | undefined) => {
  const handleDownload = useCallback(async () => {
    if (!analysis) return;
    
    try {
      const fileHash = analysis.metadata?.file_hash;
      if (!fileHash) {
        alert('File hash not found. Cannot download.');
        return;
      }
      
      const blob = await downloadDocumentFile(fileHash);
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', analysis.metadata.title || 'document');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Failed to download document. Please try again.');
    }
  }, [analysis]);

  return handleDownload;
};

/**
 * Hook for document sharing functionality
 */
export const useDocumentShare = (analysis: DocumentAnalysis | undefined) => {
  const handleShare = useCallback(async () => {
    if (!analysis) return;
    
    const metadata = analysis.metadata || {};
    const shareData = {
      title: metadata.title || 'Document',
      text: `Check out this document: ${metadata.title || 'Untitled'}`,
      url: window.location.href
    };
    
    try {
      if (navigator.share && navigator.canShare(shareData)) {
        await navigator.share(shareData);
      } else {
        // Fallback: Copy link to clipboard
        await navigator.clipboard.writeText(window.location.href);
        alert('Link copied to clipboard!');
      }
    } catch (error) {
      console.error('Share failed:', error);
      // Fallback: Copy link to clipboard
      try {
        await navigator.clipboard.writeText(window.location.href);
        alert('Link copied to clipboard!');
      } catch (clipboardError) {
        console.error('Clipboard copy failed:', clipboardError);
      }
    }
  }, [analysis]);

  return handleShare;
};

/**
 * Hook for page transition animations
 */
export const usePageTransition = () => {
  const [isTransitioning, setIsTransitioning] = useState(false);
  const navigate = useNavigate();

  const navigateWithTransition = useCallback(async (path: string) => {
    setIsTransitioning(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
    
    await new Promise(resolve => setTimeout(resolve, 300));
    navigate(path);
    
    setTimeout(() => setIsTransitioning(false), 100);
  }, [navigate]);

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