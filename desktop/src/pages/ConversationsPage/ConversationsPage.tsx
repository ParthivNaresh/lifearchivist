/**
 * Conversations Page - Main chat interface
 */

import { useState } from 'react';
import { Trash2, X } from 'lucide-react';
import { useConversations, useConversation } from './hooks';
import { conversationsApi } from './api';
import { ConversationList } from './components/ConversationList';
import { MessageList } from './components/MessageList';
import { MessageInput } from './components/MessageInput';
import { EditableTitle } from './components/EditableTitle';

const ConversationsPage: React.FC = () => {
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const {
    conversations,
    setConversations,
    loading: conversationsLoading,
    error: _conversationsError,
    createConversation,
    deleteConversation,
  } = useConversations();

  const {
    conversation,
    messages,
    loading: conversationLoading,
    sending,
    error: conversationError,
    sendMessage: _sendMessage,
    sendMessageStreaming,
    reload: reloadConversation,
  } = useConversation(selectedConversationId);

  const handleNewConversation = async () => {
    try {
      const newConv = await createConversation('New Conversation');
      setSelectedConversationId(newConv.id);
    } catch (err) {
      console.error('Failed to create conversation:', err);
    }
  };

  const handleDeleteConversation = async (conversationId: string) => {
    try {
      await deleteConversation(conversationId);
      // If deleted conversation was selected, clear selection
      if (selectedConversationId === conversationId) {
        setSelectedConversationId(null);
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  const handleDeleteAllConversations = async () => {
    try {
      // Delete all conversations
      await Promise.all(conversations.map((conv) => deleteConversation(conv.id)));
      // Clear selection
      setSelectedConversationId(null);
    } catch (err) {
      console.error('Failed to delete all conversations:', err);
    }
  };

  const handleSendMessage = async (content: string) => {
    try {
      // Use streaming by default for better UX
      await sendMessageStreaming(content);
    } catch (err) {
      console.error('Failed to send message:', err);
    }
  };

  const handleUpdateTitle = async (conversationId: string, newTitle: string) => {
    try {
      const updated = await conversationsApi.update(conversationId, { title: newTitle });

      // Update conversation list
      setConversations((prev) =>
        prev.map((c) =>
          c.id === conversationId ? { ...c, title: newTitle, updated_at: updated.updated_at } : c
        )
      );

      // Reload current conversation if it's the one being edited
      if (selectedConversationId === conversationId) {
        await reloadConversation();
      }
    } catch (err) {
      console.error('Failed to update title:', err);
      throw err;
    }
  };

  return (
    <div className="h-full flex">
      {/* Conversation List Sidebar */}
      <ConversationList
        conversations={conversations}
        selectedId={selectedConversationId}
        onSelect={setSelectedConversationId}
        onNew={() => void handleNewConversation()}
        onUpdateTitle={handleUpdateTitle}
        onDeleteAll={() => {
          void handleDeleteAllConversations();
        }}
        loading={conversationsLoading}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {selectedConversationId ? (
          <>
            {/* Header */}
            <div className="border-b border-border/30 p-4 bg-background/50 flex items-start justify-between">
              {conversation && (
                <>
                  <div className="flex-1">
                    <EditableTitle
                      value={conversation.title ?? ''}
                      onSave={(newTitle) => handleUpdateTitle(conversation.id, newTitle)}
                      size="lg"
                      placeholder="Untitled Conversation"
                      fullWidth={false}
                    />
                    <p className="text-sm text-muted-foreground mt-1">
                      Model: {conversation.model} • Temperature: {conversation.temperature}
                    </p>
                  </div>
                  <button
                    onClick={() => setDeleteConfirmId(conversation.id)}
                    className="p-2 rounded-md hover:bg-destructive/10 text-destructive transition-colors"
                    title="Delete conversation"
                  >
                    <Trash2 className="h-5 w-5" />
                  </button>
                </>
              )}
            </div>

            {/* Messages */}
            <MessageList messages={messages} loading={conversationLoading} />

            {/* Error Display */}
            {conversationError && (
              <div className="px-4 py-2 bg-destructive/10 text-destructive text-sm">
                {conversationError}
              </div>
            )}

            {/* Input */}
            <MessageInput
              onSend={(content) => void handleSendMessage(content)}
              disabled={sending}
            />
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <p className="text-lg">Select a conversation or create a new one</p>
            </div>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirmId && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-destructive/10 rounded-full">
                <Trash2 className="h-6 w-6 text-destructive" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold mb-2">Delete Conversation</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Are you sure you want to delete this conversation? This action cannot be undone.
                </p>
                <div className="flex gap-3 justify-end">
                  <button
                    onClick={() => setDeleteConfirmId(null)}
                    className="px-4 py-2 text-sm border border-border rounded-md hover:bg-accent transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => {
                      void handleDeleteConversation(deleteConfirmId);
                      setDeleteConfirmId(null);
                    }}
                    className="px-4 py-2 text-sm bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>
              <button
                onClick={() => setDeleteConfirmId(null)}
                className="p-1 hover:bg-accent rounded-md transition-colors"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConversationsPage;
