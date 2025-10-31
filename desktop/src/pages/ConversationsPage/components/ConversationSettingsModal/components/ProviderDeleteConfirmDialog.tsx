import { AlertTriangle, X } from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';

interface ProviderDeleteConfirmDialogProps {
  isOpen: boolean;
  providerId: string;
  conversationCount: number;
  sampleConversations: {
    id: string;
    title: string;
    model: string;
  }[];
  defaultProvider?: {
    id: string;
    name: string;
    model: string;
  };
  isDeleting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ProviderDeleteConfirmDialog: React.FC<ProviderDeleteConfirmDialogProps> = ({
  isOpen,
  providerId,
  conversationCount,
  sampleConversations,
  defaultProvider,
  isDeleting,
  onConfirm,
  onCancel,
}) => {
  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onCancel()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-background border border-border rounded-lg p-6 w-full max-w-md z-50 shadow-xl">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center">
              <AlertTriangle className="h-5 w-5 text-destructive" />
            </div>
            <div className="flex-1">
              <Dialog.Title className="text-lg font-semibold mb-2">Delete Provider</Dialog.Title>

              {conversationCount > 0 ? (
                <>
                  <Dialog.Description className="text-sm text-muted-foreground mb-4">
                    This provider is currently being used by{' '}
                    <span className="font-semibold text-foreground">
                      {conversationCount} conversation{conversationCount !== 1 ? 's' : ''}
                    </span>
                    .
                  </Dialog.Description>

                  {sampleConversations.length > 0 && (
                    <div className="mb-4 p-3 bg-muted/50 rounded-lg border border-border/50">
                      <p className="text-xs font-medium text-muted-foreground mb-2">
                        Affected conversations:
                      </p>
                      <ul className="space-y-1">
                        {sampleConversations.map((conv) => (
                          <li key={conv.id} className="text-xs text-muted-foreground">
                            • {conv.title || 'Untitled'} ({conv.model})
                          </li>
                        ))}
                        {conversationCount > sampleConversations.length && (
                          <li className="text-xs text-muted-foreground italic">
                            • and {conversationCount - sampleConversations.length} more...
                          </li>
                        )}
                      </ul>
                    </div>
                  )}

                  <p className="text-sm text-muted-foreground mb-4">
                    If you delete this provider, these conversations will automatically switch to
                    the default provider{' '}
                    {defaultProvider ? (
                      <>
                        (<span className="font-medium">{defaultProvider.name}</span>) with the model{' '}
                        <span className="font-mono text-xs">{defaultProvider.model}</span>
                      </>
                    ) : (
                      <>
                        (Ollama) with the model{' '}
                        <span className="font-mono text-xs">llama3.2:1b</span>
                      </>
                    )}
                    .
                  </p>

                  <p className="text-sm font-medium">
                    Are you sure you want to delete this provider?
                  </p>
                </>
              ) : (
                <>
                  <Dialog.Description className="text-sm text-muted-foreground mb-4">
                    Are you sure you want to delete the provider{' '}
                    <span className="font-mono text-xs">{providerId}</span>? This action cannot be
                    undone.
                  </Dialog.Description>
                </>
              )}
            </div>

            <Dialog.Close asChild>
              <button
                className="text-muted-foreground hover:text-foreground transition-colors"
                aria-label="Close"
                disabled={isDeleting}
              >
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          <div className="flex gap-3 mt-6 justify-end">
            <button
              onClick={onCancel}
              disabled={isDeleting}
              className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              disabled={isDeleting}
              className="px-4 py-2 text-sm bg-destructive text-destructive-foreground rounded-lg hover:bg-destructive/90 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isDeleting ? (
                <>
                  <div className="h-3 w-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  Deleting...
                </>
              ) : (
                <>Delete Provider</>
              )}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
