/**
 * TypeScript interfaces for QAPage
 */

export interface Citation {
  doc_id: string;
  title: string;
  snippet: string;
  score?: number;
}

export interface QAResponse {
  answer: string;
  confidence: number;
  citations: Citation[];
  method?: string;
  context_length?: number;
}

export interface Message {
  id: string;
  type: 'question' | 'answer';
  content: string;
  timestamp: Date;
  confidence?: number;
  citations?: Citation[];
  method?: string;
}

export interface ConversationStats {
  hasMessages: boolean;
  totalMessages: number;
  questionCount: number;
  answerCount: number;
  avgConfidence: number;
}

export interface QARequest {
  question: string;
  context_limit: number;
}