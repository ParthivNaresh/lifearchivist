import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import { UploadQueueProvider } from './contexts/UploadQueueContext';
import Layout from './components/Layout';
import InboxPage from './pages/InboxPage';
import DocumentDetailPage from './pages/DocumentDetailPage';
import VaultPage from './pages/VaultPage';
import QAPage from './pages/QAPage';
import SearchPage from './pages/SearchPage';
import SettingsPage from './pages/SettingsPage';
import ActivityPage from './pages/ActivityPage';

function App() {
  return (
    <ThemeProvider>
      <UploadQueueProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<InboxPage />} />
            <Route path="/vault" element={<VaultPage />} />
            <Route path="/vault/:documentId/details" element={<DocumentDetailPage />} />
            <Route path="/activity" element={<ActivityPage />} />
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