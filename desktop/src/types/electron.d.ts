export interface FolderFilesResult {
  folderPath: string;
  files: string[];
  fileCount: number;
}

export interface ElectronAPI {
  selectFiles: () => Promise<string[]>;
  selectDirectory: () => Promise<string>;
  selectFolderFiles: () => Promise<FolderFilesResult | null>;
  showInFolder: (filePath: string) => Promise<void>;
  openExternal: (url: string) => Promise<void>;
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}