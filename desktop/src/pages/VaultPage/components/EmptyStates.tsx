/**
 * EmptyStates component - displays loading, no documents, and no matches states
 */

import { Loader2, FolderOpen, Search } from 'lucide-react';

interface EmptyStatesProps {
  type: 'loading' | 'no-documents' | 'no-matches';
}

export const EmptyStates: React.FC<EmptyStatesProps> = ({ type }) => {
  const states = {
    loading: {
      icon: <Loader2 className="h-16 w-16 mb-4 animate-spin opacity-50" />,
      title: 'Loading documents...',
      subtitle: null,
    },
    'no-documents': {
      icon: <FolderOpen className="h-16 w-16 mb-4 opacity-50" />,
      title: 'No documents in vault',
      subtitle: 'Upload some documents to get started',
    },
    'no-matches': {
      icon: <Search className="h-16 w-16 mb-4 opacity-50" />,
      title: 'No matches found',
      subtitle: 'Try a different search term',
    },
  };

  const state = states[type];

  return (
    <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
      {state.icon}
      <p className="text-lg font-medium">{state.title}</p>
      {state.subtitle && <p className="text-sm mt-2">{state.subtitle}</p>}
    </div>
  );
};
