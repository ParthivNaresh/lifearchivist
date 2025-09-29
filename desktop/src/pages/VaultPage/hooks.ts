/**
 * Custom hooks for VaultPage
 * 
 * Hierarchy:
 * - Theme (e.g., Financial, Healthcare)
 *   - Category/Subtheme (e.g., Insurance, Loan, Banking)
 *     - Subclassification (e.g., Insurance Policy, Mortgage Statement)
 *       - Individual Documents
 */

import { useState, useCallback, useEffect, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useCache, clearCacheKey } from '../../hooks/useCache';
import { 
  Document, 
  VaultInfo, 
  FileSystemItem, 
  ViewMode,
  CurrentStats 
} from './types';
import { 
  CACHE_DURATIONS,
  THEME_CONFIG,
  THEME_ORDER
} from './constants';
import {
  getDocumentTheme,
  getSubthemeCategory,
  getSubthemeCategoryConfig,
  getSubclassificationConfig,
  getFileName,
  getFileIcon,
  hasProcessingDocuments,
  sortDocumentsByDate
} from './utils';
import * as api from './api';

/**
 * Hook for managing vault data fetching
 */
export const useVaultData = () => {
  const fetchVaultInfo = useCallback(api.fetchVaultInfo, []);
  const fetchDocuments = useCallback(() => api.fetchDocuments(500), []);

  const { 
    data: vaultInfo, 
    refresh: refreshInfo 
  } = useCache(
    'vault-info',
    fetchVaultInfo,
    CACHE_DURATIONS.VAULT_INFO
  );

  const { 
    data: documents, 
    refresh: refreshDocuments, 
    loading: documentsLoading 
  } = useCache(
    'documents-vault',
    fetchDocuments,
    CACHE_DURATIONS.DOCUMENTS
  );

  const manualRefresh = useCallback(async () => {
    // Clear the cache to force fresh data
    clearCacheKey('vault-info');
    clearCacheKey('documents-vault');
    
    // Refresh both info and documents
    await Promise.all([refreshInfo(), refreshDocuments()]);
  }, [refreshInfo, refreshDocuments]);

  return {
    vaultInfo,
    documents,
    documentsLoading,
    refreshInfo,
    refreshDocuments,
    manualRefresh
  };
};

/**
 * Extract primary subclassification and category from document
 */
const extractDocumentClassification = (doc: Document): { 
  primarySubclassification?: string; 
  category?: string;
} => {
  if (!doc.primary_subclassification) {
    return { primarySubclassification: undefined, category: undefined };
  }
  
  const primarySubclassification = doc.primary_subclassification;
  const category = doc.category_mapping?.[primarySubclassification] || 
                  getSubthemeCategory(primarySubclassification);
  
  return { primarySubclassification, category };
};

/**
 * Create a FileSystemItem from a Document
 */
const createFileItem = (doc: Document, themeName: string): FileSystemItem => {
  const { primarySubclassification } = extractDocumentClassification(doc);
  
  return {
    name: doc.file_hash,
    displayName: getFileName(doc.original_path),
    type: 'file' as const,
    size: doc.size_bytes,
    created: doc.created_at,
    documentId: doc.id,
    status: doc.status,
    wordCount: doc.word_count,
    mimeType: doc.mime_type,
    primaryTheme: themeName,
    themes: doc.themes,
    themeConfidence: doc.theme_confidence,
    subthemes: doc.subthemes,
    primarySubtheme: doc.primary_subtheme,
    subclassifications: doc.subclassifications,
    primarySubclassification,
    subclassificationConfidence: doc.subclassification_confidence,
    icon: getFileIcon(doc.mime_type)
  };
};

/**
 * Hook for building the file system structure
 * Creates a hierarchical structure: Theme > Category > Subclassification > Documents
 */
