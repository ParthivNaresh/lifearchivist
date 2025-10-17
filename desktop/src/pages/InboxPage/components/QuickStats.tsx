/**
 * QuickStats - Dashboard statistics cards
 * 
 * Displays key metrics: total documents, weekly uploads, storage usage
 */

import React from 'react';
import { Database, TrendingUp, LucideIcon } from 'lucide-react';
import { BYTES_PER_MB } from '../constants';

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  iconColor?: string;
}

interface QuickStatsProps {
  totalDocuments: number;
  weekCount: number;
  storageBytes: number;
  isLoading?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, icon: Icon, iconColor = 'text-primary' }) => (
  <div className="glass-card rounded-xl p-6">
    <div className="flex items-center justify-between mb-2">
      <span className="text-sm text-muted-foreground">{label}</span>
      <Icon className={`h-5 w-5 ${iconColor}`} />
    </div>
    <div className="text-3xl font-bold">
      {value}
    </div>
  </div>
);

export const QuickStats: React.FC<QuickStatsProps> = ({
  totalDocuments,
  weekCount,
  storageBytes,
  isLoading = false,
}) => {
  const formatStorage = (bytes: number): string => {
    return `${(bytes / BYTES_PER_MB).toFixed(0)} MB`;
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <StatCard
        label="Total Documents"
        value={isLoading ? '...' : totalDocuments.toLocaleString()}
        icon={Database}
        iconColor="text-primary"
      />
      
      <StatCard
        label="This Week"
        value={isLoading ? '...' : weekCount}
        icon={TrendingUp}
        iconColor="text-emerald-500"
      />
      
      <StatCard
        label="Storage Used"
        value={isLoading ? '...' : formatStorage(storageBytes)}
        icon={Database}
        iconColor="text-blue-500"
      />
    </div>
  );
};
