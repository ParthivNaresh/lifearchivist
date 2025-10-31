/**
 * Timeline API functions
 */

import { type TimelineData, type TimelineSummary } from './types';

const API_BASE = 'http://localhost:8000/api';

export async function fetchTimelineData(
  startDate?: string,
  endDate?: string
): Promise<TimelineData> {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);

  const url = `${API_BASE}/timeline/data${params.toString() ? `?${params.toString()}` : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch timeline data: ${response.statusText}`);
  }

  return response.json() as Promise<TimelineData>;
}

export async function fetchTimelineSummary(): Promise<TimelineSummary> {
  const response = await fetch(`${API_BASE}/timeline/summary`);

  if (!response.ok) {
    throw new Error(`Failed to fetch timeline summary: ${response.statusText}`);
  }

  return response.json() as Promise<TimelineSummary>;
}
