import {
  ChevronDown,
  ChevronUp,
  Trash2,
  Check,
  Loader2,
  AlertCircle,
  Zap,
  Globe,
  Eye,
} from 'lucide-react';
import type { Provider } from '../../../providers-types';
import { getProviderMetadata } from '../constants';

interface EnhancedProviderCardProps {
  provider: Provider;
  isExpanded: boolean;
  isTestingConnection: boolean;
  testResult: { success: boolean; message: string; isExiting?: boolean } | null;
  isSettingDefault: boolean;
  onToggleExpand: () => void;
  onSetDefault: () => void;
  onTestConnection: () => void;
  onDelete: () => void;
}

export const EnhancedProviderCard: React.FC<EnhancedProviderCardProps> = ({
  provider,
  isExpanded,
  isTestingConnection,
  testResult,
  isSettingDefault,
  onToggleExpand,
  onSetDefault,
  onTestConnection,
  onDelete,
}) => {
  const metadata = getProviderMetadata(provider.type);

  const getFeatureIcon = () => {
    if (metadata.features.fastInference) return <Zap className="h-3 w-3 text-yellow-500" />;
    if (metadata.features.localOption) return <Globe className="h-3 w-3 text-blue-500" />;
    if (metadata.features.vision) return <Eye className="h-3 w-3 text-purple-500" />;
    return null;
  };

  return (
    <div className="p-4 bg-background/50 backdrop-blur-sm rounded-lg border border-border/50 hover:border-border transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleExpand}
            className="p-1 hover:bg-accent rounded transition-colors"
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>

          <div>
            <div className="flex items-center gap-2">
              <h4 className="font-medium">{provider.name}</h4>
              {getFeatureIcon()}
              {provider.is_default && (
                <span className="px-2 py-0.5 text-xs bg-primary/10 text-primary rounded-full">
                  Default
                </span>
              )}
              {provider.is_healthy && (
                <span className="px-2 py-0.5 text-xs bg-green-500/10 text-green-500 rounded-full">
                  Healthy
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">{metadata.description}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {!provider.is_default && (
            <button
              onClick={onSetDefault}
              disabled={isSettingDefault}
              className="px-3 py-1.5 text-xs border border-border rounded-md hover:bg-accent transition-colors disabled:opacity-50"
            >
              {isSettingDefault ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Set Default'}
            </button>
          )}

          <button
            onClick={onTestConnection}
            disabled={isTestingConnection}
            className="px-3 py-1.5 text-xs border border-border rounded-md hover:bg-accent transition-colors disabled:opacity-50"
          >
            {isTestingConnection ? <Loader2 className="h-3 w-3 animate-spin" /> : 'Test'}
          </button>

          <button
            onClick={onDelete}
            className="p-1.5 text-destructive hover:bg-destructive/10 rounded transition-colors"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {testResult && (
        <div
          className={`mt-3 p-2 rounded-md flex items-start gap-2 transition-all ${
            testResult.isExiting ? 'opacity-0 scale-95' : 'opacity-100 scale-100'
          } ${
            testResult.success
              ? 'bg-green-500/10 border border-green-500/20'
              : 'bg-destructive/10 border border-destructive/20'
          }`}
        >
          {testResult.success ? (
            <Check className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
          ) : (
            <AlertCircle className="h-4 w-4 text-destructive mt-0.5 flex-shrink-0" />
          )}
          <p className={`text-xs ${testResult.success ? 'text-green-500' : 'text-destructive'}`}>
            {testResult.message}
          </p>
        </div>
      )}

      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-border/50 space-y-3">
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <span className="text-muted-foreground">Provider Type:</span>
              <span className="ml-2 font-mono">{provider.type}</span>
            </div>
            <div>
              <span className="text-muted-foreground">Provider ID:</span>
              <span className="ml-2 font-mono">{provider.id}</span>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {metadata.features.streaming && (
              <span className="px-2 py-1 text-xs bg-accent rounded">Streaming</span>
            )}
            {metadata.features.functions && (
              <span className="px-2 py-1 text-xs bg-accent rounded">Functions</span>
            )}
            {metadata.features.vision && (
              <span className="px-2 py-1 text-xs bg-accent rounded">Vision</span>
            )}
            {metadata.features.fastInference && (
              <span className="px-2 py-1 text-xs bg-yellow-500/10 text-yellow-500 rounded">
                Fast Inference
              </span>
            )}
            {metadata.features.localOption && (
              <span className="px-2 py-1 text-xs bg-blue-500/10 text-blue-500 rounded">Local</span>
            )}
          </div>

          {metadata.pricing && (
            <div className="text-xs text-muted-foreground">
              <span className="font-medium">Pricing:</span> {metadata.pricing.note}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
