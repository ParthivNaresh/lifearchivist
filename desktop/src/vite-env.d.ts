/// <reference types="vite/client" />

declare global {
  interface ImportMetaEnv {
    readonly VITE_API_URL?: string;
    // Add other env variables as needed
  }

  interface ImportMeta {
    readonly env: ImportMetaEnv;
  }
}

export {};
