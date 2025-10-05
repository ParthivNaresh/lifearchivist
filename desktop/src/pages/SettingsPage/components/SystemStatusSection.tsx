/**
 * SystemStatusSection component
 */

import React from 'react';
import { 
  Activity, 
  CheckCircle, 
  AlertCircle, 
  Clock, 
  HardDrive, 
  Database 
} from 'lucide-react';
import { SystemHealth, VaultStats } from '../types';
import { UI_TEXT } from '../constants';

interface SystemStatusSectionProps {
  systemHealth: SystemHealth | null;
  vaultStats: VaultStats | null;
  loading: boolean;
}

export const SystemStatusSection: React.FC<SystemStatusSectionProps> = ({
  systemHealth,
  vaultStats,
  loading,
}) => {
  const getStatusIcon = (status: boolean) => {
    return status ? (
      <CheckCircle className="h-4 w-4 text-green-500" />
    ) : (
      <AlertCircle className="h-4 w-4 text-red-500" />
    );
  };

  return (
    <div className="bg-card rounded-lg border p-6">
      <div className="flex items-center space-x-3 mb-4">
        <Activity className="h-6 w-6 text-primary" />
        <h2 className="text-lg font-semibold">{UI_TEXT.SECTIONS.SYSTEM_STATUS}</h2>
      </div>
      
      {loading ? (
        <div className="flex items-center space-x-2">
          <Clock className="h-4 w-4 animate-spin" />
          <span className="text-sm text-muted-foreground">{UI_TEXT.STATUS.LOADING}</span>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center justify-between p-3 bg-muted/30 rounded-md">
              <div className="flex items-center space-x-2">
                <HardDrive className="h-4 w-4" />
                <span className="text-sm font-medium">Vault</span>
              </div>
              {getStatusIcon(systemHealth?.vault || false)}
            </div>
            
            <div className="flex items-center justify-between p-3 bg-muted/30 rounded-md">
              <div className="flex items-center space-x-2">
                <Database className="h-4 w-4" />
                <span className="text-sm font-medium">LlamaIndex</span>
              </div>
              {getStatusIcon(systemHealth?.llamaindex || false)}
            </div>
          </div>

          {vaultStats && (
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">{UI_TEXT.STATUS.DOCUMENTS}</span>
                <span className="ml-2 font-medium">{vaultStats.total_files.toLocaleString()}</span>
              </div>
              <div>
                <span className="text-muted-foreground">{UI_TEXT.STATUS.STORAGE_USED}</span>
                <span className="ml-2 font-medium">{vaultStats.total_size_mb.toFixed(1)} MB</span>
              </div>
              <div>
                <span className="text-muted-foreground">{UI_TEXT.STATUS.STATUS}</span>
                <span className="ml-2 font-medium text-green-600">{UI_TEXT.STATUS.HEALTHY}</span>
              </div>
            </div>
          )}

          <div className="pt-2 border-t">
            <p className="text-xs text-muted-foreground">
              {UI_TEXT.STATUS.VAULT_LOCATION} {vaultStats?.vault_path || '~/.lifearchivist/vault'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};