export const useFileSystem = (documents: Document[] | undefined) => {
  const buildFileSystem = useMemo(() => {
    return (): FileSystemItem[] => {
      if (!documents || documents.length === 0) return [];

      try {
        // Group documents by theme
        const themeGroups = new Map<string, Document[]>();
        
        documents.forEach(doc => {
          const theme = getDocumentTheme(doc);
          if (!themeGroups.has(theme)) {
            themeGroups.set(theme, []);
          }
          themeGroups.get(theme)?.push(doc);
        });
        
        // Sort themes by predefined order
        const sortedThemes = Array.from(themeGroups.keys()).sort((a, b) => {
          const aIndex = THEME_ORDER.indexOf(a as any);
          const bIndex = THEME_ORDER.indexOf(b as any);
          
          if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
          if (aIndex !== -1) return -1;
          if (bIndex !== -1) return 1;
          return a.localeCompare(b);
        });
        
        // Build the file system structure
        return sortedThemes.map(themeName => {
          const docs = themeGroups.get(themeName) || [];
          const config = THEME_CONFIG[themeName] || THEME_CONFIG['Unclassified'];
          
          // Count processing documents
          const processingCount = docs.filter(d => 
            d.status === 'processing' || d.status === 'pending'
          ).length;
          
          // Group documents by category, then by subclassification
          const categoryGroups = new Map<string, Map<string, Document[]>>();
          const uncategorizedDocs: Document[] = [];
          
          // Categorize documents
          docs.forEach(doc => {
            const { primarySubclassification, category } = extractDocumentClassification(doc);
            
            if (primarySubclassification && category) {
              if (!categoryGroups.has(category)) {
                categoryGroups.set(category, new Map<string, Document[]>());
              }
              
              const subclassificationGroups = categoryGroups.get(category)!;
              if (!subclassificationGroups.has(primarySubclassification)) {
                subclassificationGroups.set(primarySubclassification, []);
              }
              
              subclassificationGroups.get(primarySubclassification)?.push(doc);
            } else {
              uncategorizedDocs.push(doc);
            }
          });
          
          // Build children array
          const children: FileSystemItem[] = [];
          
          // Process categorized documents
          const sortedCategories = Array.from(categoryGroups.keys()).sort();
          
          sortedCategories.forEach(categoryName => {
            const subclassificationGroups = categoryGroups.get(categoryName)!;
            const categoryConfig = getSubthemeCategoryConfig(categoryName);
            
            // Build subclassification folders
            const categoryChildren: FileSystemItem[] = [];
            let categoryDocCount = 0;
            let categorySize = 0;
            
            const sortedSubclassifications = Array.from(subclassificationGroups.keys()).sort();
            
            sortedSubclassifications.forEach(subclassificationName => {
              const subclassificationDocs = subclassificationGroups.get(subclassificationName) || [];
              const sortedDocs = sortDocumentsByDate(subclassificationDocs);
              const subclassificationConfig = getSubclassificationConfig(subclassificationName);
              
              categoryDocCount += sortedDocs.length;
              categorySize += sortedDocs.reduce((sum, doc) => sum + doc.size_bytes, 0);
              
              // Create subclassification folder
              const subclassificationFolder: FileSystemItem = {
                name: `${themeName}-${categoryName}-${subclassificationName}`,
                displayName: subclassificationName,
                type: 'folder',
                icon: subclassificationConfig.icon,
                itemCount: sortedDocs.length,
                size: sortedDocs.reduce((sum, doc) => sum + doc.size_bytes, 0),
                hierarchyLevel: 'subclassification',
                useColoredCard: true,  // Renders as SubthemeCard
                parentTheme: themeName,
                parentCategory: categoryName,
                children: sortedDocs.map(doc => createFileItem(doc, themeName))
              };
              
              categoryChildren.push(subclassificationFolder);
            });
            
            // Create category folder
            const categoryFolder: FileSystemItem = {
              name: `${themeName}-${categoryName}`,
              displayName: categoryName,
              type: 'folder',
              icon: categoryConfig.icon,
              itemCount: categoryDocCount,
              size: categorySize,
              hierarchyLevel: 'category',
              useColoredCard: true,  // Renders as SubthemeCard
              parentTheme: themeName,
              children: categoryChildren
            };
            
            children.push(categoryFolder);
          });
          
          // Add uncategorized documents directly under theme
          const sortedUncategorizedDocs = sortDocumentsByDate(uncategorizedDocs);
          sortedUncategorizedDocs.forEach(doc => {
            children.push(createFileItem(doc, themeName));
          });
          
          // Create theme folder
          const themeFolder: FileSystemItem = {
            name: themeName,
            displayName: themeName,
            type: 'folder',
            icon: config.icon,
            itemCount: docs.length,
            processingCount,
            size: docs.reduce((sum, doc) => sum + doc.size_bytes, 0),
            hierarchyLevel: 'theme',
            useColoredCard: false,  // Renders as ThemeCard
            children
          };
          
          return themeFolder;
        });
      } catch (error) {
        console.error('Error building file system structure:', error);
        return [];
      }
    };
  }, [documents]);

  return buildFileSystem();
};

