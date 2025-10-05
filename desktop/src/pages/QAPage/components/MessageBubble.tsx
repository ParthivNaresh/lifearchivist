/**
 * MessageBubble component - individual message display
 */

import React from 'react';
import { FileText } from 'lucide-react';
import { Message } from '../types';
import { UI_TEXT } from '../constants';
import { 
  formatConfidence, 
  getConfidenceColor, 
  getMethodDescription, 
  formatTimestamp,
  formatRelevanceScore 
} from '../utils';

interface MessageBubbleProps {
  message: Message;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isQuestion = message.type === 'question';

  return (
    <div className={`flex ${isQuestion ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-3xl ${isQuestion ? 'ml-auto' : 'mr-auto'}`}>
        <div
          className={`p-4 rounded-lg ${
            isQuestion
              ? 'bg-primary text-primary-foreground'
              : 'glass-card border border-border/30'
          }`}
        >
          <div className="whitespace-pre-wrap">{message.content}</div>
          
          {!isQuestion && (
            <div className="mt-3 space-y-3">
              {/* Confidence and Method */}
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center space-x-4">
                  {message.confidence !== undefined && (
                    <div className="flex items-center space-x-1">
                      <span className="text-muted-foreground">{UI_TEXT.MESSAGE.CONFIDENCE}</span>
                      <span className={getConfidenceColor(message.confidence)}>
                        {formatConfidence(message.confidence)}
                      </span>
                    </div>
                  )}
                  {message.method && (
                    <div className="flex items-center space-x-1">
                      <span className="text-muted-foreground">{UI_TEXT.MESSAGE.METHOD}</span>
                      <span className="text-muted-foreground">
                        {getMethodDescription(message.method)}
                      </span>
                    </div>
                  )}
                </div>
                <span className="text-muted-foreground">
                  {formatTimestamp(message.timestamp)}
                </span>
              </div>

              {/* Citations */}
              {message.citations && message.citations.length > 0 && (
                <div className="border-t border-border/30 pt-3">
                  <div className="flex items-center text-sm font-medium text-muted-foreground mb-2">
                    <FileText className="h-4 w-4 mr-1" />
                    {UI_TEXT.MESSAGE.SOURCES(message.citations.length)}
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
                              {formatRelevanceScore(citation.score)}
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
  );
};