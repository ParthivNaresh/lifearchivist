/**
 * Type definitions for InboxPage
 */

export interface FileFormat {
  category: string;
  categoryIcon: string;
  categoryColor: string;
  formats: FormatItem[];
}

export interface FormatItem {
  name: string;
  extensions: string;
  isNew?: boolean;
}

export interface AcceptedFileTypes {
  [mimeType: string]: string[];
}

export interface UploadOptions {
  batchName: string;
}