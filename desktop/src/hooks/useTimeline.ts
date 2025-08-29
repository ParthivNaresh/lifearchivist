import { useState, useCallback, useEffect } from 'react';
import { useCache, clearCacheKey } from './useCache';
import { 
  TimelineState, 
  TimelineDocument, 
  ZoomLevel, 
  DateRange, 
  TimelinePeriodsResponse 
} from '../types/timeline';
import { 
  timelineApi, 
  calculateDateRange, 
  formatDateForApi, 
  TimelineFilters 
} from '../utils/timelineApi';

const CACHE_KEYS = {
  TIMELINE_DATA: 'timeline-data',
  TIMELINE_PERIODS: 'timeline-periods',
} as const;

export interface UseTimelineOptions {
  initialZoomLevel?: ZoomLevel;
  initialDate?: Date;
  autoFetch?: boolean;
}

export interface UseTimelineReturn {
  state: TimelineState;
  actions: {
    setZoomLevel: (level: ZoomLevel) => void;
    setSelectedDate: (date: Date) => void;
    navigateToDate: (date: Date) => void;
    refreshData: () => Promise<void>;
    fetchTimelineData: (filters?: TimelineFilters) => Promise<void>;
    clearCache: () => void;
  };
}

export const useTimeline = (options: UseTimelineOptions = {}): UseTimelineReturn => {
  const {
    initialZoomLevel = 'month',
    initialDate = new Date(),
    autoFetch = true
  } = options;

  const [state, setState] = useState<TimelineState>({
    documents: [],
    loading: false,
    error: null,
    zoomLevel: initialZoomLevel,
    selectedDate: initialDate,
    dateRange: null,
    periods: null,
  });

  const [hasInitializedDate, setHasInitializedDate] = useState(false);

  const fetchTimelinePeriods = useCallback(async () => {
    try {
      const periods = await timelineApi.getTimelinePeriods();
      setState(prev => ({ ...prev, periods }));

      // Auto-adjust selected date to latest available date if not manually set
      if (!hasInitializedDate && periods.latest_date && periods.total_documents > 0) {
        const latestDate = new Date(periods.latest_date);
        setState(prev => ({ 
          ...prev, 
          selectedDate: latestDate,
        }));
        setHasInitializedDate(true);
      }

      return periods;
    } catch (error) {
      console.error('Failed to fetch timeline periods:', error);
      setState(prev => ({ 
        ...prev, 
        error: error instanceof Error ? error.message : 'Failed to fetch timeline periods'
      }));
      return null;
    }
  }, [hasInitializedDate]);

  const fetchTimelineData = useCallback(async (filters: TimelineFilters = {}) => {
    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const dateRange = calculateDateRange(state.zoomLevel, state.selectedDate);
      
      const apiFilters: TimelineFilters = {
        startDate: formatDateForApi(dateRange.start),
        endDate: formatDateForApi(dateRange.end),
        zoomLevel: state.zoomLevel,
        limit: 100,
        ...filters
      };

      const response = await timelineApi.getTimelineData(apiFilters);
      
      setState(prev => ({
        ...prev,
        documents: response.documents,
        dateRange,
        loading: false,
        error: null
      }));

    } catch (error) {
      console.error('Failed to fetch timeline data:', error);
      setState(prev => ({
        ...prev,
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch timeline data'
      }));
    }
  }, [state.zoomLevel, state.selectedDate]);

  const setZoomLevel = useCallback((level: ZoomLevel) => {
    setState(prev => ({ ...prev, zoomLevel: level }));
  }, []);

  const setSelectedDate = useCallback((date: Date) => {
    setState(prev => ({ ...prev, selectedDate: date }));
    setHasInitializedDate(true); // Mark as manually set
  }, []);

  const navigateToDate = useCallback((date: Date) => {
    setState(prev => ({ ...prev, selectedDate: date }));
    setHasInitializedDate(true); // Mark as manually set
    // The useEffect will automatically trigger fetchTimelineData when selectedDate changes
  }, []);

  const refreshData = useCallback(async () => {
    await Promise.all([
      fetchTimelineData(),
      fetchTimelinePeriods()
    ]);
  }, [fetchTimelineData, fetchTimelinePeriods]);

  const clearCache = useCallback(() => {
    clearCacheKey(CACHE_KEYS.TIMELINE_DATA);
    clearCacheKey(CACHE_KEYS.TIMELINE_PERIODS);
  }, []);

  // Auto-fetch data when zoom level or selected date changes
  useEffect(() => {
    if (autoFetch) {
      fetchTimelineData();
    }
  }, [state.zoomLevel, state.selectedDate, autoFetch, fetchTimelineData]);

  // Fetch periods on mount
  useEffect(() => {
    if (autoFetch) {
      fetchTimelinePeriods();
    }
  }, [autoFetch, fetchTimelinePeriods]);

  return {
    state,
    actions: {
      setZoomLevel,
      setSelectedDate,
      navigateToDate,
      refreshData,
      fetchTimelineData,
      clearCache,
    }
  };
};

export default useTimeline;