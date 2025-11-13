import { type SearchResult } from './types';
import { FILE_SIZE_UNITS, MIME_TYPE_ICONS } from './constants';

export interface SearchResultMetadata {
  mime_type?: string;
  size_bytes?: number;
  word_count?: number | null;
  ingested_at?: string | null;
  created_at?: string | null;
  tags?: string[];
  status?: string;
  [key: string]: unknown;
}

export function getMetadata(result: SearchResult): SearchResultMetadata {
  return (result.metadata as SearchResultMetadata) ?? {};
}

export function getMimeType(result: SearchResult): string {
  return getMetadata(result).mime_type ?? 'application/octet-stream';
}

export function getSizeBytes(result: SearchResult): number {
  return getMetadata(result).size_bytes ?? 0;
}

export function getWordCount(result: SearchResult): number | null {
  return getMetadata(result).word_count ?? null;
}

export function getIngestedAt(result: SearchResult): string | null {
  return getMetadata(result).ingested_at ?? null;
}

export function getTags(result: SearchResult): string[] {
  return getMetadata(result).tags ?? [];
}

export function getStatus(result: SearchResult): string {
  return getMetadata(result).status ?? 'unknown';
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + FILE_SIZE_UNITS[i];
}

export function formatDate(dateString: string | null): string {
  if (!dateString) return 'Unknown';
  return new Date(dateString).toLocaleDateString();
}

export function getMimeTypeIcon(mimeType: string): string {
  const defaultIcon = MIME_TYPE_ICONS.default ?? '📄';

  if (mimeType.startsWith('text/')) {
    return MIME_TYPE_ICONS['text/'] ?? defaultIcon;
  }
  if (mimeType === 'application/pdf') {
    return MIME_TYPE_ICONS['application/pdf'] ?? defaultIcon;
  }
  if (mimeType.startsWith('image/')) {
    return MIME_TYPE_ICONS['image/'] ?? defaultIcon;
  }

  return defaultIcon;
}

export function parseTagsFromUrl(urlTags: string | null): string[] {
  if (!urlTags) return [];
  return urlTags
    .split(',')
    .map((tag) => decodeURIComponent(tag.trim()))
    .filter((tag) => tag);
}

export function formatScore(score: number): string {
  return `${(score * 100).toFixed(0)}%`;
}

export function getFileType(mimeType: string): string {
  const parts = mimeType.split('/');
  return parts[1] ?? 'unknown';
}
