/**
 * Utility functions for VaultPage
 */

import React from 'react';
import {
  FileText,
  FileSpreadsheet,
  Image,
  FileCode,
  FileArchive,
  File
} from 'lucide-react';
import { 
  Document, 
  CategoryConfig,
  SubthemeStyles 
} from './types';
import { 
  SUBTHEME_CATEGORIES,
  SUBTHEME_CATEGORY_CONFIG,
  SUBCLASSIFICATION_CONFIG 
} from './constants';
import { getSubthemeColors } from '../../utils/theme-colors';

/**
 * Format bytes into human-readable file size
 */
export const formatFileSize = (bytes: number): string => {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * Format date string into relative time
 */
export const formatDate = (dateString: string): string => {
  if (!dateString) return 'Unknown';
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
  
  return date.toLocaleDateString();
};

/**
 * Extract filename from path
 */
export const getFileName = (path: string): string => {
  if (!path) return 'Unnamed Document';
  // Handle both forward and backward slashes
  const parts = path.split(/[/\\]/);
  return parts[parts.length - 1] || path;
};

/**
 * Get file icon based on MIME type
 */
export const getFileIcon = (mimeType: string): React.ReactNode => {
  const mime = mimeType?.toLowerCase() || '';
  
  if (mime.includes('pdf')) {
    return <FileText className="h-5 w-5 text-red-500" />;
  }
  if (mime.includes('excel') || mime.includes('spreadsheet') || mime === 'text/csv') {
    return <FileSpreadsheet className="h-5 w-5 text-green-500" />;
  }
  if (mime.includes('word') || mime.includes('wordprocessingml')) {
    return <FileText className="h-5 w-5 text-blue-500" />;
  }
  if (mime.includes('image')) {
    return <Image className="h-5 w-5 text-purple-500" />;
  }
  if (mime.includes('text')) {
    return <FileCode className="h-5 w-5 text-gray-500" />;
  }
  if (mime.includes('zip') || mime.includes('rar') || mime.includes('archive')) {
    return <FileArchive className="h-5 w-5 text-orange-500" />;
  }
  
  return <File className="h-5 w-5 text-gray-400" />;
};

/**
 * Get theme for a document
 */
export const getDocumentTheme = (doc: Document): string => {
  // Processing status takes priority
  if (doc.status === 'processing' || doc.status === 'pending') {
    return 'Processing';
  }
  
  // Use the theme field directly from the API response
  if (doc.theme) {
    return doc.theme;
  }
  
  // Default to unclassified
  return 'Unclassified';
};

/**
 * Get the subtheme category for a subclassification
 */
export const getSubthemeCategory = (subclassification: string): string => {
  return SUBTHEME_CATEGORIES[subclassification] || 'Other';
};

/**
 * Get subtheme category config with fallback
 */
export const getSubthemeCategoryConfig = (categoryName: string): CategoryConfig => {
  return SUBTHEME_CATEGORY_CONFIG[categoryName] || SUBTHEME_CATEGORY_CONFIG['default'];
};

/**
 * Get subclassification config with fallback
 */
export const getSubclassificationConfig = (subclassificationName: string): CategoryConfig => {
  return SUBCLASSIFICATION_CONFIG[subclassificationName] || SUBCLASSIFICATION_CONFIG['default'];
};

/**
 * Get dynamic styles for subtheme cards using centralized theme colors
 */
export const getSubthemeStyles = (displayName: string): SubthemeStyles => {
  const isDark = document.documentElement.classList.contains('dark');
  const colors = getSubthemeColors(displayName, isDark);
  
  return {
    bg: colors.background,
    border: colors.border,
    icon: colors.icon
  };
};

/**
 * Check if documents are being processed
 */
export const hasProcessingDocuments = (documents: Document[] | undefined): boolean => {
  if (!documents) return false;
  return documents.some(doc => 
    doc.status === 'processing' || doc.status === 'pending'
  );
};

/**
 * Sort documents by creation date (newest first)
 */
export const sortDocumentsByDate = (docs: Document[]): Document[] => {
  return [...docs].sort((a, b) => {
    const dateA = new Date(a.created_at).getTime();
    const dateB = new Date(b.created_at).getTime();
    return dateB - dateA;
  });
};

/**
 * Sort themes by predefined order
 */
export const sortThemes = (themes: string[], themeOrder: readonly string[]): string[] => {
  return themes.sort((a, b) => {
    const aIndex = themeOrder.indexOf(a);
    const bIndex = themeOrder.indexOf(b);
    
    if (aIndex !== -1 && bIndex !== -1) {
      return aIndex - bIndex;
    }
    if (aIndex !== -1) return -1;
    if (bIndex !== -1) return 1;
    return a.localeCompare(b);
  });
};