import { useState, useEffect } from 'react';
import { Loader2, ChevronDown, Sparkles } from 'lucide-react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { providersApi } from '../../../providers-api';
import { settingsApi } from '../api';
import type { ProviderModel } from '../../../providers-types';

interface DefaultProviderModelSelectorProps {
  providerId: string;
  providerName: string;
  onModelChange?: (model: string) => void;
}

export const DefaultProviderModelSelector: React.FC<DefaultProviderModelSelectorProps> = ({
  providerId,
  providerName,
  onModelChange,
}) => {
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [hasInitialized, setHasInitialized] = useState(false);

  const { data: modelsData, isLoading: modelsLoading } = useQuery({
    queryKey: ['provider-models', providerId],
    queryFn: () => providersApi.listModels(providerId),
    staleTime: 5 * 60 * 1000,
  });

  const { data: currentSettings } = useQuery({
    queryKey: ['settings'],
    queryFn: () => settingsApi.getSettings(),
    staleTime: 30 * 1000,
  });

  const updateDefaultModelMutation = useMutation({
    mutationFn: async (model: string) => {
      setIsUpdating(true);
      await providersApi.setDefault({ 
        provider_id: providerId, 
        default_model: model 
      });
    },
    onSuccess: (_, model) => {
      setIsUpdating(false);
      if (onModelChange) {
        onModelChange(model);
      }
    },
    onError: () => {
      setIsUpdating(false);
    },
  });

  useEffect(() => {
    if (!modelsData?.models || hasInitialized) return;
    
    let modelToSet: string | null = null;
    
    if (currentSettings?.data?.llm_model) {
      const modelExists = modelsData.models.some(m => m.id === currentSettings.data.llm_model);
      if (modelExists) {
        modelToSet = currentSettings.data.llm_model;
      }
    }
    
    if (!modelToSet) {
      const firstModel = modelsData.models[0];
      if (firstModel) {
        modelToSet = firstModel.id;
      }
    }
    
    if (modelToSet) {
      setSelectedModel(modelToSet);
      setHasInitialized(true);
      
      providersApi.setDefault({ 
        provider_id: providerId, 
        default_model: modelToSet 
      }).then(() => {
        if (onModelChange) {
          onModelChange(modelToSet);
        }
      }).catch(console.error);
    }
  }, [modelsData, currentSettings, hasInitialized, providerId, onModelChange]);

  const handleModelChange = (modelId: string) => {
    setSelectedModel(modelId);
    void updateDefaultModelMutation.mutate(modelId);
  };

  const models = modelsData?.models ?? [];
  const groupedModels = models.reduce((acc, model) => {
    const category = model.metadata?.category as string || 'Standard';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(model);
    return acc;
  }, {} as Record<string, ProviderModel[]>);

  const formatModelName = (model: ProviderModel) => {
    const contextK = model.context_window ? Math.floor(model.context_window / 1000) : null;
    const costInfo = model.cost_per_1k_input 
      ? ` ($${model.cost_per_1k_input}/1k)`
      : '';
    
    return `${model.name || model.id}${contextK ? ` (${contextK}k)` : ''}${costInfo}`;
  };

  if (modelsLoading) {
    return (
      <div className="px-4 py-3 bg-accent/5 border-t border-border/30">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          <span>Loading models...</span>
        </div>
      </div>
    );
  }

  if (models.length === 0) {
    return (
      <div className="px-4 py-3 bg-accent/5 border-t border-border/30">
        <p className="text-sm text-muted-foreground">No models available</p>
      </div>
    );
  }

  return (
    <div className="px-4 py-3 bg-accent/5 border-t border-border/30">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-1">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          <label className="text-xs font-medium text-muted-foreground">
            Default Model
          </label>
        </div>
        
        <div className="relative flex-1 max-w-sm">
          <select
            value={selectedModel || ''}
            onChange={(e) => handleModelChange(e.target.value)}
            disabled={isUpdating || models.length === 0}
            className="w-full px-3 py-1.5 pr-8 text-sm bg-background/80 border border-border/50 rounded-md 
                     hover:border-border focus:outline-none focus:ring-2 focus:ring-primary/20 
                     disabled:opacity-50 disabled:cursor-not-allowed appearance-none cursor-pointer
                     transition-colors"
          >
            {Object.keys(groupedModels).length > 1 ? (
              Object.entries(groupedModels).map(([category, categoryModels]) => (
                <optgroup key={category} label={category}>
                  {categoryModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {formatModelName(model)}
                    </option>
                  ))}
                </optgroup>
              ))
            ) : (
              models.map((model) => (
                <option key={model.id} value={model.id}>
                  {formatModelName(model)}
                </option>
              ))
            )}
          </select>
          
          <div className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
            {isUpdating ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            )}
          </div>
        </div>
      </div>
      
      {selectedModel && (
        <p className="mt-2 text-xs text-muted-foreground">
          New conversations will use {providerName} with this model
        </p>
      )}
    </div>
  );
};