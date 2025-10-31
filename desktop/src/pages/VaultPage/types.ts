/**
 * Type definitions for VaultPage
 */

import { type ReactNode } from 'react';

export interface Document {
  id: string;
  file_hash: string;
  original_path: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
  status: string;
  word_count: number;
  tags: string[];
  text_preview: string;
  theme?: string;
  theme_confidence?: number;
  confidence_level?: string;
  classification?: string;
  pattern_or_phrase?: string;

  // Subtheme fields (e.g., Banking, Investment, Insurance)
  subthemes?: string[];
  primary_subtheme?: string;

  // Subclassification fields (e.g., Bank Statement, Brokerage Statement)
  subclassifications?: string[];
  primary_subclassification?: string;
  subclassification_confidence?: number;

  // Category mapping for UI
  category_mapping?: Record<string, string>;
}

export interface VaultInfo {
  vault_path: string;
  directories: Record<
    string,
    {
      file_count: number;
      total_size_bytes: number;
      total_size_mb: number;
    }
  >;
}

export interface FileSystemItem {
  name: string;
  displayName: string;
  type: 'folder' | 'file';
  icon?: ReactNode;
  size?: number;
  created?: string;
  documentId?: string;
  status?: string;
  wordCount?: number;
  mimeType?: string;
  primaryTheme?: string;
  themeConfidence?: number;
  subthemes?: string[];
  primarySubtheme?: string;
  subclassifications?: string[];
  primarySubclassification?: string;
  subclassificationConfidence?: number;
  children?: FileSystemItem[];
  itemCount?: number;
  processingCount?: number;

  // Hierarchy information
  hierarchyLevel?: 'theme' | 'category' | 'subclassification';
  useColoredCard?: boolean; // Whether to render as SubthemeCard (colored) or ThemeCard

  // Parent references
  parentTheme?: string;
  parentCategory?: string;
}

export type ViewMode = 'grid' | 'list';

export interface ThemeConfig {
  icon: ReactNode;
  description: string;
}

export interface CategoryConfig {
  icon: ReactNode;
  description?: string;
}

export interface SubthemeStyles {
  bg: string;
  border: string;
  icon: string;
}

export interface CurrentStats {
  folders: number;
  files: number;
  totalDocuments: number; // Total documents including those in subfolders
  totalSize: number;
}

// Location state type for navigation
export interface VaultLocationState {
  navigationPath?: string[];
  displayPath?: string[];
  searchTerm?: string;
  viewMode?: ViewMode;
  from?: string;
  returnPath?: string;
  returnState?: {
    navigationPath: string[];
    displayPath: string[];
    searchTerm: string;
    viewMode: ViewMode;
  };
}
