/**
 * TabNavigation component - renders tab navigation
 */

import { FileText, Link, Clock } from 'lucide-react';
import { TAB_CONFIG, type TabType } from '../index';

interface TabNavigationProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}

const tabs = [
  { id: TAB_CONFIG.OVERVIEW, label: 'Overview', icon: FileText },
  { id: TAB_CONFIG.RELATED, label: 'Related', icon: Link },
  { id: TAB_CONFIG.ACTIVITY, label: 'Activity', icon: Clock },
];

export const TabNavigation: React.FC<TabNavigationProps> = ({ activeTab, onTabChange }) => {
  return (
    <div className="border-b border-border mb-6">
      <nav className="flex space-x-8">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
              activeTab === tab.id
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground'
            }`}
          >
            <tab.icon className="h-4 w-4" />
            <span>{tab.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
};
