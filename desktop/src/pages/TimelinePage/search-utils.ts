/**
 * Search utilities for timeline filtering
 */

import {
  type TimelineData,
  type TimelineDocument,
  type TimelineYear,
  type TimelineMonth,
} from './types';

/**
 * Check if a document matches the search query
 */
export function documentMatchesSearch(doc: TimelineDocument, query: string): boolean {
  if (!query.trim()) return true;

  const searchLower = query.toLowerCase().trim();

  // Search in title
  if (doc.title.toLowerCase().includes(searchLower)) {
    return true;
  }

  // Search in theme
  if (doc.theme?.toLowerCase().includes(searchLower)) {
    return true;
  }

  // Search in mime type (e.g., "pdf", "image")
  if (doc.mime_type?.toLowerCase().includes(searchLower)) {
    return true;
  }

  // Search in date (e.g., "2024", "march")
  if (doc.date?.toLowerCase().includes(searchLower)) {
    return true;
  }

  return false;
}

/**
 * Filter timeline data by search query
 */
export function filterTimelineBySearch(
  timelineData: TimelineData,
  searchQuery: string
): { filteredData: TimelineData; resultCount: number } {
  if (!searchQuery.trim()) {
    return { filteredData: timelineData, resultCount: timelineData.total_documents };
  }

  let resultCount = 0;
  const filteredByYear: Record<string, TimelineYear> = {};

  // Iterate through years
  Object.entries(timelineData.by_year).forEach(([year, yearData]) => {
    const filteredMonths: Record<string, TimelineMonth> = {};
    let yearCount = 0;

    // Iterate through months
    Object.entries(yearData.months).forEach(([month, monthData]) => {
      // Filter documents in this month
      const matchingDocs = monthData.documents.filter((doc) =>
        documentMatchesSearch(doc, searchQuery)
      );

      // Only include month if it has matching documents
      if (matchingDocs.length > 0) {
        filteredMonths[month] = {
          count: matchingDocs.length,
          documents: matchingDocs,
        };
        yearCount += matchingDocs.length;
        resultCount += matchingDocs.length;
      }
    });

    // Only include year if it has matching documents
    if (yearCount > 0) {
      filteredByYear[year] = {
        count: yearCount,
        months: filteredMonths,
      };
    }
  });

  // Find new date range from filtered results
  let earliest: string | null = null;
  let latest: string | null = null;

  Object.values(filteredByYear).forEach((yearData: TimelineYear) => {
    Object.values(yearData.months).forEach((monthData: TimelineMonth) => {
      monthData.documents.forEach((doc: TimelineDocument) => {
        if (!earliest || doc.date < earliest) earliest = doc.date;
        if (!latest || doc.date > latest) latest = doc.date;
      });
    });
  });

  const filteredData: TimelineData = {
    total_documents: resultCount,
    date_range: {
      earliest,
      latest,
    },
    by_year: filteredByYear,
    documents_without_dates: 0,
  };

  return { filteredData, resultCount };
}

/**
 * Debounce function for search input
 *
 * Generic type constraint ensures the function parameter is properly typed
 * without using 'any' types. The return type preserves the original function's
 * parameter types while returning void since debounced functions don't return values.
 */
export function debounce<T extends (...args: never[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      func(...args);
    };

    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, wait);
  };
}
