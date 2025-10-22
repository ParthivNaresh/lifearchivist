import { useState, useEffect, useCallback } from 'react';

interface Citation {
  doc_id: string;
  title: string;
  snippet: string;
  score?: number;
}

interface Message {
  id: string;
  type: 'question' | 'answer';
  content: string;
  timestamp: Date;
  confidence?: number;
  citations?: Citation[];
  method?: string;
}

// Type for stored messages (with timestamp as string for JSON serialization)
interface StoredMessage {
  id: string;
  type: 'question' | 'answer';
  content: string;
  timestamp: string;
  confidence?: number;
  citations?: Citation[];
  method?: string;
}

const STORAGE_KEY = 'lifearchivist-conversation-history';
const MAX_STORED_MESSAGES = 100; // Limit to prevent localStorage bloat

export const useConversation = () => {
  const [messages, setMessages] = useState<Message[]>([]);

  // Load conversation from localStorage on mount
  useEffect(() => {
    const loadMessages = () => {
      try {
        const storedConversation = localStorage.getItem(STORAGE_KEY);
        if (storedConversation) {
          const parsedMessages = JSON.parse(storedConversation) as StoredMessage[];
          // Convert timestamp strings back to Date objects
          const messagesWithDates: Message[] = parsedMessages.map((msg) => ({
            ...msg,
            timestamp: new Date(msg.timestamp),
          }));
          return messagesWithDates;
        }
        return null;
      } catch (error) {
        console.error('Failed to load conversation from localStorage:', error);
        // Clear corrupted data
        localStorage.removeItem(STORAGE_KEY);
        return null;
      }
    };

    const loadedMessages = loadMessages();
    if (loadedMessages) {
      // Defer state update to avoid synchronous setState in effect
      setTimeout(() => {
        setMessages(loadedMessages);
      }, 0);
    }
  }, []);

  // Save conversation to localStorage whenever messages change
  useEffect(() => {
    // Skip saving if messages array is empty on initial load
    if (messages.length === 0) {
      return;
    }

    try {
      // Only store the most recent messages to prevent localStorage bloat
      const messagesToStore = messages.slice(-MAX_STORED_MESSAGES);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messagesToStore));
    } catch (error) {
      console.error('Failed to save conversation to localStorage:', error);
      // If storage is full, try to clear old data and save again
      try {
        localStorage.removeItem(STORAGE_KEY);
        const messagesToStore = messages.slice(-MAX_STORED_MESSAGES / 2); // Keep fewer messages
        localStorage.setItem(STORAGE_KEY, JSON.stringify(messagesToStore));
      } catch (retryError) {
        console.error('Failed to save conversation after clearing:', retryError);
      }
    }
  }, [messages]);

  const addMessage = useCallback((message: Message) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const clearConversation = useCallback(() => {
    setMessages([]);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (error) {
      console.error('Failed to clear conversation from localStorage:', error);
    }
  }, []);

  const getConversationStats = useCallback(() => {
    const questionCount = messages.filter((msg) => msg.type === 'question').length;
    const answerCount = messages.filter((msg) => msg.type === 'answer').length;

    // Calculate average confidence without non-null assertion
    const answersWithConfidence = messages.filter(
      (msg) => msg.type === 'answer' && msg.confidence !== undefined
    );

    const avgConfidence =
      answersWithConfidence.length > 0
        ? answersWithConfidence.reduce((sum, msg) => {
            // We've already filtered for messages with confidence, so this is safe
            const confidence = msg.confidence ?? 0;
            return sum + confidence;
          }, 0) / answersWithConfidence.length
        : 0;

    return {
      totalMessages: messages.length,
      questionCount,
      answerCount,
      avgConfidence,
      hasMessages: messages.length > 0,
    };
  }, [messages]);

  return {
    messages,
    addMessage,
    clearConversation,
    getConversationStats,
  };
};
