/**
 * Message list component
 */

import { useEffect, useRef } from 'react';
import { User, Bot } from 'lucide-react';
import { cn } from '../../../utils/cn';
import type { Message } from '../types';
import { ErrorMessage } from './ErrorMessage';

interface MessageListProps {
  messages: Message[];
  loading?: boolean;
  onRetryMessage?: (messageId: string) => void;
}

function isErrorMessage(message: Message): boolean {
  if (!message?.metadata) return false;
  const metadata = typeof message.metadata === 'string' 
    ? JSON.parse(message.metadata) 
    : message.metadata;
  return metadata?.is_error === true;
}

export const MessageList: React.FC<MessageListProps> = ({ messages, loading }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        Loading messages...
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <div className="text-center">
          <Bot className="h-16 w-16 mx-auto mb-4 opacity-50" />
          <p className="text-lg">Start a conversation</p>
          <p className="text-sm mt-2">Ask a question about your documents</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.filter(Boolean).map((message) => {
        const isError = isErrorMessage(message);

        return (
          <div
            key={message.id}
            className={cn('flex gap-3', message.role === 'user' ? 'justify-end' : 'justify-start')}
          >
            {message.role === 'assistant' && !isError && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="h-5 w-5 text-primary" />
              </div>
            )}

            {isError ? (
              <ErrorMessage message={message} />
            ) : (
              <div
                className={cn(
                  'max-w-[70%] rounded-lg p-4',
                  message.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-accent text-accent-foreground'
                )}
              >
                <p className="whitespace-pre-wrap break-words">{message.content}</p>

                <div className="mt-2 flex items-center gap-3 text-xs opacity-70">
                  <span>{new Date(message.created_at).toLocaleTimeString()}</span>
                  {message.latency_ms && <span>{message.latency_ms}ms</span>}
                  {message.confidence !== null && message.confidence !== undefined && (
                    <span>{Math.round(message.confidence * 100)}% confidence</span>
                  )}
                </div>

                {message.citations && message.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-border/30">
                    <p className="text-xs font-medium mb-2">Sources:</p>
                    <div className="space-y-1">
                      {message.citations.map((citation) => (
                        <div key={citation.id} className="text-xs opacity-80">
                          <span className="font-medium">{citation.document_id}</span>
                          {citation.score && (
                            <span className="ml-2">({Math.round(citation.score * 100)}% match)</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {message.role === 'user' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                <User className="h-5 w-5 text-primary-foreground" />
              </div>
            )}
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
};
