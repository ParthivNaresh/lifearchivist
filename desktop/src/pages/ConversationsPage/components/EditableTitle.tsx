/**
 * Inline editable title component
 */

import { useState, useRef, useEffect } from 'react';
import { cn } from '../../../utils/cn';

interface EditableTitleProps {
  value: string;
  onSave: (newTitle: string) => Promise<void>;
  className?: string;
  placeholder?: string;
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
}

const SHARED_STYLES = {
  padding: '0.25rem 0',
  margin: 0,
  height: '1.75rem',
  lineHeight: '1.25rem',
} as const;

const SIZE_CLASSES = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg font-semibold',
} as const;

export const EditableTitle: React.FC<EditableTitleProps> = ({
  value,
  onSave,
  className,
  placeholder = 'Untitled',
  size = 'md',
  fullWidth = false,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value);
  const [isSaving, setIsSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setEditValue(value);
  }, [value]);

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleSave = async () => {
    const trimmed = editValue.trim();

    if (!trimmed || trimmed === value) {
      setIsEditing(false);
      setEditValue(value);
      return;
    }

    setIsSaving(true);
    try {
      await onSave(trimmed);
      setIsEditing(false);
    } catch (err) {
      console.error('Failed to save title:', err);
      setEditValue(value);
    } finally {
      setIsSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      void handleSave();
    } else if (e.key === 'Escape') {
      setEditValue(value);
      setIsEditing(false);
    }
  };

  if (isEditing) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => void handleSave()}
        disabled={isSaving}
        size={Math.max(editValue.length, placeholder.length, 20)}
        className={cn(
          'border border-border/50 rounded bg-background',
          'focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/50',
          'disabled:opacity-50 max-w-full',
          SIZE_CLASSES[size],
          className
        )}
        style={{
          ...SHARED_STYLES,
          paddingLeft: '0.5rem',
          paddingRight: '0.5rem',
          verticalAlign: 'baseline',
        }}
        placeholder={placeholder}
      />
    );
  }

  return (
    <div
      className={cn(
        'cursor-text hover:bg-accent/30 rounded border border-transparent transition-colors truncate',
        fullWidth ? 'w-full' : 'inline-block',
        className
      )}
      style={{ ...SHARED_STYLES, display: 'inline-flex', alignItems: 'center' }}
      onClick={() => setIsEditing(true)}
    >
      <span className={SIZE_CLASSES[size]}>{value || placeholder}</span>
    </div>
  );
};
