/**
 * Timeline page types
 */

export interface TimelineDocument {
  id: string;
  title: string;
  date: string;
  mime_type: string;
  theme: string | null;
}

export interface TimelineMonth {
  count: number;
  documents: TimelineDocument[];
}

export interface TimelineYear {
  count: number;
  months: Record<string, TimelineMonth>;
}

export interface TimelineData {
  total_documents: number;
  date_range: {
    earliest: string | null;
    latest: string | null;
  };
  by_year: Record<string, TimelineYear>;
  documents_without_dates: number;
}

export interface TimelineSummary {
  total_documents: number;
  date_range: {
    earliest: string | null;
    latest: string | null;
  };
  by_year: Record<string, number>;
  data_quality: {
    with_document_created_at: number;
    with_platform_dates: number;
    fallback_to_disk: number;
    no_dates: number;
  };
}
