import apiClient from '../../utils/api-client';
import type {
  Conversation,
  ConversationListResponse,
  ConversationResponse,
  CreateConversationRequest,
  UpdateConversationRequest,
  MessageListResponse,
  SendMessageRequest,
  SendMessageResponse,
  SSECallbacks,
  SSEUserMessageEvent,
  SSEIntentEvent,
  SSEContextEvent,
  SSESourceEvent,
  SSEChunkEvent,
  SSEMetadataEvent,
  SSECompleteEvent,
  SSEErrorEvent,
} from './types';

export const conversationsApi = {
  async create(data: CreateConversationRequest): Promise<Conversation> {
    const result = await apiClient.post<ConversationResponse>('/api/conversations', data);
    return result.conversation;
  },

  async list(params?: {
    limit?: number;
    offset?: number;
    include_archived?: boolean;
  }): Promise<ConversationListResponse> {
    return await apiClient.get<ConversationListResponse>('/api/conversations', { params });
  },

  async get(
    conversationId: string,
    params?: { include_messages?: boolean; message_limit?: number }
  ): Promise<Conversation> {
    const result = await apiClient.get<ConversationResponse>(
      `/api/conversations/${conversationId}`,
      { params }
    );
    return result.conversation;
  },

  async sendMessage(
    conversationId: string,
    data: SendMessageRequest
  ): Promise<SendMessageResponse> {
    return await apiClient.post<SendMessageResponse>(
      `/api/conversations/${conversationId}/messages`,
      data
    );
  },

  async sendMessageStreaming(
    conversationId: string,
    data: SendMessageRequest,
    callbacks: SSECallbacks,
    signal?: AbortSignal
  ): Promise<void> {
    const response = await fetch(
      `${apiClient.getBaseURL()}/api/conversations/${conversationId}/messages/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
        signal,
      }
    );

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
                  case 'intent': {
                    const data = JSON.parse(currentData) as SSEIntentEvent;
                    callbacks.onIntent?.(data);
                    break;
                  }
                  case 'context': {
                    const data = JSON.parse(currentData) as SSEContextEvent;
                    callbacks.onContext?.(data);
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
                    callbacks.onError?.(data.message ?? 'Unknown error');
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

  async getMessages(
    conversationId: string,
    params?: {
      limit?: number;
      offset?: number;
      include_citations?: boolean;
    }
  ): Promise<MessageListResponse> {
    return await apiClient.get<MessageListResponse>(
      `/api/conversations/${conversationId}/messages`,
      { params }
    );
  },

  async update(conversationId: string, data: UpdateConversationRequest): Promise<Conversation> {
    const result = await apiClient.patch<ConversationResponse>(
      `/api/conversations/${conversationId}`,
      data
    );
    return result.conversation;
  },

  async archive(conversationId: string): Promise<Conversation> {
    const result = await apiClient.delete<ConversationResponse>(
      `/api/conversations/${conversationId}`
    );
    return result.conversation;
  },
};
