/**
 * Conversation list sidebar component
 */

import { useState } from 'react';
import { MessageCircle, Plus, Settings } from 'lucide-react';
import { cn } from '../../../utils/cn';
import { EditableTitle } from './EditableTitle';
import { ConversationSettingsModal } from './ConversationSettingsModal/index';
import type { Conversation } from '../types';

interface ConversationListProps {
  conversations: Conversation[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onUpdateTitle: (id: string, title: string) => Promise<void>;
  onDeleteAll: () => void;
  loading?: boolean;
}

export const ConversationList: React.FC<ConversationListProps> = ({
  conversations,
  selectedId,
  onSelect,
  onNew,
  onUpdateTitle,
  onDeleteAll,
  loading,
}) => {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="w-80 border-r border-border/30 flex flex-col bg-background/50">
      {/* Header */}
      <div className="p-4 border-b border-border/30">
        <button
          onClick={onNew}
          className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          <span>New Conversation</span>
        </button>
      </div>

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto">
        {(() => {
          if (loading) {
            return (
              <div className="p-4 text-center text-muted-foreground">Loading conversations...</div>
            );
          }

          if (conversations.length === 0) {
            return (
              <div className="p-4 text-center text-muted-foreground">
                <MessageCircle className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>No conversations yet</p>
                <p className="text-sm mt-1">Click &ldquo;New Conversation&rdquo; to start</p>
              </div>
            );
          }

          return (
            <ul className="p-2 space-y-1 list-none">
              {conversations.map((conversation) => (
                <li
                  key={conversation.id}
                  className={cn(
                    'group relative rounded-md transition-colors',
                    selectedId === conversation.id
                      ? 'bg-accent text-accent-foreground'
                      : 'hover:bg-accent/50'
                  )}
                >
                  <button
                    className="w-full p-3 pr-10 cursor-pointer text-left focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded-md"
                    onClick={() => onSelect(conversation.id)}
                    aria-label={`Select conversation: ${conversation.title ?? 'New Conversation'}`}
                    aria-current={selectedId === conversation.id ? 'true' : 'false'}
                  >
                    <div className="flex items-start justify-between mb-1">
                      <div className="flex-1 min-w-0">
                        {selectedId === conversation.id ? (
                          <div onClick={(e) => e.stopPropagation()}>
                            <EditableTitle
                              value={conversation.title ?? ''}
                              onSave={(newTitle) => onUpdateTitle(conversation.id, newTitle)}
                              size="sm"
                              placeholder="New Conversation"
                              className="font-medium"
                              fullWidth
                            />
                          </div>
                        ) : (
                          <div
                            className="truncate px-2 py-1"
                            style={{
                              height: '1.75rem',
                              display: 'flex',
                              alignItems: 'center',
                            }}
                          >
                            <span className="font-medium text-sm">
                              {conversation.title ?? 'New Conversation'}
                            </span>
                          </div>
                        )}
                      </div>
                      {conversation.message_count !== undefined && (
                        <span className="text-xs text-muted-foreground ml-2">
                          {conversation.message_count}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground px-2">
                      {formatDate(conversation.updated_at)}
                    </p>
                  </button>
                </li>
              ))}
            </ul>
          );
        })()}
      </div>

      {/* Settings Button */}
      <div className="p-4 border-t border-border/30">
        <button
          onClick={() => setSettingsOpen(true)}
          className="w-full flex items-center justify-center space-x-2 px-4 py-2 border border-border rounded-md hover:bg-accent transition-colors"
        >
          <Settings className="h-4 w-4" />
          <span>Settings</span>
        </button>
      </div>

      {/* Settings Modal */}
      <ConversationSettingsModal
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        onDeleteAllConversations={onDeleteAll}
      />
    </div>
  );
};
