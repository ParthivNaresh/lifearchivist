/**
 * Message list component
 */

import { useEffect, useRef } from 'react';
import { User, Bot, Search, FileCheck, Sparkles } from 'lucide-react';
import { cn } from '../../../utils/cn';
import type { Message, AgentProgress } from '../types';
import { ErrorMessage } from './ErrorMessage';
import { getErrorMetadata } from '../utils/metadata';
import { AgentProgressIndicator } from './AgentProgressIndicator';

interface MessageListProps {
  messages: Message[];
  loading?: boolean;
  agentProgress?: AgentProgress;
  onRetryMessage?: (messageId: string) => void;
}

function isErrorMessage(message: Message): boolean {
  if (!message?.metadata) return false;
  return getErrorMetadata(message.metadata) !== null;
}

interface MessageContentProps {
  message: Message;
}

interface ProcessingIndicatorProps {
  stage?: 'searching' | 'found_sources' | 'generating';
  sourcesFound?: number;
}

interface CitationsListProps {
  citations: Message['citations'];
}

const CitationsList: React.FC<CitationsListProps> = ({ citations }) => {
  if (!citations || citations.length === 0) {
    return null;
  }

  return (
    <div className="mt-3 pt-3 border-t border-border/30">
      <p className="text-xs font-medium mb-2">Sources:</p>
      <div className="space-y-1">
        {citations.map((citation) => (
          <div key={citation.id} className="text-xs opacity-80">
            <span className="font-medium">{citation.document_id}</span>
            {citation.score && (
              <span className="ml-2">({Math.round(citation.score * 100)}% match)</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

const ProcessingIndicator: React.FC<ProcessingIndicatorProps> = ({ stage, sourcesFound }) => {
  const getStageContent = () => {
    switch (stage) {
      case 'searching':
        return (
          <>
            <Search className="h-4 w-4 animate-pulse" />
            <span>Searching your documents...</span>
          </>
        );
      case 'found_sources':
        return (
          <>
            <FileCheck className="h-4 w-4" />
            <span>
              Found {sourcesFound ?? 0} {sourcesFound === 1 ? 'source' : 'sources'}
            </span>
          </>
        );
      case 'generating':
        return (
          <>
            <Sparkles className="h-4 w-4 animate-pulse" />
            <span>Generating response</span>
            <span className="flex gap-1">
              <span className="animate-bounce" style={{ animationDelay: '0ms' }}>
                ●
              </span>
              <span className="animate-bounce" style={{ animationDelay: '150ms' }}>
                ●
              </span>
              <span className="animate-bounce" style={{ animationDelay: '300ms' }}>
                ●
              </span>
            </span>
          </>
        );
      default:
        return (
          <>
            <Bot className="h-4 w-4 animate-pulse" />
            <span>Processing</span>
            <span className="flex gap-1">
              <span className="animate-bounce" style={{ animationDelay: '0ms' }}>
                ●
              </span>
              <span className="animate-bounce" style={{ animationDelay: '150ms' }}>
                ●
              </span>
              <span className="animate-bounce" style={{ animationDelay: '300ms' }}>
                ●
              </span>
            </span>
          </>
        );
    }
  };

  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">{getStageContent()}</div>
  );
};

const ProcessingMessageView: React.FC<MessageContentProps> = ({ message }) => {
  const sourcesFound =
    typeof message.metadata === 'object' &&
    message.metadata !== null &&
    'sources_found' in message.metadata
      ? Number(message.metadata.sources_found)
      : undefined;

  return (
    <div className="max-w-[70%] rounded-lg p-4 bg-accent text-accent-foreground">
      <ProcessingIndicator stage={message.stage} sourcesFound={sourcesFound} />
      <CitationsList citations={message.citations} />
    </div>
  );
};

const CompletedMessageView: React.FC<MessageContentProps> = ({ message }) => {
  return (
    <div
      className={cn(
        'max-w-[70%] rounded-lg p-4',
        message.role === 'user'
          ? 'bg-primary text-primary-foreground'
          : 'bg-accent text-accent-foreground'
      )}
    >
      {message.content && <p className="whitespace-pre-wrap break-words">{message.content}</p>}

      {message.status === 'processing' && message.content && (
        <div className="mt-2 flex items-center gap-2 text-xs opacity-70">
          <ProcessingIndicator stage={message.stage} />
        </div>
      )}

      {message.status !== 'processing' && (
        <div className="mt-2 flex items-center gap-3 text-xs opacity-70">
          <span>{new Date(message.created_at).toLocaleTimeString()}</span>
          {message.latency_ms && <span>{message.latency_ms}ms</span>}
          {message.confidence !== null && message.confidence !== undefined && (
            <span>{Math.round(message.confidence * 100)}% confidence</span>
          )}
        </div>
      )}

      <CitationsList citations={message.citations} />
    </div>
  );
};

const MessageContent: React.FC<MessageContentProps> = ({ message }) => {
  const isError = isErrorMessage(message);

  if (isError) {
    return <ErrorMessage message={message} />;
  }

  if (message.status === 'processing' && !message.content) {
    return <ProcessingMessageView message={message} />;
  }

  return <CompletedMessageView message={message} />;
};

interface AgentProgressMessageProps {
  progress: AgentProgress;
}

const AgentProgressMessage: React.FC<AgentProgressMessageProps> = ({ progress }) => {
  return (
    <div className="flex gap-3 justify-start">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
        <Bot className="h-5 w-5 text-primary" />
      </div>
      <AgentProgressIndicator progress={progress} />
    </div>
  );
};

const hasActiveAgentProgress = (progress: AgentProgress | undefined): boolean => {
  if (!progress) return false;
  return progress.phases.length > 0 || progress.isSynthesizing;
};

export const MessageList: React.FC<MessageListProps> = ({ messages, loading, agentProgress }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, agentProgress]);

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

  const showAgentProgress = hasActiveAgentProgress(agentProgress);
  const lastMessage = messages[messages.length - 1];
  const isLastMessageProcessing = lastMessage?.status === 'processing' && !lastMessage?.content;

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.filter(Boolean).map((message, index) => {
        const isError = isErrorMessage(message);
        const isLastProcessingMessage =
          index === messages.length - 1 && message.status === 'processing' && !message.content;

        if (isLastProcessingMessage && showAgentProgress) {
          return null;
        }

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

            <MessageContent message={message} />

            {message.role === 'user' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                <User className="h-5 w-5 text-primary-foreground" />
              </div>
            )}
          </div>
        );
      })}

      {showAgentProgress && isLastMessageProcessing && agentProgress && (
        <AgentProgressMessage progress={agentProgress} />
      )}

      <div ref={bottomRef} />
    </div>
  );
};
