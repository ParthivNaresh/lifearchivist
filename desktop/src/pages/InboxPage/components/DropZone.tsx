import React from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, CheckCircle2 } from 'lucide-react';
import { cn } from '../../../utils/cn';
import { ACCEPTED_FILE_TYPES, UI_TEXT } from '../constants';

interface DropZoneProps {
  onDrop: (acceptedFiles: File[]) => void;
  onSelectFiles: () => void;
  onSelectFolder: () => void;
  disabled: boolean;
}

export const DropZone: React.FC<DropZoneProps> = ({
  onDrop,
  onSelectFiles,
  onSelectFolder,
  disabled,
}) => {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    disabled,
    accept: ACCEPTED_FILE_TYPES,
  });

  return (
    <div
      {...getRootProps()}
      className={cn(
        'glass-dropzone rounded-xl p-12 text-center cursor-pointer transition-all',
        isDragActive && 'border-primary/60 bg-primary/10 scale-[1.02]',
        disabled && 'opacity-50 cursor-not-allowed'
      )}
    >
      <input {...getInputProps()} />
      
      <div className="flex flex-col items-center space-y-4">
        <div className="relative">
          <div className="absolute inset-0 bg-gradient-to-r from-primary/20 to-purple-500/20 blur-3xl" />
          <Upload className="h-16 w-16 text-muted-foreground relative z-10" />
        </div>
        
        {isDragActive ? (
          <div className="space-y-2">
            <p className="text-xl font-semibold">{UI_TEXT.DROP_ZONE.DRAG_ACTIVE}</p>
            <p className="text-sm text-muted-foreground">
              {UI_TEXT.DROP_ZONE.DRAG_ACTIVE_SUBTITLE}
            </p>
          </div>
        ) : (
          <>
            <div className="space-y-2">
              <p className="text-xl font-semibold">{UI_TEXT.DROP_ZONE.DEFAULT}</p>
              <p className="text-sm text-muted-foreground">
                {UI_TEXT.DROP_ZONE.DEFAULT_SUBTITLE}
              </p>
            </div>
            
            <div className="flex items-center space-x-1 text-xs text-muted-foreground">
              <CheckCircle2 className="h-3 w-3 text-emerald-500" />
              <span>{UI_TEXT.DROP_ZONE.SUPPORTED_FILES}</span>
            </div>
          </>
        )}
        
        <div className="flex space-x-3 pt-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelectFiles();
            }}
            disabled={disabled}
            className="px-6 py-2.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 font-medium"
          >
            {UI_TEXT.BUTTONS.CHOOSE_FILES}
          </button>
          
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelectFolder();
            }}
            disabled={disabled}
            className="px-6 py-2.5 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/90 transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 font-medium"
          >
            {UI_TEXT.BUTTONS.SELECT_FOLDER}
          </button>
        </div>
      </div>
    </div>
  );
};