import React, { useState, useEffect } from 'react';
import { MessageCircle, Send, Loader2, FileText, Lightbulb, AlertCircle, Trash2, BarChart3 } from 'lucide-react';
import axios from 'axios';
import { useConversation } from '../hooks/useConversation';

interface Citation {
  doc_id: string;
  title: string;
  snippet: string;
  score?: number;
}

interface QAResponse {
  answer: string;
  confidence: number;
  citations: Citation[];
  method?: string;
  context_length?: number;
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

const QAPage: React.FC = () => {
  const { messages, addMessage, clearConversation, getConversationStats } = useConversation();
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [contextLimit, setContextLimit] = useState(5);
  const [showClearConfirm, setShowClearConfirm] = useState(false);

  const conversationStats = getConversationStats();


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!currentQuestion.trim() || isLoading) {
      return;
    }

    const questionId = Date.now().toString();
    const questionMessage: Message = {
      id: questionId,
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
      const response = await axios.post<QAResponse>('http://localhost:8000/api/ask', {
        question,
        context_limit: contextLimit
      });

      const answerMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'answer',
        content: response.data.answer,
        timestamp: new Date(),
        confidence: response.data.confidence,
        citations: response.data.citations,
        method: response.data.method
      };

      addMessage(answerMessage);
    } catch (error) {
      console.error('Q&A failed:', error);
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'answer',
        content: 'I encountered an error while processing your question. Please try again or rephrase your question.',
        timestamp: new Date(),
        confidence: 0
      };

      addMessage(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const formatConfidence = (confidence: number): string => {
    return `${Math.round(confidence * 100)}%`;
  };

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'text-green-600 dark:text-green-400';
    if (confidence >= 0.5) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  const getMethodDescription = (method?: string): string => {
    switch (method) {
      case 'rag_llm': return 'AI-generated using document context';
      case 'no_context': return 'No relevant documents found';
      case 'insufficient_context': return 'Insufficient context available';
      case 'fallback_simple': return 'Simple fallback response';
      case 'error': return 'Error occurred during processing';
      default: return 'Response generated';
    }
  };

  const handleClearConversation = () => {
    setShowClearConfirm(false);
    clearConversation();
  };

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

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [showClearConfirm]);

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="p-6 border-b border-border/30">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center">
              <MessageCircle className="h-6 w-6 mr-2" />
              Ask Questions
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Ask questions about your documents and get AI-powered answers
            </p>
          </div>
          
          {/* Settings and Actions */}
          <div className="flex items-center space-x-4">
            {/* Conversation Stats */}
            {conversationStats.hasMessages && (
              <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                <div className="flex items-center space-x-1">
                  <BarChart3 className="h-4 w-4" />
                  <span>{conversationStats.questionCount} questions</span>
                </div>
                {conversationStats.avgConfidence > 0 && (
                  <div className="flex items-center space-x-1">
                    <span>Avg confidence: </span>
                    <span className={getConfidenceColor(conversationStats.avgConfidence)}>
                      {formatConfidence(conversationStats.avgConfidence)}
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* Context Limit Setting */}
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium">Context documents:</label>
              <select
                value={contextLimit}
                onChange={(e) => setContextLimit(Number(e.target.value))}
                className="px-3 py-1 border border-input rounded-md bg-background text-foreground"
              >
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={10}>10</option>
              </select>
            </div>

            {/* Clear Conversation Button */}
            {conversationStats.hasMessages && (
              <div className="relative">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowClearConfirm(true);
                  }}
                  className="px-3 py-1 text-sm border border-border rounded-md hover:bg-muted/50 transition-colors flex items-center space-x-2 text-muted-foreground hover:text-foreground"
                  title="Clear conversation history"
                >
                  <Trash2 className="h-4 w-4" />
                  <span>Clear</span>
                </button>

                {/* Confirmation Modal */}
                {showClearConfirm && (
                  <div 
                    className="absolute top-full right-0 mt-2 p-4 bg-card border border-border rounded-lg shadow-lg z-10 min-w-[280px] confirmation-modal"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="space-y-3">
                      <div>
                        <h3 className="font-medium text-sm">Clear Conversation</h3>
                        <p className="text-xs text-muted-foreground mt-1">
                          This will permanently delete all {conversationStats.totalMessages} messages from this conversation.
                        </p>
                      </div>
                      <div className="flex space-x-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleClearConversation();
                          }}
                          className="px-3 py-1 text-xs bg-destructive text-destructive-foreground rounded hover:bg-destructive/90 transition-colors"
                        >
                          Clear All
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setShowClearConfirm(false);
                          }}
                          className="px-3 py-1 text-xs border border-border rounded hover:bg-muted/50 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <MessageCircle className="h-16 w-16 text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold text-muted-foreground mb-2">
              Start a conversation
            </h2>
            <p className="text-muted-foreground max-w-md">
              Ask questions about your documents and get intelligent answers powered by AI. 
              Try questions like "What are the key findings?" or "Summarize the main points."
            </p>
            <div className="mt-6 p-4 bg-muted/30 rounded-lg max-w-md">
              <div className="flex items-center text-sm text-muted-foreground mb-2">
                <Lightbulb className="h-4 w-4 mr-2" />
                Example questions:
              </div>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• "What are the main topics discussed?"</li>
                <li>• "Summarize the key findings"</li>
                <li>• "What are the financial highlights?"</li>
                <li>• "Who are the main stakeholders mentioned?"</li>
              </ul>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className={`flex ${message.type === 'question' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-3xl ${message.type === 'question' ? 'ml-auto' : 'mr-auto'}`}>
                <div
                  className={`p-4 rounded-lg ${
                    message.type === 'question'
                      ? 'bg-primary text-primary-foreground'
                      : 'glass-card border border-border/30'
                  }`}
                >
                  <div className="whitespace-pre-wrap">{message.content}</div>
                  
                  {message.type === 'answer' && (
                    <div className="mt-3 space-y-3">
                      {/* Confidence and Method */}
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center space-x-4">
                          {message.confidence !== undefined && (
                            <div className="flex items-center space-x-1">
                              <span className="text-muted-foreground">Confidence:</span>
                              <span className={getConfidenceColor(message.confidence)}>
                                {formatConfidence(message.confidence)}
                              </span>
                            </div>
                          )}
                          {message.method && (
                            <div className="flex items-center space-x-1">
                              <span className="text-muted-foreground">Method:</span>
                              <span className="text-muted-foreground">
                                {getMethodDescription(message.method)}
                              </span>
                            </div>
                          )}
                        </div>
                        <span className="text-muted-foreground">
                          {message.timestamp.toLocaleTimeString()}
                        </span>
                      </div>

                      {/* Citations */}
                      {message.citations && message.citations.length > 0 && (
                        <div className="border-t border-border/30 pt-3">
                          <div className="flex items-center text-sm font-medium text-muted-foreground mb-2">
                            <FileText className="h-4 w-4 mr-1" />
                            Sources ({message.citations.length})
                          </div>
                          <div className="space-y-2">
                            {message.citations.map((citation, index) => (
                              <div key={index} className="p-3 bg-muted/30 rounded border border-border/20">
                                <div className="flex items-start justify-between">
                                  <div className="flex-1">
                                    <div className="font-medium text-sm">{citation.title}</div>
                                    <div className="text-xs text-muted-foreground mt-1">
                                      {citation.snippet}
                                    </div>
                                  </div>
                                  {citation.score && (
                                    <div className="text-xs text-muted-foreground ml-2">
                                      {Math.round(citation.score * 100)}%
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
        
        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="max-w-3xl mr-auto">
              <div className="glass-card border border-border/30 p-4 rounded-lg">
                <div className="flex items-center space-x-2 text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Thinking...</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-6 border-t border-border/30">
        <form onSubmit={handleSubmit} className="flex space-x-4">
          <div className="flex-1">
            <input
              type="text"
              value={currentQuestion}
              onChange={(e) => setCurrentQuestion(e.target.value)}
              placeholder="Ask a question about your documents..."
              disabled={isLoading}
              className="w-full px-4 py-2 border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>
          <button
            type="submit"
            disabled={!currentQuestion.trim() || isLoading}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            <span>Ask</span>
          </button>
        </form>
        
        {/* Help text */}
        <div className="mt-2 text-xs text-muted-foreground">
          <div className="flex items-center space-x-1">
            <AlertCircle className="h-3 w-3" />
            <span>
              Answers are generated from your uploaded documents. Make sure relevant documents are uploaded for best results.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default QAPage;