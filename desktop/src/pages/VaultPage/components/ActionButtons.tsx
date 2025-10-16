/**
 * ActionButtons component - refresh and clear vault buttons
 */

import React from 'react';
import { RefreshCw, Trash2 } from 'lucide-react';

interface ActionButtonsProps {
  refreshing: boolean;
  clearing: boolean;
  documentsCount: number;
  onRefresh: () => void;
  onClearVault: () => void;
}

export const ActionButtons: React.FC<ActionButtonsProps> = ({
  refreshing,
  clearing,
  documentsCount,
  onRefresh,
  onClearVault
}) => {
  return (
    <>
      {/* Refresh */}
      <button
        onClick={onRefresh}
        disabled={refreshing}
        className="p-2 hover:bg-muted rounded-md transition-colors disabled:opacity-50"
        title="Refresh"
      >
        <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
      </button>

      {/* Clear Vault */}
      <button
        onClick={onClearVault}
        disabled={clearing || documentsCount === 0}
        className="p-2 hover:bg-muted rounded-md transition-colors text-red-600 hover:text-red-700 disabled:opacity-50"
        title="Clear vault"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </>
  );
};