/**
 * Hook for managing vault navigation
 */
export const useVaultNavigation = () => {
  const navigate = useNavigate();
  const location = useLocation();
  
  // Store both the actual path (for navigation) and display path (for breadcrumbs)
  const [navigationPath, setNavigationPath] = useState<string[]>(
    location.state?.navigationPath || ['All Documents']
  );
  const [displayPath, setDisplayPath] = useState<string[]>(
    location.state?.displayPath || ['All Documents']
  );
  const [isTransitioning, setIsTransitioning] = useState(false);

  // Clear location state after using it to prevent stale state
  useEffect(() => {
    if (location.state) {
      // Replace current history entry without state
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  const navigateToFolder = useCallback((folder: FileSystemItem) => {
    if (folder.type !== 'folder') return;
    
    setIsTransitioning(true);
    setTimeout(() => {
      setNavigationPath(prev => [...prev, folder.name]);
      setDisplayPath(prev => [...prev, folder.displayName]);
      setIsTransitioning(false);
    }, 150);
  }, []);

  const navigateToBreadcrumb = useCallback((index: number) => {
    setIsTransitioning(true);
    setTimeout(() => {
      setNavigationPath(prev => prev.slice(0, index + 1));
      setDisplayPath(prev => prev.slice(0, index + 1));
      setIsTransitioning(false);
    }, 150);
  }, []);

  const handleFileClick = useCallback((item: FileSystemItem, viewMode: ViewMode, searchTerm: string) => {
    if (item.type === 'folder') {
      navigateToFolder(item);
    } else if (item.documentId) {
      // Pass state to indicate we came from vault
      navigate(`/vault/${item.documentId}/details`, {
        state: { 
          from: 'vault',
          returnPath: location.pathname,
          returnState: { 
            navigationPath, 
            displayPath,
            searchTerm, 
            viewMode 
          }
        }
      });
    }
  }, [navigate, location.pathname, navigationPath, displayPath, navigateToFolder]);

  const resetPath = useCallback(() => {
    setNavigationPath(['All Documents']);
    setDisplayPath(['All Documents']);
  }, []);

  return {
    currentPath: displayPath,  // For breadcrumbs display
    navigationPath,  // For actual navigation
    isTransitioning,
    navigateToFolder,
    navigateToBreadcrumb,
    handleFileClick,
    resetPath
  };
};

/**
 * Hook for managing vault search
 */
export const useVaultSearch = () => {
  const location = useLocation();
  const [searchTerm, setSearchTerm] = useState(
    location.state?.searchTerm || ''
  );
  const [isSearching, setIsSearching] = useState(false);

  const clearSearch = useCallback(() => {
    setIsSearching(false);
    setSearchTerm('');
  }, []);

  const filterItems = useCallback((items: FileSystemItem[]) => {
    if (!searchTerm) return items;
    
    const lowerSearchTerm = searchTerm.toLowerCase();
    return items.filter(item => 
      item.displayName.toLowerCase().includes(lowerSearchTerm)
    );
  }, [searchTerm]);

  return {
    searchTerm,
    setSearchTerm,
    isSearching,
    setIsSearching,
    clearSearch,
    filterItems
  };
};

/**
 * Hook for managing vault view mode
 */
export const useVaultViewMode = () => {
  const location = useLocation();
  const [viewMode, setViewMode] = useState<ViewMode>(
    location.state?.viewMode || 'grid'
  );

  return {
    viewMode,
    setViewMode
  };
};

/**
 * Hook for managing vault refresh and clearing
 */
export const useVaultActions = (manualRefresh: () => Promise<void>, resetPath: () => void) => {
  const [refreshing, setRefreshing] = useState(false);
  const [clearing, setClearing] = useState(false);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await manualRefresh();
    } catch (err) {
      console.error('Failed to refresh vault data:', err);
    } finally {
      setRefreshing(false);
    }
  }, [manualRefresh]);

  const handleClearVault = useCallback(async () => {
    const confirmed = window.confirm(
      'Are you sure you want to clear the entire vault? ' +
      'This will permanently delete all files and their associated document records. ' +
      'This cannot be undone.'
    );
    
    if (!confirmed) return;

    try {
      setClearing(true);
      await api.clearVault();
      await manualRefresh();
      resetPath();
    } catch (err) {
      console.error('Failed to clear vault:', err);
      // Could add user notification here
    } finally {
      setClearing(false);
    }
  }, [manualRefresh, resetPath]);

  return {
    refreshing,
    clearing,
    handleRefresh,
    handleClearVault
  };
};

