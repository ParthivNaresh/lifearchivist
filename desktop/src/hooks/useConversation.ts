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

const STORAGE_KEY = 'lifearchivist-conversation-history';
const MAX_STORED_MESSAGES = 100; // Limit to prevent localStorage bloat

export const useConversation = () => {
  const [messages, setMessages] = useState<Message[]>([]);

  // Load conversation from localStorage on mount
  useEffect(() => {
    try {
      const storedConversation = localStorage.getItem(STORAGE_KEY);
      if (storedConversation) {
        const parsedMessages = JSON.parse(storedConversation);
        // Convert timestamp strings back to Date objects
        const messagesWithDates = parsedMessages.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        }));
        setMessages(messagesWithDates);
      }
    } catch (error) {
      console.error('Failed to load conversation from localStorage:', error);
      // Clear corrupted data
      localStorage.removeItem(STORAGE_KEY);
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
    setMessages(prev => [...prev, message]);
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
    const questionCount = messages.filter(msg => msg.type === 'question').length;
    const answerCount = messages.filter(msg => msg.type === 'answer').length;
    const avgConfidence = messages
      .filter(msg => msg.type === 'answer' && msg.confidence !== undefined)
      .reduce((sum, msg, _, arr) => sum + (msg.confidence! / arr.length), 0);

    return {
      totalMessages: messages.length,
      questionCount,
      answerCount,
      avgConfidence: isNaN(avgConfidence) ? 0 : avgConfidence,
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