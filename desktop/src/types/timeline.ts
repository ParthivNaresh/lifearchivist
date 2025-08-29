export type ZoomLevel = 'year' | 'month' | 'week' | 'day';

export interface TimelineDocument {
  id: string;
  title: string;
  content_date: string;
  file_type: string;
  size_bytes: number;
  confidence_score: number;
  date_type: string | null;
  snippet: string | null;
}

export interface TimelineResponse {
  documents: TimelineDocument[];
  period_start: string;
  period_end: string;
  total_documents: number;
  zoom_level: string;
}

export interface TimePeriodSummary {
  year: number;
  month: number;
  document_count: number;
  period_label: string;
}

export interface TimelinePeriodsResponse {
  earliest_date: string;
  latest_date: string;
  total_documents: number;
  periods: TimePeriodSummary[];
}

export interface ContentDate {
  id: string;
  document_id: string;
  extracted_date: string;
  confidence_score: number;
  context_text: string | null;
  date_type: string | null;
  extraction_method: string;
  created_at: string | null;
}

export interface DocumentContentDatesResponse {
  document_id: string;
  content_dates: ContentDate[];
  total_dates: number;
}

export interface DateRange {
  start: Date;
  end: Date;
}

export interface TimelineState {
  documents: TimelineDocument[];
  loading: boolean;
  error: string | null;
  zoomLevel: ZoomLevel;
  selectedDate: Date;
  dateRange: DateRange | null;
  periods: TimelinePeriodsResponse | null;
}