import { Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from './contexts/ThemeProvider';
import { UploadQueueProvider } from './contexts/UploadQueueContext';
import Layout from './components/Layout';
import InboxPage from './pages/InboxPage';
import DocumentDetailPage from './pages/DocumentDetailPage';
import VaultPage from './pages/VaultPage';
import TimelinePage from './pages/TimelinePage';
import QAPage from './pages/QAPage';
import ConversationsPage from './pages/ConversationsPage';
import SearchPage from './pages/SearchPage';
import SettingsPage from './pages/SettingsPage';
import ActivityPage from './pages/ActivityPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <UploadQueueProvider>
          <Layout>
            <Routes>
              <Route path="/" element={<InboxPage />} />
              <Route path="/vault" element={<VaultPage />} />
              <Route path="/vault/:documentId/details" element={<DocumentDetailPage />} />
              <Route path="/timeline" element={<TimelinePage />} />
              <Route path="/activity" element={<ActivityPage />} />
              <Route path="/qa" element={<QAPage />} />
              <Route path="/conversations" element={<ConversationsPage />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </Layout>
        </UploadQueueProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
