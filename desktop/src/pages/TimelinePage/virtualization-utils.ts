/**
 * Utilities for flattening timeline data for virtualization
 */

import { TimelineData } from './types';
import { VirtualItem, VirtualizationState } from './virtualization-types';
import { getMonthName, sortYears, sortMonths } from './utils';

/**
 * Flatten timeline data into a flat array for virtualization
 */
export function flattenTimelineData(
  timelineData: TimelineData,
  state: VirtualizationState
): VirtualItem[] {
  const items: VirtualItem[] = [];
  const years = sortYears(Object.keys(timelineData.by_year));
  
  years.forEach(year => {
    const yearData = timelineData.by_year[year];
    const isYearExpanded = state.expandedYears.has(year);
    
    // Add year item
    items.push({
      id: `year-${year}`,
      type: 'year',
      year,
      count: yearData.count,
      isExpanded: isYearExpanded,
    });
    
    // If year is expanded, add months and documents
    if (isYearExpanded) {
      const months = sortMonths(Object.keys(yearData.months));
      
      months.forEach(month => {
        const monthData = yearData.months[month];
        
        // Add month item
        items.push({
          id: `month-${year}-${month}`,
          type: 'month',
          year,
          month,
          monthName: getMonthName(month),
          count: monthData.count,
        });
        
        // Add document items
        monthData.documents.forEach((doc, index) => {
          items.push({
            id: `doc-${year}-${month}-${doc.id}`,
            type: 'document',
            year,
            month,
            document: doc,
          });
        });
      });
    }
  });
  
  return items;
}

/**
 * Toggle year expansion state
 */
export function toggleYearExpansion(
  year: string,
  state: VirtualizationState
): VirtualizationState {
  const newExpandedYears = new Set(state.expandedYears);
  
  if (newExpandedYears.has(year)) {
    newExpandedYears.delete(year);
  } else {
    newExpandedYears.add(year);
  }
  
  return {
    expandedYears: newExpandedYears,
  };
}

/**
 * Initialize virtualization state with all years expanded
 */
export function initializeVirtualizationState(
  timelineData: TimelineData,
  allExpanded: boolean = true
): VirtualizationState {
  const expandedYears = new Set<string>();
  
  if (allExpanded) {
    Object.keys(timelineData.by_year).forEach(year => {
      expandedYears.add(year);
    });
  }
  
  return {
    expandedYears,
  };
}

/**
 * Expand or collapse all years
 */
export function setAllYearsExpanded(
  timelineData: TimelineData,
  expanded: boolean
): VirtualizationState {
  return initializeVirtualizationState(timelineData, expanded);
}
