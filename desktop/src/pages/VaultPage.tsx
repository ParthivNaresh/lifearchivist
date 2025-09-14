import React, { useState, useCallback, useEffect } from 'react';
import { HardDrive, Calendar, Hash, Database, Link, AlertCircle, Loader2, Trash2, RefreshCw } from 'lucide-react';
import { useCache, clearCacheKey } from '../hooks/useCache';
import axios from 'axios';

interface VaultFile {
  path: string;
  full_path: string;
  hash: string;
  extension: string;
  size_bytes: number;
  created_at: number;
  modified_at: number;
  database_record: {
    id: string | null;
    original_path: string | null;
    status: string | null;
  } | null;
}

interface VaultInfo {
  vault_path: string;
  directories: {
    [key: string]: {
      file_count: number;
      total_size_bytes: number;
      total_size_mb: number;
    };
  };
}

interface VaultResponse {
  files: VaultFile[];
  total: number;
  directory: string;
  limit: number;
  offset: number;
}

const VaultPage: React.FC = () => {
  const [selectedDirectory, setSelectedDirectory] = useState<string>('content');
  const [clearing, setClearing] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const fetchVaultInfo = useCallback(async () => {
    const response = await axios.get<VaultInfo>('http://localhost:8000/api/vault/info');
    return response.data;
  }, []);

  const fetchVaultFiles = useCallback(async () => {
    const response = await axios.get<VaultResponse>(
      `http://localhost:8000/api/vault/files?directory=${selectedDirectory}&limit=100`
    );
    return response.data.files;
  }, [selectedDirectory]);

  const { data: vaultInfo, refresh: refreshInfo } = useCache(
    'vault-info',
    fetchVaultInfo,
    30 * 1000 // 30 second cache - more responsive
  );

  const { data: vaultFiles, loading, error, refresh } = useCache(
    `vault-files-${selectedDirectory}`,
    fetchVaultFiles,
    30 * 1000 // 30 second cache - more responsive
  );

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (timestamp: number): string => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  const manualRefresh = async () => {
    setRefreshing(true);
    try {
      // Clear caches and refresh
      clearCacheKey('vault-info');
      clearCacheKey(`vault-files-${selectedDirectory}`);
      await Promise.all([refreshInfo(), refresh()]);
    } catch (err) {
      console.error('Failed to refresh vault data:', err);
    } finally {
      setRefreshing(false);
    }
  };

  const clearVault = async () => {
    if (!confirm('Are you sure you want to clear the entire vault? This will permanently delete all files and their associated document records. This cannot be undone.')) {
      return;
    }

    try {
      setClearing(true);
      
      // Clear all data (vault files + document records)
      await axios.delete('http://localhost:8000/api/documents');
      
      // Clear all caches
      clearCacheKey('vault-info');
      clearCacheKey(`vault-files-${selectedDirectory}`);
      clearCacheKey('documents-all');
      
      // Refresh data
      await refreshInfo();
      await refresh();
      
      console.log('✅ Vault cleared successfully');
    } catch (err) {
      console.error('Failed to clear vault:', err);
    } finally {
      setClearing(false);
    }
  };

  // Auto-refresh when page becomes visible
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        // Page became visible, refresh data
        manualRefresh();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [selectedDirectory]);

  const getDirectoryIcon = (directory: string) => {
    switch (directory) {
      case 'content':
        return '📁';
      case 'thumbnails':
        return '🖼️';
      case 'temp':
        return '⏳';
      case 'exports':
        return '📤';
      default:
        return '📂';
    }
  };

  if (error) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertCircle className="h-8 w-8 text-red-500 mx-auto" />
            <p className="mt-2 text-red-600">{error}</p>
            <button 
              onClick={() => {
                refreshInfo();
                refresh();
              }}
              className="mt-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Vault Storage</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Low-level content-addressed file storage
            </p>
          </div>
          
          <div className="flex items-center space-x-3">
            {/* Manual Refresh Button */}
            <button
              onClick={manualRefresh}
              disabled={refreshing || loading}
              className="flex items-center space-x-2 px-3 py-2 border border-input rounded-md hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
              <span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
            </button>

            {/* Clear Vault Button */}
            <button
              onClick={clearVault}
              disabled={clearing || !vaultInfo || Object.values(vaultInfo.directories || {}).every(dir => dir.file_count === 0)}
              className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              <Trash2 className="h-4 w-4" />
              <span>{clearing ? 'Clearing...' : 'Clear Vault'}</span>
            </button>
          </div>
        </div>

        {/* Vault Summary */}
        {vaultInfo && vaultInfo.directories && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            {Object.entries(vaultInfo.directories).map(([dirName, stats]) => (
              <div
                key={dirName}
                className={`glass-card p-4 rounded-lg border cursor-pointer transition-colors ${
                  selectedDirectory === dirName 
                    ? 'border-primary bg-primary/5' 
                    : 'border-border/30 hover:border-border/60'
                }`}
                onClick={() => setSelectedDirectory(dirName)}
              >
                <div className="text-center">
                  <div className="text-2xl mb-2">{getDirectoryIcon(dirName)}</div>
                  <h3 className="font-medium capitalize">{dirName}</h3>
                  <p className="text-2xl font-bold text-primary">{stats.file_count}</p>
                  <p className="text-xs text-muted-foreground">
                    {stats.total_size_mb > 0 ? `${stats.total_size_mb} MB` : 'Empty'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Vault Path */}
        {vaultInfo && (
          <div className="mb-6 p-4 glass-card rounded-lg border border-border/30">
            <div className="flex items-center space-x-2 text-sm">
              <HardDrive className="h-4 w-4" />
              <span className="font-medium">Vault Location:</span>
              <code className="bg-muted px-2 py-1 rounded text-xs font-mono">
                {vaultInfo.vault_path}
              </code>
            </div>
          </div>
        )}

        {/* Files List */}
        <div className="glass-card rounded-lg border border-border/30">
          <div className="p-4 border-b border-border/30">
            <h2 className="text-lg font-semibold capitalize">
              {selectedDirectory} Directory
              {loading && <Loader2 className="inline-block ml-2 h-4 w-4 animate-spin" />}
            </h2>
            <p className="text-sm text-muted-foreground">
              Showing {vaultFiles?.length || 0} files
            </p>
          </div>

          <div className="divide-y divide-border/30">
            {(!vaultFiles || vaultFiles.length === 0) ? (
              <div className="p-8 text-center">
                <div className="text-4xl mb-2">{getDirectoryIcon(selectedDirectory)}</div>
                <p className="text-muted-foreground">No files in this directory</p>
              </div>
            ) : (
              vaultFiles?.map((file, index) => (
                <div key={index} className="p-4 hover:bg-muted/30 transition-colors">
                  <div className="flex items-start space-x-4">
                    {/* File Type Icon */}
                    <div className="flex-shrink-0 mt-1">
                      <div className="w-8 h-8 rounded bg-primary/10 flex items-center justify-center">
                        <span className="text-xs font-mono text-primary">
                          {file.extension.toUpperCase() || 'BIN'}
                        </span>
                      </div>
                    </div>

                    {/* File Details */}
                    <div className="flex-1 min-w-0">
                      {/* Hash and Path */}
                      <div className="mb-2">
                        <div className="flex items-center space-x-2 mb-1">
                          <Hash className="h-3 w-3 text-muted-foreground" />
                          <code className="text-sm font-mono bg-muted px-2 py-1 rounded truncate">
                            {file.hash}
                          </code>
                        </div>
                        <p className="text-xs text-muted-foreground font-mono">
                          {file.path}
                        </p>
                      </div>

                      {/* Database Link */}
                      {file.database_record ? (
                        <div className="flex items-center space-x-2 mb-2">
                          <Link className="h-3 w-3 text-green-500" />
                          <span className="text-sm text-green-600">
                            ↔ {file.database_record.original_path}
                          </span>
                          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                            file.database_record.status === 'ready' 
                              ? 'bg-green-100 text-green-800'
                              : file.database_record.status === 'pending'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {file.database_record.status}
                          </span>
                        </div>
                      ) : (
                        <div className="flex items-center space-x-2 mb-2">
                          <AlertCircle className="h-3 w-3 text-orange-500" />
                          <span className="text-sm text-orange-600">No database record</span>
                        </div>
                      )}

                      {/* File Stats */}
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-xs text-muted-foreground">
                        <div className="flex items-center space-x-1">
                          <HardDrive className="h-3 w-3" />
                          <span>{formatFileSize(file.size_bytes)}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Calendar className="h-3 w-3" />
                          <span>{formatDate(file.created_at)}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Database className="h-3 w-3" />
                          <span>ID: {file.database_record?.id?.slice(0, 8) || 'None'}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default VaultPage;