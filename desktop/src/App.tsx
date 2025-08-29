import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { UploadQueueProvider } from './contexts/UploadQueueContext';
import Layout from './components/Layout';
import InboxPage from './pages/InboxPage';
import DocumentsPage from './pages/DocumentsPage';
import DocumentDetailPage from './pages/DocumentDetailPage';
import TimelinePage from './pages/TimelinePage';
import VaultPage from './pages/VaultPage';
import EmbeddingsPage from './pages/EmbeddingsPage';
import QAPage from './pages/QAPage';
import SearchPage from './pages/SearchPage';
import SettingsPage from './pages/SettingsPage';

function App() {
  return (
    <ThemeProvider>
      <UploadQueueProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<InboxPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/documents/:documentId/details" element={<DocumentDetailPage />} />
            <Route path="/timeline" element={<TimelinePage />} />
            <Route path="/vault" element={<VaultPage />} />
            <Route path="/embeddings" element={<EmbeddingsPage />} />
            <Route path="/qa" element={<QAPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </Layout>
      </UploadQueueProvider>
    </ThemeProvider>
  );
}

export default App;