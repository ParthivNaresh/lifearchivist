/**
 * EmptyState component - shown when no messages
 */

import { MessageCircle, Lightbulb } from 'lucide-react';
import { EXAMPLE_QUESTIONS, UI_TEXT } from '../constants';

export const EmptyState: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center">
      <MessageCircle className="h-16 w-16 text-muted-foreground mb-4" />
      <h2 className="text-xl font-semibold text-muted-foreground mb-2">
        {UI_TEXT.EMPTY_STATE.TITLE}
      </h2>
      <p className="text-muted-foreground max-w-md">{UI_TEXT.EMPTY_STATE.DESCRIPTION}</p>
      <div className="mt-6 p-4 bg-muted/30 rounded-lg max-w-md">
        <div className="flex items-center text-sm text-muted-foreground mb-2">
          <Lightbulb className="h-4 w-4 mr-2" />
          {UI_TEXT.EMPTY_STATE.EXAMPLES_TITLE}
        </div>
        <ul className="text-sm text-muted-foreground space-y-1">
          {EXAMPLE_QUESTIONS.map((question) => (
            <li key={question}>• &ldquo;{question}&rdquo;</li>
          ))}
        </ul>
      </div>
    </div>
  );
};
