/**
 * Utility functions for InboxPage
 */

/**
 * Format file size for display
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

/**
 * Get file extension from filename
 */
export const getFileExtension = (filename: string): string => {
  const parts = filename.split('.');
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
};

/**
 * Check if file type is supported
 */
export const isFileTypeSupported = (filename: string, acceptedExtensions: string[]): boolean => {
  const extension = getFileExtension(filename);
  return acceptedExtensions.some(ext => ext.toLowerCase() === extension);
};

/**
 * Generate batch name from files
 */
export const generateBatchName = (files: File[]): string => {
  if (files.length === 0) return 'Empty batch';
  if (files.length === 1) return files[0].name;
  return `${files.length} files`;
};

/**
 * Calculate total size of files
 */
export const calculateTotalSize = (files: File[]): number => {
  return files.reduce((total, file) => total + (file.size || 0), 0);
};

/**
 * Group files by extension
 */
export const groupFilesByExtension = (files: File[]): Record<string, File[]> => {
  return files.reduce((groups, file) => {
    const ext = getFileExtension(file.name);
    if (!groups[ext]) {
      groups[ext] = [];
    }
    groups[ext].push(file);
    return groups;
  }, {} as Record<string, File[]>);
};

/**
 * Validate file size
 */
export const validateFileSize = (file: File, maxSizeMB: number): boolean => {
  const maxSizeBytes = maxSizeMB * 1024 * 1024;
  return file.size <= maxSizeBytes;
};

/**
 * Get file type category
 */
export const getFileTypeCategory = (filename: string): string => {
  const ext = getFileExtension(filename);
  
  const categories: Record<string, string[]> = {
    'Documents': ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt'],
    'Spreadsheets': ['xls', 'xlsx', 'csv', 'ods'],
    'Presentations': ['ppt', 'pptx', 'odp'],
    'Images': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp'],
    'Archives': ['zip', 'rar', '7z', 'tar', 'gz'],
  };
  
  for (const [category, extensions] of Object.entries(categories)) {
    if (extensions.includes(ext)) {
      return category;
    }
  }
  
  return 'Other';
};