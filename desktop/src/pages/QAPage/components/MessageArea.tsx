/**
 * MessageArea component - displays all messages
 */

import { type Message } from '../types';
import { EmptyState } from './EmptyState';
import { MessageBubble } from './MessageBubble';
import { LoadingMessage } from './LoadingMessage';

interface MessageAreaProps {
  messages: Message[];
  isLoading: boolean;
}

export const MessageArea: React.FC<MessageAreaProps> = ({ messages, isLoading }) => {
  return (
    <div className="flex-1 overflow-auto p-6 space-y-4">
      {messages.length === 0 ? (
        <EmptyState />
      ) : (
        <>
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          {isLoading && <LoadingMessage />}
        </>
      )}
    </div>
  );
};
