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
  FileExplorer,
} from './VaultPage/index';

const VaultPage: React.FC = () => {
  // Use custom hooks
  const { viewMode, setViewMode } = useVaultViewMode();
  const { vaultInfo, documents, documentsLoading, refreshDocuments, manualRefresh } =
    useVaultData();

  const {
    currentPath,
    navigationPath,
    isTransitioning,
    navigateToBreadcrumb,
    handleFileClick,
    resetPath,
  } = useVaultNavigation();

  const { searchTerm, setSearchTerm, isSearching, setIsSearching, filterItems } = useVaultSearch();

  const {
    refreshing,
    clearing,
    showClearConfirm,
    handleRefresh,
    handleClearVault,
    confirmClearVault,
    cancelClearVault,
  } = useVaultActions(manualRefresh, resetPath);

  // Build file system
  const fileSystem = useFileSystem(documents ?? undefined);

  // Get current items
  const currentItems = useCurrentItems(fileSystem, navigationPath);

  // Filter items
  const filteredItems = filterItems(currentItems);

  // Calculate stats
  const currentStats = useCurrentStats(filteredItems);

  // Auto-refresh for processing documents
  useAutoRefresh(documents ?? undefined, refreshDocuments);

  return (
    <div className="p-6 h-full flex flex-col">
      {/* Clear Vault Confirmation Modal */}
      {showClearConfirm && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-lg shadow-xl max-w-md w-full p-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-destructive/10 rounded-full">
                <svg
                  className="h-6 w-6 text-destructive"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold mb-2">Clear Entire Vault</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Are you sure you want to clear the entire vault? This will permanently delete all
                  files and their associated document records. This cannot be undone.
                </p>
                <div className="flex gap-3 justify-end">
                  <button
                    onClick={cancelClearVault}
                    disabled={clearing}
                    className="px-4 py-2 text-sm border border-border rounded-md hover:bg-accent transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => void confirmClearVault()}
                    disabled={clearing}
                    className="px-4 py-2 text-sm bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90 transition-colors disabled:opacity-50 flex items-center gap-2"
                  >
                    {clearing ? (
                      <>
                        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-current" />
                        Clearing...
                      </>
                    ) : (
                      'Clear Vault'
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <VaultHeader />

        <div className="flex items-center space-x-3">
          <ViewModeToggle viewMode={viewMode} onViewModeChange={setViewMode} />

          <SearchBar
            searchTerm={searchTerm}
            isSearching={isSearching}
            onSearchTermChange={setSearchTerm}
            onSearchingChange={setIsSearching}
          />

          <ActionButtons
            refreshing={refreshing}
            clearing={clearing}
            documentsCount={documents?.length ?? 0}
            onRefresh={() => void handleRefresh()}
            onClearVault={() => void handleClearVault()}
          />
        </div>
      </div>

      {/* Breadcrumb Navigation */}
      <div className="mb-4">
        <Breadcrumbs currentPath={currentPath} onNavigate={navigateToBreadcrumb} />
      </div>

      {/* Status Bar */}
      <div className="mb-4">
        <StatusBar
          currentPath={currentPath}
          currentStats={currentStats}
          documentsCount={documents?.length ?? 0}
          vaultInfo={vaultInfo ?? undefined}
        />
      </div>

      {/* File Explorer */}
      <FileExplorer
        documentsLoading={documentsLoading}
        documents={documents ?? undefined}
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
