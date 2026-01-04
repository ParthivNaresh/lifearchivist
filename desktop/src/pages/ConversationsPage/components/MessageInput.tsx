/**
 * Message input component
 */

import { useState, useRef, useEffect } from 'react';
import { Send, Square } from 'lucide-react';

interface MessageInputProps {
  onSend: (message: string) => void;
  onCancel?: () => void;
  disabled?: boolean;
  isSending?: boolean;
  placeholder?: string;
}

export const MessageInput: React.FC<MessageInputProps> = ({
  onSend,
  onCancel,
  disabled,
  isSending = false,
  placeholder = 'Ask a question about your documents...',
}) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled && !isSending) {
      onSend(message.trim());
      setMessage('');
    }
  };

  const handleCancel = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onCancel?.();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
    if (e.key === 'Escape' && isSending) {
      e.preventDefault();
      onCancel?.();
    }
  };

  const isInputDisabled = disabled || isSending;
  const canSubmit = message.trim().length > 0 && !isInputDisabled;

  return (
    <form onSubmit={handleSubmit} className="border-t border-border/30 p-4 bg-background/50">
      <div className="flex gap-2">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isSending ? 'Processing...' : placeholder}
          disabled={isInputDisabled}
          rows={1}
          className="flex-1 resize-none rounded-md border border-border bg-background px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed max-h-32"
        />
        {isSending ? (
          <button
            type="button"
            onClick={handleCancel}
            className="px-4 py-3 bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90 transition-colors flex items-center gap-2"
            title="Cancel request (Esc)"
          >
            <Square className="h-4 w-4 fill-current" />
            <span className="sr-only">Cancel</span>
          </button>
        ) : (
          <button
            type="submit"
            disabled={!canSubmit}
            className="px-4 py-3 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            title="Send message (Enter)"
          >
            <Send className="h-5 w-5" />
          </button>
        )}
      </div>
      <p className="text-xs text-muted-foreground mt-2">
        {isSending
          ? 'Press Esc or click Stop to cancel'
          : 'Press Enter to send, Shift+Enter for new line'}
      </p>
    </form>
  );
};
