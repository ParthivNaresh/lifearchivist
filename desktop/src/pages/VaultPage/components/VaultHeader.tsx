/**
 * VaultHeader component - displays the page title and description
 */

import React from 'react';

interface VaultHeaderProps {
  title?: string;
  subtitle?: string;
}

export const VaultHeader: React.FC<VaultHeaderProps> = ({
  title = 'Document Vault',
  subtitle = 'Browse your documents organized by theme'
}) => {
  return (
    <div>
      <h1 className="text-2xl font-bold">{title}</h1>
      <p className="text-sm text-muted-foreground mt-1">
        {subtitle}
      </p>
    </div>
  );
};