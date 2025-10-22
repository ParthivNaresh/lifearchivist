/**
 * InputArea component - question input form
 */

import { Send, Loader2, AlertCircle } from 'lucide-react';
import { UI_TEXT } from '../constants';

interface InputAreaProps {
  currentQuestion: string;
  isLoading: boolean;
  onQuestionChange: (question: string) => void;
  onSubmit: (e: React.FormEvent) => void;
}

export const InputArea: React.FC<InputAreaProps> = ({
  currentQuestion,
  isLoading,
  onQuestionChange,
  onSubmit,
}) => {
  return (
    <div className="p-6 border-t border-border/30">
      <form onSubmit={onSubmit} className="flex space-x-4">
        <div className="flex-1">
          <input
            type="text"
            value={currentQuestion}
            onChange={(e) => onQuestionChange(e.target.value)}
            placeholder={UI_TEXT.INPUT.PLACEHOLDER}
            disabled={isLoading}
            className="w-full px-4 py-2 border border-input rounded-md bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          />
        </div>
        <button
          type="submit"
          disabled={!currentQuestion.trim() || isLoading}
          className="px-6 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
        >
          {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          <span>{UI_TEXT.ASK_BUTTON}</span>
        </button>
      </form>

      {/* Help text */}
      <div className="mt-2 text-xs text-muted-foreground">
        <div className="flex items-center space-x-1">
          <AlertCircle className="h-3 w-3" />
          <span>{UI_TEXT.INPUT.HELP_TEXT}</span>
        </div>
      </div>
    </div>
  );
};
