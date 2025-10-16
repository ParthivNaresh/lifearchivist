/**
 * Visual timeline bar component
 * Shows year/month markers with density indicators
 */

import React, { useEffect, useState, useRef } from 'react';
import { TimelineData } from '../types';
import { getMonthName, sortYears, sortMonths, getDominantTheme } from '../utils';
import { getThemeColors } from '../theme-config';

interface TimelineBarProps {
  timelineData: TimelineData;
  onJumpToSection: (year: string, month?: string) => void;
}

interface TimelineSegment {
  year: string;
  month: string;
  count: number;
  label: string;
  id: string;
}

export const TimelineBar: React.FC<TimelineBarProps> = ({ timelineData, onJumpToSection }) => {
  const [activeSegment, setActiveSegment] = useState<string | null>(null);
  const barRef = useRef<HTMLDivElement>(null);

  // Build timeline segments
  const segments: TimelineSegment[] = [];
  const years = sortYears(Object.keys(timelineData.by_year));
  
  years.forEach(year => {
    const yearData = timelineData.by_year[year];
    const months = sortMonths(Object.keys(yearData.months));
    
    months.forEach(month => {
      const monthData = yearData.months[month];
      segments.push({
        year,
        month,
        count: monthData.count,
        label: `${getMonthName(month, true)} ${year}`,
        id: `timeline-${year}-${month}`
      });
    });
  });

  // Calculate max count for density scaling
  const maxCount = Math.max(...segments.map(s => s.count), 1);

  // Track scroll position to highlight active segment
  useEffect(() => {
    // Find the virtualized timeline scroll container
    const scrollContainer = document.querySelector('[data-virtualized-timeline]');
    if (!scrollContainer) {
      return;
    }

    const handleScroll = () => {
      const scrollTop = scrollContainer.scrollTop;
      const detectionPoint = scrollTop + 100; // 100px from top of container
      
      let foundActive = false;
      
      // Find which month is at the detection point based on scroll position
      // Since items are virtualized, we estimate based on scroll position
      let accumulatedHeight = 0;
      
      for (const segment of segments) {
        const year = segment.year;
        const month = segment.month;
        
        // Estimate heights: year header ~80px, month header ~60px, each doc ~100px
        const yearData = timelineData.by_year[year];
        const monthData = yearData?.months[month];
        
        if (!monthData) continue;
        
        const monthHeight = 60 + (monthData.count * 103); // 60 for header, 103 per doc (100 + 3 margin)
        
        if (detectionPoint >= accumulatedHeight && detectionPoint < accumulatedHeight + monthHeight) {
          setActiveSegment(segment.id);
          foundActive = true;
          break;
        }
        
        accumulatedHeight += monthHeight;
      }
      
      // If no segment found, default to first
      if (!foundActive && segments.length > 0) {
        setActiveSegment(segments[0].id);
      }
    };

    // Listen to the virtualized container
    scrollContainer.addEventListener('scroll', handleScroll, { passive: true });
    
    // Initial check
    const timer = setTimeout(handleScroll, 100);
    
    return () => {
      scrollContainer.removeEventListener('scroll', handleScroll);
      clearTimeout(timer);
    };
  }, [segments, timelineData]);

  const handleSegmentClick = (segment: TimelineSegment) => {
    const scrollContainer = document.querySelector('[data-virtualized-timeline]');
    if (!scrollContainer) return;
    
    // Calculate scroll position based on accumulated heights
    let scrollPosition = 0;
    
    for (const seg of segments) {
      if (seg.id === segment.id) {
        break;
      }
      
      const yearData = timelineData.by_year[seg.year];
      const monthData = yearData?.months[seg.month];
      
      if (monthData) {
        // Add height for this month section
        scrollPosition += 60 + (monthData.count * 103); // 60 for header, 103 per doc
      }
    }
    
    // Scroll to calculated position
    scrollContainer.scrollTo({
      top: scrollPosition,
      behavior: 'smooth'
    });
    
    onJumpToSection(segment.year, segment.month);
  };

  return (
    <div 
      ref={barRef}
      className="fixed left-64 top-0 h-screen w-32 bg-background/50 backdrop-blur-sm border-r border-border/30 z-20 hidden lg:flex flex-col items-center py-20"
    >
      {/* Vertical connecting line - positioned more to the right */}
      <div className="absolute left-20 top-20 bottom-20 w-0.5 bg-gradient-to-b from-border/50 via-border to-border/50" />
      
      <div className="flex-1 flex flex-col justify-between w-full pl-16 pr-4 relative">
        {segments.map((segment, index) => {
          const density = segment.count / maxCount;
          const isActive = activeSegment === segment.id;
          const barWidth = Math.max(density * 100, 20); // Min 20% width
          
          // Get dominant theme for this month
          const monthData = timelineData.by_year[segment.year]?.months[segment.month];
          const dominantTheme = monthData ? getDominantTheme(monthData.documents) : 'Unclassified';
          const themeColors = getThemeColors(dominantTheme);
          
          return (
            <button
              key={segment.id}
              onClick={() => handleSegmentClick(segment)}
              className="group relative flex items-center justify-center py-2 transition-all duration-200 z-10"
              title={`${segment.label} (${segment.count} ${segment.count === 1 ? 'doc' : 'docs'})`}
            >
              {/* Connection dot on timeline - enhanced for active state */}
              <div className={`absolute left-1/2 -translate-x-1/2 rounded-full border-2 border-background transition-all duration-300 ${
                isActive 
                  ? `w-4 h-4 ${themeColors.accent} shadow-lg shadow-primary/50` 
                  : `w-2 h-2 ${themeColors.accent} opacity-60 group-hover:scale-125 group-hover:opacity-100`
              }`}>
                {/* Pulsing ring for active segment */}
                {isActive && (
                  <div className="absolute -inset-2 rounded-full border-2 border-primary animate-ping opacity-50" />
                )}
              </div>
              
              {/* Timeline bar segment with theme color and glow */}
              <div
                className={`h-3 rounded-full transition-all duration-300 relative ${
                  isActive 
                    ? `${themeColors.accent} shadow-lg` 
                    : `${themeColors.accent} opacity-40 group-hover:opacity-80`
                }`}
                style={{ 
                  width: `${barWidth}%`,
                  boxShadow: isActive ? '0 0 20px currentColor' : undefined
                }}
              >
                {/* Inner glow effect */}
                {isActive && (
                  <div className="absolute inset-0 rounded-full bg-white/30 animate-pulse" />
                )}
              </div>
              
              {/* Tooltip on hover */}
              <div className="absolute left-full ml-4 px-3 py-2 bg-popover text-popover-foreground text-xs rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap border border-border">
                <div className="font-semibold">{segment.label}</div>
                <div className="text-muted-foreground">
                  {segment.count} {segment.count === 1 ? 'document' : 'documents'}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Year markers on the left */}
      <div className="absolute left-2 top-20 bottom-20 pointer-events-none z-20">
        {years.map((year, index) => {
          const firstSegmentIndex = segments.findIndex(s => s.year === year);
          const position = (firstSegmentIndex / segments.length) * 100;
          
          return (
            <div
              key={year}
              className="absolute left-0"
              style={{ top: `${position}%`, transform: 'translateY(-50%)' }}
            >
              {/* Horizontal line connecting to timeline */}
              <div className="absolute left-full w-12 h-px bg-border/30 top-1/2" />
              
              {/* Year badge - clean and simple */}
              <div className="px-2.5 py-1 rounded-md shadow-md text-xs font-bold bg-background border border-border text-foreground">
                {year}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
