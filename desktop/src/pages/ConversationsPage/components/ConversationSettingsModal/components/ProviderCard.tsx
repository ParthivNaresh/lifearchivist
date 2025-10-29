import {
  Star,
  Shield,
  Check,
  AlertCircle,
  Loader2,
  Trash,
  ChevronDown,
  ChevronRight,
  BarChart3,
  DollarSign,
  Info,
} from 'lucide-react';
import * as Tooltip from '@radix-ui/react-tooltip';
import type { Provider } from '../../../providers-types';

interface ProviderCardProps {
  provider: Provider;
  isExpanded: boolean;
  isTesting: boolean;
  testResult: { success: boolean; message: string; isExiting?: boolean } | null;
  onToggleExpand: () => void;
  onSetDefault: () => void;
  onTest: () => void;
  onDelete: () => void;
  isSettingDefault: boolean;
  isDeletable: boolean;
}

export const ProviderCard: React.FC<ProviderCardProps> = ({
  provider,
  isExpanded,
  isTesting,
  testResult,
  onToggleExpand,
  onSetDefault,
  onTest,
  onDelete,
  isSettingDefault,
  isDeletable,
}) => {
  const hasCapabilities = provider.is_admin;

  return (
    <div className="bg-background/60 backdrop-blur-sm rounded-lg border border-border/50 hover:border-border transition-colors overflow-hidden">
      <div className="flex items-center gap-3 p-4">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {hasCapabilities && (
            <button
              onClick={onToggleExpand}
              className="p-1.5 text-sm border border-border rounded-md hover:bg-accent transition-colors flex-shrink-0"
              title={isExpanded ? 'Hide capabilities' : 'Show capabilities'}
            >
              {isExpanded ? (
                <ChevronDown className="h-3.5 w-3.5" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5" />
              )}
            </button>
          )}

          {!provider.is_default && (
            <button
              onClick={onSetDefault}
              disabled={isSettingDefault}
              className="p-1.5 text-sm border border-border rounded-md hover:bg-accent transition-colors disabled:opacity-50 flex-shrink-0"
              title="Set as default provider"
            >
              <Star className="h-3.5 w-3.5" />
            </button>
          )}

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="font-medium truncate">{provider.id}</span>
              {provider.is_default && (
                <span className="flex items-center gap-1 px-2 py-0.5 text-xs bg-primary/10 text-primary rounded-full border border-primary/20 flex-shrink-0">
                  <Star className="h-3 w-3 fill-current" />
                  DEFAULT
                </span>
              )}
              {provider.is_admin && (
                <Tooltip.Root>
                  <Tooltip.Trigger asChild>
                    <span className="flex items-center gap-1 px-2 py-0.5 text-xs bg-blue-500/10 text-blue-600 dark:text-blue-400 rounded-full border border-blue-500/20 flex-shrink-0 cursor-help">
                      <Shield className="h-3 w-3" />
                      ADMIN
                    </span>
                  </Tooltip.Trigger>
                  <Tooltip.Portal>
                    <Tooltip.Content
                      className="z-50 px-3 py-2 text-xs bg-popover text-popover-foreground border border-border rounded-md shadow-lg max-w-xs"
                      sideOffset={5}
                    >
                      Admin keys provide usage analytics and cost tracking but cannot be used for
                      chat inference.
                      <Tooltip.Arrow className="fill-border" />
                    </Tooltip.Content>
                  </Tooltip.Portal>
                </Tooltip.Root>
              )}
              <span
                className={`px-2 py-0.5 text-xs rounded-full border flex-shrink-0 ${
                  provider.is_healthy
                    ? 'bg-green-500/10 text-green-600 border-green-500/20'
                    : 'bg-red-500/10 text-red-600 border-red-500/20'
                }`}
              >
                {provider.is_healthy ? 'Healthy' : 'Unhealthy'}
              </span>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-xs text-muted-foreground capitalize">{provider.type}</p>
              {provider.workspace_name && (
                <>
                  <span className="text-xs text-muted-foreground">•</span>
                  <p className="text-xs text-muted-foreground truncate">
                    {provider.workspace_name}
                  </p>
                </>
              )}
            </div>
          </div>
        </div>

        <div
          className="flex items-center gap-2 flex-shrink-0"
          style={{ minWidth: '280px', justifyContent: 'flex-end' }}
        >
          {testResult && (
            <span
              className={`flex items-center gap-1 px-2 py-1 text-xs rounded-md border transition-all duration-300 ease-in-out ${
                testResult.success
                  ? 'bg-green-500/10 text-green-600 border-green-500/20'
                  : 'bg-red-500/10 text-red-600 border-red-500/20'
              }`}
              style={{
                animation: testResult.isExiting
                  ? 'fadeOut 300ms ease-in-out'
                  : 'fadeIn 300ms ease-in-out',
              }}
            >
              {testResult.success ? (
                <Check className="h-3 w-3" />
              ) : (
                <AlertCircle className="h-3 w-3" />
              )}
              {testResult.message}
            </span>
          )}
          <Tooltip.Root>
            <Tooltip.Trigger asChild>
              <button
                onClick={onTest}
                disabled={isTesting}
                className="px-3 py-2 text-xs font-medium border border-border rounded-md hover:bg-accent transition-colors disabled:opacity-50"
              >
                {isTesting ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Test Connection'}
              </button>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content
                className="z-50 px-3 py-2 text-xs bg-popover text-popover-foreground border border-border rounded-md shadow-lg max-w-xs"
                sideOffset={5}
              >
                Validates API key and checks connectivity to the provider&apos;s servers.
                <Tooltip.Arrow className="fill-border" />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
          {isDeletable && (
            <button
              onClick={onDelete}
              className="p-2 text-sm text-destructive border border-destructive/20 rounded-md hover:bg-destructive/10 transition-colors"
              title="Delete provider"
            >
              <Trash className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {isExpanded && hasCapabilities && (
        <div className="px-4 pb-4 pt-2 border-t border-border/30 bg-card/30 backdrop-blur-sm">
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground mb-3">Admin Capabilities</p>
            <div className="grid grid-cols-2 gap-2">
              <div className="flex items-center gap-2 px-3 py-2 bg-background/50 backdrop-blur-sm rounded-md border border-border/30">
                <BarChart3 className="h-4 w-4 text-blue-500" />
                <span className="text-xs">Usage Tracking</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-2 bg-background/50 backdrop-blur-sm rounded-md border border-border/30">
                <DollarSign className="h-4 w-4 text-green-500" />
                <span className="text-xs">Cost Tracking</span>
              </div>
            </div>
            <div className="mt-3 p-3 bg-blue-500/5 border border-blue-500/10 rounded-md flex items-start gap-2">
              <Info className="h-4 w-4 text-blue-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-muted-foreground">
                <strong className="text-blue-600 dark:text-blue-400">Admin keys</strong> provide
                organization-level usage analytics and cost tracking but cannot be used for chat
                inference. Use regular API keys for conversations.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
