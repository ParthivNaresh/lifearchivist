import React from 'react';

// Import from extracted modules
import {
  useVaultData,
  useFileSystem,
  useVaultNavigation,
  useVaultSearch,
  useVaultViewMode,
  useVaultActions,
  useCurrentStats,
  useAutoRefresh,
  useCurrentItems,
  VaultHeader,
  ViewModeToggle,
  SearchBar,
  ActionButtons,
  Breadcrumbs,
  StatusBar,
  FileExplorer
} from './VaultPage/index';

const VaultPage: React.FC = () => {
  
  // Use custom hooks
  const { viewMode, setViewMode } = useVaultViewMode();
  const { 
    vaultInfo, 
    documents, 
    documentsLoading, 
    refreshDocuments, 
    manualRefresh 
  } = useVaultData();
  
  const {
    currentPath,
    navigationPath,
    isTransitioning,
    navigateToBreadcrumb,
    handleFileClick,
    resetPath
  } = useVaultNavigation();
  
  const {
    searchTerm,
    setSearchTerm,
    isSearching,
    setIsSearching,
    clearSearch,
    filterItems
  } = useVaultSearch();
  
  const {
    refreshing,
    clearing,
    handleRefresh,
    handleClearVault
  } = useVaultActions(manualRefresh, resetPath);
  
  // Build file system
  const fileSystem = useFileSystem(documents);
  
  // Get current items
  const currentItems = useCurrentItems(fileSystem, navigationPath);
  
  // Filter items
  const filteredItems = filterItems(currentItems);
  
  // Calculate stats
  const currentStats = useCurrentStats(filteredItems);
  
  // Auto-refresh for processing documents
  useAutoRefresh(documents, refreshDocuments);

  return (
    <div className="p-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <VaultHeader />
        
        <div className="flex items-center space-x-3">
          <ViewModeToggle 
            viewMode={viewMode}
            onViewModeChange={setViewMode}
          />
          
          <SearchBar
            searchTerm={searchTerm}
            isSearching={isSearching}
            onSearchTermChange={setSearchTerm}
            onSearchingChange={setIsSearching}
          />
          
          <ActionButtons
            refreshing={refreshing}
            clearing={clearing}
            documentsCount={documents?.length || 0}
            onRefresh={handleRefresh}
            onClearVault={handleClearVault}
          />
        </div>
      </div>

      {/* Breadcrumb Navigation */}
      <div className="mb-4">
        <Breadcrumbs 
          currentPath={currentPath}
          onNavigate={navigateToBreadcrumb}
        />
      </div>

      {/* Status Bar */}
      <div className="mb-4">
        <StatusBar
          currentPath={currentPath}
          currentStats={currentStats}
          documentsCount={documents?.length || 0}
          vaultInfo={vaultInfo}
        />
      </div>

      {/* File Explorer */}
      <FileExplorer
        documentsLoading={documentsLoading}
        documents={documents}
        filteredItems={filteredItems}
        viewMode={viewMode}
        searchTerm={searchTerm}
        isTransitioning={isTransitioning}
        onItemClick={handleFileClick}
      />
    </div>
  );
};

export default VaultPage;