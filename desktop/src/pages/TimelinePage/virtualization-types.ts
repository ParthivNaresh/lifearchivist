/**
 * Types for virtualized timeline
 */

import { type TimelineDocument } from './types';

export type VirtualItemType = 'year' | 'month' | 'document';

export interface BaseVirtualItem {
  id: string;
  type: VirtualItemType;
}

export interface YearVirtualItem extends BaseVirtualItem {
  type: 'year';
  year: string;
  count: number;
  isExpanded: boolean;
}

export interface MonthVirtualItem extends BaseVirtualItem {
  type: 'month';
  year: string;
  month: string;
  monthName: string;
  count: number;
}

export interface DocumentVirtualItem extends BaseVirtualItem {
  type: 'document';
  year: string;
  month: string;
  document: TimelineDocument;
}

export type VirtualItem = YearVirtualItem | MonthVirtualItem | DocumentVirtualItem;

export interface VirtualizationState {
  expandedYears: Set<string>;
}