/**
 * Hook for calculating current view statistics
 */
export const useCurrentStats = (filteredItems: FileSystemItem[]): CurrentStats => {
  return useMemo(() => {
    // Helper function to recursively count documents
    const countDocumentsRecursively = (items: FileSystemItem[]): number => {
      let count = 0;
      items.forEach(item => {
        if (item.type === 'file') {
          count++;
        } else if (item.type === 'folder' && item.children) {
          count += countDocumentsRecursively(item.children);
        }
      });
      return count;
    };
    
    // Helper function to recursively calculate total size
    const calculateTotalSize = (items: FileSystemItem[]): number => {
      let size = 0;
      items.forEach(item => {
        if (item.type === 'file') {
          size += item.size || 0;
        } else if (item.type === 'folder' && item.children) {
          size += calculateTotalSize(item.children);
        }
      });
      return size;
    };
    
    const stats = {
      folders: 0,
      files: 0,
      totalDocuments: 0,  // Total documents including those in subfolders
      totalSize: 0
    };
    
    filteredItems.forEach(item => {
      if (item.type === 'folder') {
        stats.folders++;
        // Count all documents within this folder
        if (item.children) {
          stats.totalDocuments += countDocumentsRecursively(item.children);
        }
      } else {
        stats.files++;
        stats.totalDocuments++;
      }
    });
    
    // Calculate total size
    stats.totalSize = calculateTotalSize(filteredItems);
    
    return stats;
  }, [filteredItems]);
};

/**
 * Hook for auto-refresh when documents are processing
 */
export const useAutoRefresh = (documents: Document[] | undefined, refreshDocuments: () => Promise<any>) => {
  useEffect(() => {
    if (!hasProcessingDocuments(documents)) return;
    
    // Set up polling interval for processing documents
    const interval = setInterval(() => {
      refreshDocuments();
    }, CACHE_DURATIONS.POLLING_INTERVAL);
    
    return () => clearInterval(interval);
  }, [documents, refreshDocuments]);
};

/**
 * Hook to get current directory items based on navigation path
 */
export const useCurrentItems = (fileSystem: FileSystemItem[], navigationPath: string[]): FileSystemItem[] => {
  return useMemo(() => {
    if (navigationPath.length === 1) {
      return fileSystem;
    }

    let current = fileSystem;
    for (let i = 1; i < navigationPath.length; i++) {
      const folder = current.find(item => item.name === navigationPath[i]);
      if (folder?.children) {
        current = folder.children;
      } else {
        // Path not found, return empty array
        console.warn(`Path not found: ${navigationPath.slice(0, i + 1).join(' > ')}`);
        return [];
      }
    }
    return current;
  }, [fileSystem, navigationPath]);
};