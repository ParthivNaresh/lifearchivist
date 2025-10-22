/**
 * API functions for conversations
 */

import type {
  Conversation,
  ConversationListResponse,
  ConversationResponse,
  CreateConversationRequest,
  MessageListResponse,
  SendMessageRequest,
  SendMessageResponse,
  SSECallbacks,
  SSEUserMessageEvent,
  SSEIntentCheckEvent,
  SSESourceEvent,
  SSEChunkEvent,
  SSEMetadataEvent,
  SSECompleteEvent,
  SSEErrorEvent,
} from './types';

const API_BASE = 'http://localhost:8000/api';

export const conversationsApi = {
  /**
   * Create a new conversation
   */
  async create(data: CreateConversationRequest): Promise<Conversation> {
    const response = await fetch(`${API_BASE}/conversations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`Failed to create conversation: ${response.statusText}`);
    }

    const result = (await response.json()) as ConversationResponse;
    return result.conversation;
  },

  /**
   * List conversations
   */
  async list(params?: {
    limit?: number;
    offset?: number;
    include_archived?: boolean;
  }): Promise<ConversationListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());
    if (params?.include_archived) searchParams.set('include_archived', 'true');

    const response = await fetch(`${API_BASE}/conversations?${searchParams.toString()}`);

    if (!response.ok) {
      throw new Error(`Failed to list conversations: ${response.statusText}`);
    }

    return response.json() as Promise<ConversationListResponse>;
  },

  /**
   * Get a single conversation
   */
  async get(
    conversationId: string,
    params?: { include_messages?: boolean; message_limit?: number }
  ): Promise<Conversation> {
    const searchParams = new URLSearchParams();
    if (params?.include_messages !== undefined) {
      searchParams.set('include_messages', params.include_messages.toString());
    }
    if (params?.message_limit) {
      searchParams.set('message_limit', params.message_limit.toString());
    }

    const response = await fetch(
      `${API_BASE}/conversations/${conversationId}?${searchParams.toString()}`
    );

    if (!response.ok) {
      throw new Error(`Failed to get conversation: ${response.statusText}`);
    }

    const result = (await response.json()) as ConversationResponse;
    return result.conversation;
  },

  /**
   * Send a message in a conversation
   */
  async sendMessage(
    conversationId: string,
    data: SendMessageRequest
  ): Promise<SendMessageResponse> {
    const response = await fetch(`${API_BASE}/conversations/${conversationId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`Failed to send message: ${response.statusText}`);
    }

    return response.json() as Promise<SendMessageResponse>;
  },

  /**
   * Send a message with streaming response using Server-Sent Events
   */
  async sendMessageStreaming(
    conversationId: string,
    data: SendMessageRequest,
    callbacks: SSECallbacks,
    signal?: AbortSignal
  ): Promise<void> {
    const response = await fetch(`${API_BASE}/conversations/${conversationId}/messages/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is null');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { value, done } = await reader.read();

        if (done) break;

        // Decode chunk and add to buffer
        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? ''; // Keep incomplete line in buffer

        let currentEvent = '';
        let currentData = '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.substring(7).trim();
          } else if (line.startsWith('data: ')) {
            currentData = line.substring(6);

            // Process the event when we have both event and data
            if (currentEvent && currentData) {
              try {
                // Parse data based on event type for proper typing
                switch (currentEvent) {
                  case 'user_message': {
                    const data = JSON.parse(currentData) as SSEUserMessageEvent;
                    callbacks.onUserMessage?.(data);
                    break;
                  }
                  case 'intent_check': {
                    const data = JSON.parse(currentData) as SSEIntentCheckEvent;
                    callbacks.onIntentCheck?.(data);
                    break;
                  }
                  case 'sources': {
                    const data = JSON.parse(currentData) as SSESourceEvent[];
                    callbacks.onSources?.(data);
                    break;
                  }
                  case 'chunk': {
                    const data = JSON.parse(currentData) as SSEChunkEvent;
                    callbacks.onChunk?.(data.text);
                    // Yield to event loop to allow React to render
                    await new Promise((resolve) => setTimeout(resolve, 0));
                    break;
                  }
                  case 'metadata': {
                    const data = JSON.parse(currentData) as SSEMetadataEvent;
                    callbacks.onMetadata?.(data);
                    break;
                  }
                  case 'complete': {
                    const data = JSON.parse(currentData) as SSECompleteEvent;
                    callbacks.onComplete?.(data);
                    break;
                  }
                  case 'error': {
                    const data = JSON.parse(currentData) as SSEErrorEvent;
                    callbacks.onError?.(data.error ?? 'Unknown error');
                    return;
                  }
                  default:
                    console.warn(`Unknown SSE event type: ${currentEvent}`);
                }
              } catch (parseError) {
                console.error('Failed to parse SSE data:', parseError);
              }

              currentEvent = '';
              currentData = '';
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },

  /**
   * Get messages for a conversation
   */
  async getMessages(
    conversationId: string,
    params?: {
      limit?: number;
      offset?: number;
      include_citations?: boolean;
    }
  ): Promise<MessageListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());
    if (params?.include_citations !== undefined) {
      searchParams.set('include_citations', params.include_citations.toString());
    }

    const response = await fetch(
      `${API_BASE}/conversations/${conversationId}/messages?${searchParams.toString()}`
    );

    if (!response.ok) {
      throw new Error(`Failed to get messages: ${response.statusText}`);
    }

    return response.json() as Promise<MessageListResponse>;
  },

  /**
   * Update a conversation
   */
  async update(
    conversationId: string,
    data: {
      title?: string;
      context_documents?: string[];
      system_prompt?: string;
      temperature?: number;
      max_tokens?: number;
    }
  ): Promise<Conversation> {
    const response = await fetch(`${API_BASE}/conversations/${conversationId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`Failed to update conversation: ${response.statusText}`);
    }

    const result = (await response.json()) as ConversationResponse;
    return result.conversation;
  },

  /**
   * Archive a conversation
   */
  async archive(conversationId: string): Promise<Conversation> {
    const response = await fetch(`${API_BASE}/conversations/${conversationId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error(`Failed to archive conversation: ${response.statusText}`);
    }

    const result = (await response.json()) as ConversationResponse;
    return result.conversation;
  },
};
