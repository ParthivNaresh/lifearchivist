/**
 * QAHeader component - displays page title and controls
 */

import { MessageCircle, Trash2, BarChart3 } from 'lucide-react';
import { type ConversationStats } from '../types';
import { CONTEXT_LIMIT_OPTIONS, UI_TEXT } from '../constants';
import { formatConfidence, getConfidenceColor } from '../utils';

interface QAHeaderProps {
  conversationStats: ConversationStats;
  contextLimit: number;
  showClearConfirm: boolean;
  onContextLimitChange: (limit: number) => void;
  onShowClearConfirm: (show: boolean) => void;
  onClearConversation: () => void;
}

export const QAHeader: React.FC<QAHeaderProps> = ({
  conversationStats,
  contextLimit,
  showClearConfirm,
  onContextLimitChange,
  onShowClearConfirm,
  onClearConversation,
}) => {
  return (
    <div className="p-6 border-b border-border/30">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center">
            <MessageCircle className="h-6 w-6 mr-2" />
            {UI_TEXT.PAGE_TITLE}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">{UI_TEXT.PAGE_SUBTITLE}</p>
        </div>

        {/* Settings and Actions */}
        <div className="flex items-center space-x-4">
          {/* Conversation Stats */}
          {conversationStats.hasMessages && (
            <div className="flex items-center space-x-4 text-sm text-muted-foreground">
              <div className="flex items-center space-x-1">
                <BarChart3 className="h-4 w-4" />
                <span>{UI_TEXT.CONVERSATION_STATS.QUESTIONS(conversationStats.questionCount)}</span>
              </div>
              {conversationStats.avgConfidence > 0 && (
                <div className="flex items-center space-x-1">
                  <span>{UI_TEXT.CONVERSATION_STATS.AVG_CONFIDENCE}</span>
                  <span className={getConfidenceColor(conversationStats.avgConfidence)}>
                    {formatConfidence(conversationStats.avgConfidence)}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Context Limit Setting */}
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium">{UI_TEXT.CONTEXT_LABEL}</label>
            <select
              value={contextLimit}
              onChange={(e) => onContextLimitChange(Number(e.target.value))}
              className="px-3 py-1 border border-input rounded-md bg-background text-foreground"
            >
              {CONTEXT_LIMIT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Clear Conversation Button */}
          {conversationStats.hasMessages && (
            <div className="relative">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onShowClearConfirm(true);
                }}
                className="px-3 py-1 text-sm border border-border rounded-md hover:bg-muted/50 transition-colors flex items-center space-x-2 text-muted-foreground hover:text-foreground"
                title="Clear conversation history"
              >
                <Trash2 className="h-4 w-4" />
                <span>{UI_TEXT.CLEAR_BUTTON}</span>
              </button>

              {/* Confirmation Modal */}
              {showClearConfirm && (
                <div
                  className="absolute top-full right-0 mt-2 p-4 bg-card border border-border rounded-lg shadow-lg z-10 min-w-[280px] confirmation-modal"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="space-y-3">
                    <div>
                      <h3 className="font-medium text-sm">{UI_TEXT.CLEAR_CONFIRMATION.TITLE}</h3>
                      <p className="text-xs text-muted-foreground mt-1">
                        {UI_TEXT.CLEAR_CONFIRMATION.DESCRIPTION(conversationStats.totalMessages)}
                      </p>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onClearConversation();
                        }}
                        className="px-3 py-1 text-xs bg-destructive text-destructive-foreground rounded hover:bg-destructive/90 transition-colors"
                      >
                        {UI_TEXT.CLEAR_CONFIRMATION.CONFIRM}
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onShowClearConfirm(false);
                        }}
                        className="px-3 py-1 text-xs border border-border rounded hover:bg-muted/50 transition-colors"
                      >
                        {UI_TEXT.CLEAR_CONFIRMATION.CANCEL}
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
  );
};
