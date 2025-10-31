import { createContext } from 'react';
import { type UploadQueueContextType } from '../types/upload';

export const UploadQueueContext = createContext<UploadQueueContextType | null>(null);
