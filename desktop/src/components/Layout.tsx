import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { cn } from '../utils/cn';
import UploadQueue from './upload/UploadQueue';
import UploadQueueTrigger from './upload/UploadQueueTrigger';
import { useUploadQueue } from '../contexts/UploadQueueContext';
import { 
  Inbox, 
  Search, 
  Settings, 
  FileText,
  Database,
  HardDrive,
  Activity,
  MessageCircle,
  DollarSign
} from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const { state: uploadQueueState } = useUploadQueue();
  
  // Only show the floating upload queue on non-inbox pages or when there are completed/error batches
  const showFloatingQueue = location.pathname !== '/' || 
    uploadQueueState.batches.some(b => 
      b.status === 'error' || 
      (b.status !== 'active' && b.createdAt < Date.now() - 60000) // Older completed batches
    );

  const navigation = [
    { name: 'Inbox', href: '/', icon: Inbox },
    { name: 'Vault', href: '/vault', icon: HardDrive },
    { name: 'Q&A', href: '/qa', icon: MessageCircle },
    { name: 'Search', href: '/search', icon: Search },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <div className="w-64 glass-card border-r border-border/30">
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b border-border">
            <div className="flex items-center space-x-3">
              <Database className="h-8 w-8 text-primary" />
              <h1 className="text-lg font-semibold">Life Archivist</h1>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    'flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>

          {/* Status */}
          <div className="p-4 border-t border-border">
            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
              <Activity className="h-4 w-4 text-green-500" />
              <span>Server Connected</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>

      {/* Upload Queue Components - Only show on non-inbox pages or for history */}
      {showFloatingQueue && (
        <>
          <UploadQueue />
          <UploadQueueTrigger />
        </>
      )}
    </div>
  );
};

export default Layout;