/**
 * DocumentCount component - displays document count
 */

import { UI_TEXT } from '../constants';

interface DocumentCountProps {
  count: number;
}

export const DocumentCount: React.FC<DocumentCountProps> = ({ count }) => {
  return (
    <div className="mb-4">
      <p className="text-sm text-muted-foreground">{UI_TEXT.SHOWING_COUNT(count)}</p>
    </div>
  );
};
