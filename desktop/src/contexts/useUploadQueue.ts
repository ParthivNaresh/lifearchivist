import { useContext } from 'react';
import { UploadQueueContext } from './UploadQueueContextDef';
import { type UploadQueueContextType } from '../types/upload';

export const useUploadQueue = (): UploadQueueContextType => {
  const context = useContext(UploadQueueContext);
  if (!context) {
    throw new Error('useUploadQueue must be used within an UploadQueueProvider');
  }
  return context;
};
