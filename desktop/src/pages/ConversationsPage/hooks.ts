/**
 * React hooks for conversations
 */

import { useState, useEffect, useCallback } from 'react';
import { conversationsApi } from './api';
import { useConversationWebSocket } from '../../hooks/useConversationWebSocket';
import type {
  Conversation,
  Message,
  SendMessageRequest,
  Citation,
  AgentProgress,
  SSEAgentProgressEvent,
} from './types';

const initialAgentProgress: AgentProgress = {
  phases: [],
  currentPhaseIndex: -1,
  completedPhases: [],
  isSynthesizing: false,
  lastEvent: null,
  error: null,
};

/**
 * Hook to manage conversations list
 */
export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadConversations = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await conversationsApi.list({ limit: 50 });
      const userConversations = result.conversations.filter((c) => c.model !== 'system');
      setConversations(userConversations);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversations');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  const createConversation = useCallback(
    async (title?: string, providerId?: string, model?: string) => {
      try {
        const conversation = await conversationsApi.create({
          title,
          provider_id: providerId,
          model,
        });
        setConversations((prev) => [conversation, ...prev]);
        return conversation;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to create conversation');
        throw err;
      }
    },
    []
  );

  const deleteConversation = useCallback(async (conversationId: string) => {
    try {
      await conversationsApi.archive(conversationId);
      setConversations((prev) => prev.filter((c) => c.id !== conversationId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete conversation');
      throw err;
    }
  }, []);

  return {
    conversations,
    setConversations,
    loading,
    error,
    reload: loadConversations,
    createConversation,
    deleteConversation,
  };
}

/**
 * Hook to manage a single conversation
 */
export function useConversation(conversationId: string | null) {
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agentProgress, setAgentProgress] = useState<AgentProgress>(initialAgentProgress);

  const resetAgentProgress = useCallback(() => {
    setAgentProgress(initialAgentProgress);
  }, []);

  const handleAgentProgress = useCallback((event: SSEAgentProgressEvent) => {
    setAgentProgress({
      phases: event.phases,
      currentPhaseIndex: event.current_phase_index,
      completedPhases: event.completed_phases,
      isSynthesizing: event.is_synthesizing,
      lastEvent: event.event,
      error: event.error,
    });
  }, []);

  const handleMessageStatusUpdate = useCallback(
    (update: {
      message_id: string;
      status: 'processing' | 'completed' | 'failed' | 'cancelled';
      stage?: 'searching' | 'found_sources' | 'generating';
      content?: string;
      metadata?: Record<string, unknown>;
    }) => {
      setMessages((prev) =>
        prev.map((m): Message => {
          if (m.id === update.message_id) {
            const updates: Partial<Message> = {
              status: update.status,
            };

            if (update.stage !== undefined) {
              updates.stage = update.stage;
            }

            if (update.content !== undefined) {
              updates.content = update.content;
            }

            if (update.metadata !== undefined) {
              const currentMetadata = typeof m.metadata === 'string' ? {} : m.metadata || {};

              updates.metadata = { ...currentMetadata, ...update.metadata } as typeof m.metadata;
            }

            return {
              ...m,
              ...updates,
            };
          }
          return m;
        })
      );
    },
    []
  );

  useConversationWebSocket({
    conversationId,
    onMessageStatusUpdate: handleMessageStatusUpdate,
    onError: (err) => {
      console.error('WebSocket error:', err);
    },
    enabled: conversationId !== null,
  });

  const loadConversation = useCallback(async () => {
    if (!conversationId) return;

    try {
      setLoading(true);
      setError(null);
      const conv = await conversationsApi.get(conversationId, {
        include_messages: true,
        message_limit: 100,
      });
      setConversation(conv);
      setMessages(conv.messages ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversation');
    } finally {
      setLoading(false);
    }
  }, [conversationId]);

  useEffect(() => {
    void loadConversation();
  }, [loadConversation]);

  const sendMessage = useCallback(
    async (content: string, contextLimit = 5) => {
      if (!conversationId) return;

      const optimisticUserMessage: Message = {
        id: `temp-${Date.now()}`,
        conversation_id: conversationId,
        parent_message_id: null,
        sequence_number: messages.length,
        role: 'user',
        content,
        status: 'completed',
        model: null,
        confidence: null,
        method: null,
        tokens_used: null,
        latency_ms: null,
        created_at: new Date().toISOString(),
        edited_at: null,
        metadata: {},
      };

      setMessages((prev) => [...prev, optimisticUserMessage]);

      try {
        setSending(true);
        setError(null);

        const request: SendMessageRequest = {
          content,
          context_limit: contextLimit,
        };

        const response = await conversationsApi.sendMessage(conversationId, request);

        setMessages((prev) => [
          ...prev.filter((m) => m.id !== optimisticUserMessage.id),
          response.user_message,
          response.assistant_message,
        ]);

        if (messages.length === 0 && conversation) {
          const shouldUpdateTitle =
            !conversation.title ||
            conversation.title === 'New Conversation' ||
            conversation.title.trim() === '';

          if (shouldUpdateTitle) {
            const generatedTitle = content.length > 50 ? content.substring(0, 47) + '...' : content;

            conversationsApi
              .update(conversationId, { title: generatedTitle })
              .then((updated) => {
                setConversation(updated);
              })
              .catch((err) => {
                console.warn('Failed to update conversation title:', err);
              });
          }
        }

        return response;
      } catch (err) {
        setMessages((prev) => prev.filter((m) => m.id !== optimisticUserMessage.id));
        setError(err instanceof Error ? err.message : 'Failed to send message');
        throw err;
      } finally {
        setSending(false);
      }
    },
    [conversationId, messages.length, conversation]
  );

  const sendMessageStreaming = useCallback(
    async (content: string, contextLimit = 5) => {
      if (!conversationId) return;

      const abortController = new AbortController();

      resetAgentProgress();

      const optimisticUserMessage: Message = {
        id: `temp-user-${Date.now()}`,
        conversation_id: conversationId,
        parent_message_id: null,
        sequence_number: messages.length,
        role: 'user',
        content,
        status: 'completed',
        model: null,
        confidence: null,
        method: null,
        tokens_used: null,
        latency_ms: null,
        created_at: new Date().toISOString(),
        edited_at: null,
        metadata: {},
      };

      const streamingAssistantMessage: Message = {
        id: `temp-assistant-${Date.now()}`,
        conversation_id: conversationId,
        parent_message_id: null,
        sequence_number: messages.length + 1,
        role: 'assistant',
        content: '',
        status: 'processing',
        model: null,
        confidence: null,
        method: null,
        tokens_used: null,
        latency_ms: null,
        created_at: new Date().toISOString(),
        edited_at: null,
        metadata: {},
      };

      const originalUserTempId = optimisticUserMessage.id;
      const originalAssistantTempId = streamingAssistantMessage.id;

      let currentUserRealId: string | null = null;
      let currentAssistantRealId: string | null = null;

      setMessages((prev) => [...prev, optimisticUserMessage, streamingAssistantMessage]);

      try {
        setSending(true);
        setError(null);

        const request: SendMessageRequest = {
          content,
          context_limit: contextLimit,
        };

        await conversationsApi.sendMessageStreaming(
          conversationId,
          request,
          {
            onUserMessage: (userMsg) => {
              currentUserRealId = userMsg.id;
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === originalUserTempId
                    ? { ...m, id: userMsg.id, created_at: userMsg.created_at }
                    : m
                )
              );
            },
            onAssistantMessageCreated: (data) => {
              currentAssistantRealId = data.id;
              setMessages((prev) =>
                prev.map((m) => (m.id === originalAssistantTempId ? { ...m, id: data.id } : m))
              );
            },
            onAgentProgress: handleAgentProgress,
            onChunk: (text) => {
              const targetId = currentAssistantRealId ?? originalAssistantTempId;
              setMessages((prev) =>
                prev.map((m) => (m.id === targetId ? { ...m, content: m.content + text } : m))
              );
            },
            onSources: (sources) => {
              const targetId = currentAssistantRealId ?? originalAssistantTempId;
              const citations: Citation[] = sources.map((source, index) => ({
                id: `temp-citation-${index}`,
                message_id: targetId,
                document_id: source.document_id,
                chunk_id: source.chunk_id,
                score: source.relevance_score,
                snippet: source.text_snippet,
                position: index,
                created_at: new Date().toISOString(),
              }));

              setMessages((prev) => prev.map((m) => (m.id === targetId ? { ...m, citations } : m)));
            },
            onComplete: (data) => {
              resetAgentProgress();

              const { user_message: userMsg, assistant_message: assistantMsg } = data;

              if (userMsg && assistantMsg) {
                setMessages((prev) => {
                  const withoutTemp = prev.filter(
                    (m) =>
                      m.id !== originalUserTempId &&
                      m.id !== originalAssistantTempId &&
                      m.id !== currentUserRealId &&
                      m.id !== currentAssistantRealId &&
                      m.id !== userMsg.id &&
                      m.id !== assistantMsg.id
                  );
                  return [...withoutTemp, userMsg, assistantMsg];
                });
              } else {
                void loadConversation();
              }

              if (messages.length === 0 && conversation) {
                const shouldUpdateTitle =
                  !conversation.title ||
                  conversation.title === 'New Conversation' ||
                  conversation.title.trim() === '';

                if (shouldUpdateTitle) {
                  const generatedTitle =
                    content.length > 50 ? content.substring(0, 47) + '...' : content;

                  conversationsApi
                    .update(conversationId, { title: generatedTitle })
                    .then((updated) => {
                      setConversation(updated);
                    })
                    .catch((err) => {
                      console.warn('Failed to update conversation title:', err);
                    });
                }
              }
            },
            onError: (_errorMsg) => {
              resetAgentProgress();
              const assistantIdToRemove = currentAssistantRealId ?? originalAssistantTempId;
              setMessages((prev) => prev.filter((m) => m.id !== assistantIdToRemove));
              void loadConversation();
            },
          },
          abortController.signal
        );
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          console.log('Stream aborted by user');
          return;
        }

        setMessages((prev) =>
          prev.filter(
            (m) =>
              m.id !== originalUserTempId &&
              m.id !== originalAssistantTempId &&
              m.id !== currentUserRealId &&
              m.id !== currentAssistantRealId
          )
        );
        setError(err instanceof Error ? err.message : 'Failed to send message');
        throw err;
      } finally {
        setSending(false);
      }

      return () => abortController.abort();
    },
    [
      conversationId,
      messages.length,
      conversation,
      loadConversation,
      resetAgentProgress,
      handleAgentProgress,
    ]
  );

  return {
    conversation,
    messages,
    loading,
    sending,
    error,
    agentProgress,
    sendMessage,
    sendMessageStreaming,
    reload: loadConversation,
  };
}
