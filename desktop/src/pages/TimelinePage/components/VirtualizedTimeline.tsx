/**
 * Virtualized timeline component
 * Renders only visible items for performance with large datasets
 */

import React, { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { ChevronDown, ChevronRight, FileText } from 'lucide-react';
import { VirtualItem } from '../virtualization-types';
import { getThemeColors } from '../theme-config';
import { useTimelineNavigation } from '../hooks';

interface VirtualizedTimelineProps {
  items: VirtualItem[];
  onToggleYear: (year: string) => void;
}

export const VirtualizedTimeline: React.FC<VirtualizedTimelineProps> = ({
  items,
  onToggleYear,
}) => {
  const parentRef = useRef<HTMLDivElement>(null);
  const { handleDocumentClick } = useTimelineNavigation();

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: (index) => {
      const item = items[index];
      if (item.type === 'year') return 80;
      if (item.type === 'month') return 60;
      return 100; // document card
    },
    overscan: 5, // Render 5 extra items above/below viewport
  });

  const renderItem = (item: VirtualItem) => {
    switch (item.type) {
      case 'year':
        return (
          <button
            onClick={() => onToggleYear(item.year)}
            className="flex items-center gap-3 text-3xl font-bold mb-6 hover:text-primary transition-colors w-full text-left group"
          >
            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 group-hover:bg-primary/20 transition-colors">
              {item.isExpanded ? (
                <ChevronDown className="h-5 w-5 text-primary transition-transform duration-200" />
              ) : (
                <ChevronRight className="h-5 w-5 text-primary transition-transform duration-200" />
              )}
            </div>
            <span>{item.year}</span>
            <span className="text-base font-normal text-muted-foreground ml-2">
              {item.count} {item.count === 1 ? 'document' : 'documents'}
            </span>
          </button>
        );

      case 'month':
        return (
          <div className="mb-4">
            <div className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm py-3 mb-4 border-b border-border/50">
              <h3 className="text-xl font-bold">{item.monthName} {item.year}</h3>
              <p className="text-sm text-muted-foreground">
                {item.count} {item.count === 1 ? 'document' : 'documents'}
              </p>
            </div>
          </div>
        );

      case 'document':
        const doc = item.document;
        const themeColors = getThemeColors(doc.theme);
        
        return (
          <button
            onClick={() => handleDocumentClick(doc.id)}
            className={`w-full flex items-center gap-4 p-4 backdrop-blur-xl rounded-lg transition-all duration-200 text-left group border-l-4 mb-3 ${themeColors.bg} ${themeColors.bgHover} ${themeColors.border} ${themeColors.borderHover} shadow-sm hover:shadow-md`}
          >
            {/* Theme icon */}
            <span className="text-2xl flex-shrink-0">{themeColors.icon}</span>
            
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{doc.title}</p>
              <div className="flex items-center gap-2 text-sm mt-1">
                {doc.theme && (
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${themeColors.badge}`}>
                    {doc.theme}
                  </span>
                )}
                <span className="text-muted-foreground">
                  {new Date(doc.date).toLocaleDateString()}
                </span>
              </div>
            </div>
            
            <FileText className={`h-5 w-5 transition-colors flex-shrink-0 ${themeColors.text}`} />
          </button>
        );

      default:
        return null;
    }
  };

  return (
    <div
      ref={parentRef}
      data-virtualized-timeline
      className="h-full overflow-auto"
      style={{ contain: 'strict' }}
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => {
          const item = items[virtualItem.index];
          
          return (
            <div
              key={virtualItem.key}
              data-index={virtualItem.index}
              ref={virtualizer.measureElement}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              {renderItem(item)}
            </div>
          );
        })}
      </div>
    </div>
  );
};
