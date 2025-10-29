/**
 * Inline Model Selector - Allows changing model mid-conversation
 * Groups models by provider instance for clarity
 */

import { useState, useEffect, useRef, useMemo } from 'react';
import { ChevronDown, Loader2, Check, Zap, X } from 'lucide-react';
import { useProviders, useAllProviderModels } from '../providers-hooks';
import type { ProviderModel, Provider } from '../providers-types';

interface GroupedModels {
  provider: Provider;
  models: ProviderModel[];
}

interface ModelSelectorProps {
  currentModel: string;
  onModelChange: (model: string, providerId?: string) => Promise<void>;
}

const getCostTier = (costPer1kInput: number | null): string => {
  if (!costPer1kInput) return '';
  if (costPer1kInput === 0) return '';
  if (costPer1kInput < 0.001) return '$';
  if (costPer1kInput < 0.01) return '$$';
  return '$$$';
};

const getProviderDisplayName = (provider: Provider): string => {
  const typeLabel = provider.type.charAt(0).toUpperCase() + provider.type.slice(1);
  if (provider.id === `${provider.type}-default`) {
    return typeLabel;
  }
  return `${typeLabel} (${provider.id})`;
};

interface ModelButtonProps {
  model: ProviderModel;
  provider: Provider;
  currentModel: string;
  onSelect: (model: ProviderModel, provider: Provider) => void;
}

const ModelButton: React.FC<ModelButtonProps> = ({ model, provider, currentModel, onSelect }) => {
  const isSelected = model.id === currentModel && model.provider_id === provider.id;
  const costTier = getCostTier(model.cost_per_1k_input);
  const isDisabled = !provider.is_healthy;

  return (
    <button
      onClick={() => onSelect(model, provider)}
      disabled={isDisabled}
      className={`w-full px-3 py-2 text-left text-sm transition-colors flex items-center justify-between ${
        isDisabled ? 'opacity-40 cursor-not-allowed' : 'hover:bg-accent cursor-pointer'
      }`}
      title={
        isDisabled
          ? 'Provider unavailable - check credentials'
          : `${model.name}\n${model.context_window.toLocaleString()} tokens\nCost: ${costTier || 'Free'}`
      }
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`font-medium truncate ${isDisabled ? 'text-muted-foreground' : ''}`}>
            {model.name}
          </span>
          {costTier && (
            <span className="text-[10px] text-muted-foreground flex-shrink-0">{costTier}</span>
          )}
        </div>
        {model.context_window && (
          <div className="text-xs text-muted-foreground">
            {model.context_window.toLocaleString()} tokens
          </div>
        )}
      </div>
      {isSelected && <Check className="h-4 w-4 text-primary flex-shrink-0" />}
    </button>
  );
};

interface ProviderGroupProps {
  group: GroupedModels;
  currentModel: string;
  showDivider: boolean;
  onModelSelect: (model: ProviderModel, provider: Provider) => void;
}

const ProviderGroup: React.FC<ProviderGroupProps> = ({
  group,
  currentModel,
  showDivider,
  onModelSelect,
}) => {
  return (
    <div>
      {showDivider && <div className="h-px bg-border/50 my-1" />}

      <div className="px-3 py-2 flex items-center justify-between bg-muted/30">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-foreground">
            {getProviderDisplayName(group.provider)}
          </span>
          {group.provider.workspace_name && (
            <span className="text-[10px] text-muted-foreground">
              ({group.provider.workspace_name})
            </span>
          )}
          {group.provider.is_admin && (
            <span className="text-[10px] px-1.5 py-0.5 bg-blue-500/10 text-blue-500 rounded border border-blue-500/20">
              ADMIN
            </span>
          )}
          {group.provider.is_default && (
            <span className="text-[10px] px-1.5 py-0.5 bg-primary/10 text-primary rounded border border-primary/20">
              DEFAULT
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {group.provider.is_healthy ? (
            <span title="Healthy">
              <Zap className="h-3 w-3 text-green-500" />
            </span>
          ) : (
            <span title="Unavailable">
              <X className="h-3 w-3 text-destructive" />
            </span>
          )}
        </div>
      </div>

      {group.models.map((model) => (
        <ModelButton
          key={`${model.provider_id}-${model.id}`}
          model={model}
          provider={group.provider}
          currentModel={currentModel}
          onSelect={onModelSelect}
        />
      ))}
    </div>
  );
};

export const ModelSelector: React.FC<ModelSelectorProps> = ({ currentModel, onModelChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [changing, setChanging] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { data: providersData } = useProviders();
  const { data: models = [], isLoading: loadingModels } = useAllProviderModels();

  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const groupedModels = useMemo((): GroupedModels[] => {
    const providers = providersData?.providers ?? [];
    const groups = new Map<string, GroupedModels>();

    for (const model of models) {
      const provider = providers.find((p) => p.id === model.provider_id);
      if (!provider) continue;

      const providerId = provider.id;
      if (!groups.has(providerId)) {
        groups.set(providerId, { provider, models: [] });
      }

      const group = groups.get(providerId);
      if (group) {
        group.models.push(model);
      }
    }

    return Array.from(groups.values()).sort((a, b) => {
      if (a.provider.is_default && !b.provider.is_default) return -1;
      if (!a.provider.is_default && b.provider.is_default) return 1;
      return a.provider.id.localeCompare(b.provider.id);
    });
  }, [models, providersData?.providers]);

  const handleModelSelect = async (model: ProviderModel, provider: Provider) => {
    if (!provider.is_healthy) return;

    try {
      setChanging(true);
      console.log(`Switching to model ${model.id} on provider ${provider.id}`);
      await onModelChange(model.id, provider.id);
      setIsOpen(false);
    } catch (err) {
      console.error('Failed to change model:', err);
    } finally {
      setChanging(false);
    }
  };

  const renderDropdownContent = () => {
    if (loadingModels) {
      return (
        <div className="p-3 flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Loading models...</span>
        </div>
      );
    }

    if (groupedModels.length === 0) {
      return <div className="p-3 text-sm text-muted-foreground">No models available</div>;
    }

    return (
      <div className="py-1">
        {groupedModels.map((group, groupIndex) => (
          <ProviderGroup
            key={group.provider.id}
            group={group}
            currentModel={currentModel}
            showDivider={groupIndex > 0}
            onModelSelect={(model, provider) => void handleModelSelect(model, provider)}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="relative inline-block" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={changing}
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
      >
        <span>Model: {currentModel}</span>
        {changing ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <ChevronDown className="h-3 w-3" />
        )}
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-80 bg-background/95 backdrop-blur-xl border border-border/50 rounded-lg shadow-xl z-50 max-h-96 overflow-y-auto">
          {renderDropdownContent()}
        </div>
      )}
    </div>
  );
};
