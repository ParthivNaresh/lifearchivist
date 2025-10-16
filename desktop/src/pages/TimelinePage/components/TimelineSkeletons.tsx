/**
 * Skeleton loading states for timeline
 */

import React from 'react';

/**
 * Skeleton for a single document card
 */
export const DocumentCardSkeleton: React.FC = () => (
  <div className="w-full flex items-center gap-4 p-4 backdrop-blur-xl rounded-lg border-l-4 border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-900/50 mb-3 animate-pulse">
    {/* Icon skeleton */}
    <div className="w-8 h-8 bg-gray-200 dark:bg-gray-700 rounded-full flex-shrink-0" />
    
    <div className="flex-1 min-w-0">
      {/* Title skeleton */}
      <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2" />
      {/* Metadata skeleton */}
      <div className="flex items-center gap-2">
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-20" />
        <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24" />
      </div>
    </div>
    
    {/* Icon skeleton */}
    <div className="w-5 h-5 bg-gray-200 dark:bg-gray-700 rounded flex-shrink-0" />
  </div>
);

/**
 * Skeleton for a month section
 */
export const MonthSectionSkeleton: React.FC = () => (
  <div className="mb-8">
    {/* Month header skeleton */}
    <div className="mb-4 animate-pulse">
      <div className="h-7 bg-gray-200 dark:bg-gray-700 rounded w-48 mb-2" />
      <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-32" />
    </div>
    
    {/* Document cards */}
    <div className="space-y-3">
      <DocumentCardSkeleton />
      <DocumentCardSkeleton />
      <DocumentCardSkeleton />
    </div>
  </div>
);

/**
 * Skeleton for a year section
 */
export const YearSectionSkeleton: React.FC = () => (
  <div className="mb-12">
    {/* Year header skeleton */}
    <div className="flex items-center gap-3 mb-6 animate-pulse">
      <div className="w-8 h-8 bg-gray-200 dark:bg-gray-700 rounded-full" />
      <div className="h-9 bg-gray-200 dark:bg-gray-700 rounded w-32" />
      <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-24" />
    </div>
    
    {/* Month sections */}
    <MonthSectionSkeleton />
    <MonthSectionSkeleton />
  </div>
);

/**
 * Full timeline skeleton loader
 */
export const TimelineLoadingSkeleton: React.FC = () => (
  <div className="space-y-0">
    <YearSectionSkeleton />
    <YearSectionSkeleton />
  </div>
);

/**
 * Search loading indicator (subtle)
 */
export const SearchLoadingIndicator: React.FC = () => (
  <div className="flex items-center justify-center py-4">
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      <span>Searching...</span>
    </div>
  </div>
);
