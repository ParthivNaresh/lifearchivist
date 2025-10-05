/**
 * Custom hooks for QAPage
 */

import { useState, useEffect, useCallback } from 'react';
import { useConversation } from '../../hooks/useConversation';
import { Message } from './types';
import { askQuestion } from './api';
import { generateMessageId } from './utils';
import { DEFAULT_CONTEXT_LIMIT, UI_TEXT } from './constants';

/**
 * Hook to manage Q&A state
 */
export const useQAState = () => {
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [contextLimit, setContextLimit] = useState(DEFAULT_CONTEXT_LIMIT);
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  return {
    currentQuestion,
    setCurrentQuestion,
    isLoading,
    setIsLoading,
    contextLimit,
    setContextLimit,
    showClearConfirm,
    setShowClearConfirm,
  };
};

/**
 * Hook to handle question submission
 */
export const useQuestionSubmit = (
  currentQuestion: string,
  contextLimit: number,
  setCurrentQuestion: (question: string) => void,
  setIsLoading: (loading: boolean) => void,
  addMessage: (message: Message) => void
) => {
  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!currentQuestion.trim() || setIsLoading) {
      return;
    }

    const questionMessage: Message = {
      id: generateMessageId(),
      type: 'question',
      content: currentQuestion.trim(),
      timestamp: new Date()
    };

    // Add question to messages
    addMessage(questionMessage);
    setIsLoading(true);
    
    const question = currentQuestion.trim();
    setCurrentQuestion('');

    try {
      const response = await askQuestion({
        question,
        context_limit: contextLimit
      });

      const answerMessage: Message = {
        id: generateMessageId(),
        type: 'answer',
        content: response.answer,
        timestamp: new Date(),
        confidence: response.confidence,
        citations: response.citations,
        method: response.method
      };

      addMessage(answerMessage);
    } catch (error) {
      console.error('Q&A failed:', error);
      
      const errorMessage: Message = {
        id: generateMessageId(),
        type: 'answer',
        content: UI_TEXT.ERROR_MESSAGE,
        timestamp: new Date(),
        confidence: 0
      };

      addMessage(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [currentQuestion, contextLimit, setCurrentQuestion, setIsLoading, addMessage]);

  return { handleSubmit };
};

/**
 * Hook to handle clear confirmation modal
 */
export const useClearConfirmation = (
  showClearConfirm: boolean,
  setShowClearConfirm: (show: boolean) => void,
  clearConversation: () => void
) => {
  const handleClearConversation = useCallback(() => {
    setShowClearConfirm(false);
    clearConversation();
  }, [setShowClearConfirm, clearConversation]);

  // Close confirmation modal when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showClearConfirm) {
        const target = event.target as Element;
        if (!target?.closest('.confirmation-modal')) {
          setShowClearConfirm(false);
        }
      }
    };

    if (showClearConfirm) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [showClearConfirm, setShowClearConfirm]);

  return { handleClearConversation };
};

/**
 * Hook to manage conversation
 */
export const useQAConversation = () => {
  const { messages, addMessage, clearConversation, getConversationStats } = useConversation();
  const conversationStats = getConversationStats();

  return {
    messages,
    addMessage,
    clearConversation,
    conversationStats,
  };
};