/**
 * Type definitions for Conversations feature
 */

export type ConversationMetadata = Record<string, string | number | boolean | null>;

export interface Conversation {
  id: string;
  user_id: string;
  title: string | null;
  model: string;
  provider_id: string | null;
  context_documents: string[];
  system_prompt: string | null;
  temperature: number;
  max_tokens: number;
  created_at: string;
  updated_at: string;
  last_message_at: string | null;
  archived_at: string | null;
  metadata: string | ConversationMetadata;
  messages?: Message[];
  message_count?: number;
}

export type MessageMetadata = Record<string, string | number | boolean | null>;

export interface ErrorMessageMetadata {
  is_error: boolean;
  error_type: string;
  provider_id: string;
  model: string;
  retryable: boolean;
  raw_error?: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  parent_message_id: string | null;
  sequence_number: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  model: string | null;
  confidence: number | null;
  method: string | null;
  tokens_used: number | null;
  latency_ms: number | null;
  created_at: string;
  edited_at: string | null;
  metadata: string | MessageMetadata;
  citations?: Citation[];
}

export interface Citation {
  id: string;
  message_id: string;
  document_id: string;
  chunk_id: string | null;
  score: number | null;
  snippet: string;
  position: number;
  created_at: string;
}

export interface CreateConversationRequest {
  title?: string;
  model?: string;
  provider_id?: string;
  context_documents?: string[];
  system_prompt?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface UpdateConversationRequest {
  title?: string;
  model?: string;
  provider_id?: string;
  context_documents?: string[];
  system_prompt?: string;
  temperature?: number;
  max_tokens?: number;
}

export interface SendMessageRequest {
  content: string;
  context_limit?: number;
}

export interface ConversationListResponse {
  success: boolean;
  conversations: Conversation[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface ConversationResponse {
  success: boolean;
  conversation: Conversation;
}

export interface MessageListResponse {
  success: boolean;
  messages: Message[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface SendMessageResponse {
  success: boolean;
  user_message: Message;
  assistant_message: Message;
  latency_ms: number;
}

// SSE Event Types
export interface SSEUserMessageEvent {
  id: string;
  content: string;
  role: 'user';
  created_at: string;
}

export interface SSEIntentEvent {
  is_document_query: boolean;
  requires_context: boolean;
  query_type?: string;
}

export interface SSEContextEvent {
  citations: {
    document_id: string;
    chunk_id: string;
    relevance_score: number;
    text_snippet: string;
    metadata: Record<string, any>;
  }[];
  total_chunks: number;
  context_length: number;
  avg_relevance_score: number;
}

export interface SSESourceEvent {
  document_id: string;
  chunk_id: string;
  relevance_score: number;
  text_snippet: string;
  metadata: Record<string, any>;
  confidence?: number;
}

export interface SSEChunkEvent {
  text: string;
}

export interface SSEMetadataEvent {
  model: string;
  provider_id: string | null;
  confidence_score: number;
  response_mode: string;
  num_sources: number;
  context_length: number;
  answer_length: number;
  unique_documents: number;
  processing_time_ms: number;
  tokens_used?: number;
  cost_usd?: number;
  [key: string]: unknown;
}

export interface SSECompleteEvent {
  status?: string;
  user_message?: Message;
  assistant_message?: Message;
  latency_ms?: number;
}

export interface SSEErrorEvent {
  error_type: string;
  message: string;
  details?: Record<string, any>;
  recoverable?: boolean;
}

export interface SSECallbacks {
  onUserMessage?: (message: SSEUserMessageEvent) => void;
  onIntent?: (data: SSEIntentEvent) => void;
  onContext?: (data: SSEContextEvent) => void;
  onSources?: (sources: SSESourceEvent[]) => void;
  onChunk?: (text: string) => void;
  onMetadata?: (metadata: SSEMetadataEvent) => void;
  onComplete?: (data: SSECompleteEvent) => void;
  onError?: (error: string) => void;
}
