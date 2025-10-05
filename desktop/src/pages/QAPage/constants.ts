/**
 * Constants for QAPage
 */

export const API_BASE_URL = 'http://localhost:8000';

export const API_ENDPOINTS = {
  ASK: '/api/ask',
} as const;

export const CONTEXT_LIMIT_OPTIONS = [
  { value: 3, label: '3' },
  { value: 5, label: '5' },
  { value: 10, label: '10' },
] as const;

export const DEFAULT_CONTEXT_LIMIT = 5;

export const CONFIDENCE_THRESHOLDS = {
  HIGH: 0.8,
  MEDIUM: 0.5,
} as const;

export const METHOD_DESCRIPTIONS: Record<string, string> = {
  'rag_llm': 'AI-generated using document context',
  'no_context': 'No relevant documents found',
  'insufficient_context': 'Insufficient context available',
  'fallback_simple': 'Simple fallback response',
  'error': 'Error occurred during processing',
  'default': 'Response generated',
} as const;

export const EXAMPLE_QUESTIONS = [
  'What are the main topics discussed?',
  'Summarize the key findings',
  'What are the financial highlights?',
  'Who are the main stakeholders mentioned?',
] as const;

export const UI_TEXT = {
  PAGE_TITLE: 'Ask Questions',
  PAGE_SUBTITLE: 'Ask questions about your documents and get AI-powered answers',
  
  CONTEXT_LABEL: 'Context documents:',
  CLEAR_BUTTON: 'Clear',
  ASK_BUTTON: 'Ask',
  
  CONVERSATION_STATS: {
    QUESTIONS: (count: number) => `${count} questions`,
    AVG_CONFIDENCE: 'Avg confidence:',
  },
  
  CLEAR_CONFIRMATION: {
    TITLE: 'Clear Conversation',
    DESCRIPTION: (count: number) => `This will permanently delete all ${count} messages from this conversation.`,
    CONFIRM: 'Clear All',
    CANCEL: 'Cancel',
  },
  
  EMPTY_STATE: {
    TITLE: 'Start a conversation',
    DESCRIPTION: 'Ask questions about your documents and get intelligent answers powered by AI. Try questions like "What are the key findings?" or "Summarize the main points."',
    EXAMPLES_TITLE: 'Example questions:',
  },
  
  MESSAGE: {
    THINKING: 'Thinking...',
    CONFIDENCE: 'Confidence:',
    METHOD: 'Method:',
    SOURCES: (count: number) => `Sources (${count})`,
  },
  
  INPUT: {
    PLACEHOLDER: 'Ask a question about your documents...',
    HELP_TEXT: 'Answers are generated from your uploaded documents. Make sure relevant documents are uploaded for best results.',
  },
  
  ERROR_MESSAGE: 'I encountered an error while processing your question. Please try again or rephrase your question.',
} as const;