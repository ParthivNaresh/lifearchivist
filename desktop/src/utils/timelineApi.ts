import axios from 'axios';
import { 
  TimelineResponse, 
  TimelinePeriodsResponse, 
  DocumentContentDatesResponse,
  ZoomLevel 
} from '../types/timeline';

const API_BASE_URL = 'http://localhost:8000/api';

export interface TimelineFilters {
  startDate?: string;
  endDate?: string;
  zoomLevel?: ZoomLevel;
  limit?: number;
}

export const timelineApi = {
  async getTimelineData(filters: TimelineFilters = {}): Promise<TimelineResponse> {
    const params = new URLSearchParams();
    
    if (filters.startDate) {
      params.append('start_date', filters.startDate);
    }
    if (filters.endDate) {
      params.append('end_date', filters.endDate);
    }
    if (filters.zoomLevel) {
      params.append('zoom_level', filters.zoomLevel);
    }
    if (filters.limit) {
      params.append('limit', filters.limit.toString());
    }

    const response = await axios.get<TimelineResponse>(
      `${API_BASE_URL}/timeline?${params}`
    );
    return response.data;
  },

  async getTimelinePeriods(): Promise<TimelinePeriodsResponse> {
    const response = await axios.get<TimelinePeriodsResponse>(
      `${API_BASE_URL}/timeline/periods`
    );
    return response.data;
  },

  async getDocumentContentDates(documentId: string): Promise<DocumentContentDatesResponse> {
    const response = await axios.get<DocumentContentDatesResponse>(
      `${API_BASE_URL}/documents/${documentId}/content-dates`
    );
    return response.data;
  }
};

export const calculateDateRange = (zoomLevel: ZoomLevel, selectedDate: Date) => {
  const start = new Date(selectedDate);
  const end = new Date(selectedDate);

  console.log(`Calculating date range for ${zoomLevel} with selected date:`, selectedDate);

  switch (zoomLevel) {
    case 'year':
      start.setMonth(0, 1);
      start.setHours(0, 0, 0, 0);
      end.setMonth(11, 31);
      end.setHours(23, 59, 59, 999);
      break;
    
    case 'month':
      start.setDate(1);
      start.setHours(0, 0, 0, 0);
      end.setMonth(end.getMonth() + 1, 0);
      end.setHours(23, 59, 59, 999);
      break;
    
    case 'week':
      const dayOfWeek = start.getDay();
      start.setDate(start.getDate() - dayOfWeek);
      start.setHours(0, 0, 0, 0);
      end.setDate(start.getDate() + 6);
      end.setHours(23, 59, 59, 999);
      break;
    
    case 'day':
      start.setHours(0, 0, 0, 0);
      end.setHours(23, 59, 59, 999);
      break;
  }

  console.log(`Calculated range: ${start.toISOString()} to ${end.toISOString()}`);
  return { start, end };
};

export const formatDateForApi = (date: Date): string => {
  return date.toISOString();
};

export const parseDateFromApi = (dateString: string): Date => {
  return new Date(dateString);
};