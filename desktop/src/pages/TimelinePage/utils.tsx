/**
 * Timeline utility functions
 */

import { MONTH_NAMES, MONTH_NAMES_SHORT } from './constants';

export function getMonthName(monthNumber: string, short: boolean = false): string {
  const index = parseInt(monthNumber, 10) - 1;
  return short ? MONTH_NAMES_SHORT[index] : MONTH_NAMES[index];
}

export function formatDateRange(earliest: string | null, latest: string | null): string {
  if (!earliest || !latest) return 'No documents';
  
  const start = new Date(earliest);
  const end = new Date(latest);
  
  if (start.getFullYear() === end.getFullYear()) {
    return `${start.getFullYear()}`;
  }
  
  return `${start.getFullYear()} - ${end.getFullYear()}`;
}

export function sortYears(years: string[]): string[] {
  return years.sort((a, b) => parseInt(b, 10) - parseInt(a, 10));
}

export function sortMonths(months: string[]): string[] {
  return months.sort((a, b) => parseInt(a, 10) - parseInt(b, 10));
}

export function getThemeDistribution(documents: Array<{ theme: string | null }>): Record<string, number> {
  const distribution: Record<string, number> = {};
  
  documents.forEach(doc => {
    const theme = doc.theme || 'Unclassified';
    distribution[theme] = (distribution[theme] || 0) + 1;
  });
  
  return distribution;
}

export function getDominantTheme(documents: Array<{ theme: string | null }>): string {
  const themeCounts: Record<string, number> = {};
  
  documents.forEach(doc => {
    const theme = doc.theme || 'Unclassified';
    themeCounts[theme] = (themeCounts[theme] || 0) + 1;
  });
  
  let dominantTheme = 'Unclassified';
  let maxCount = 0;
  
  Object.entries(themeCounts).forEach(([theme, count]) => {
    if (count > maxCount) {
      maxCount = count;
      dominantTheme = theme;
    }
  });
  
  return dominantTheme;
}
