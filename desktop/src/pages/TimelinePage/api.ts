import apiClient from '../../utils/api-client';
import { type TimelineData, type TimelineSummary } from './types';

export async function fetchTimelineData(
  startDate?: string,
  endDate?: string
): Promise<TimelineData> {
  const params: Record<string, string> = {};
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;

  return await apiClient.get<TimelineData>('/api/timeline/data', { params });
}

export async function fetchTimelineSummary(): Promise<TimelineSummary> {
  return await apiClient.get<TimelineSummary>('/api/timeline/summary');
}
