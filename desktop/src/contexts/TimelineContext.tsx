import React, { createContext, useContext, ReactNode } from 'react';
import { useTimeline, UseTimelineReturn, UseTimelineOptions } from '../hooks/useTimeline';
import { ZoomLevel } from '../types/timeline';

interface TimelineContextType extends UseTimelineReturn {}

const TimelineContext = createContext<TimelineContextType | null>(null);

export const useTimelineContext = (): TimelineContextType => {
  const context = useContext(TimelineContext);
  if (!context) {
    throw new Error('useTimelineContext must be used within a TimelineProvider');
  }
  return context;
};

interface TimelineProviderProps {
  children: ReactNode;
  options?: UseTimelineOptions;
}

export const TimelineProvider: React.FC<TimelineProviderProps> = ({ 
  children, 
  options = {} 
}) => {
  const timeline = useTimeline({
    initialZoomLevel: 'month',
    autoFetch: true,
    ...options
  });

  return (
    <TimelineContext.Provider value={timeline}>
      {children}
    </TimelineContext.Provider>
  );
};

export default TimelineContext;