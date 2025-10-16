/**
 * Utility functions for QAPage
 */

import { CONFIDENCE_THRESHOLDS, METHOD_DESCRIPTIONS } from './constants';

/**
 * Format confidence score as percentage
 */
export const formatConfidence = (confidence: number): string => {
  return `${Math.round(confidence * 100)}%`;
};

/**
 * Get color class based on confidence level
 */
export const getConfidenceColor = (confidence: number): string => {
  if (confidence >= CONFIDENCE_THRESHOLDS.HIGH) {
    return 'text-green-600 dark:text-green-400';
  }
  if (confidence >= CONFIDENCE_THRESHOLDS.MEDIUM) {
    return 'text-yellow-600 dark:text-yellow-400';
  }
  return 'text-red-600 dark:text-red-400';
};

/**
 * Get human-readable description for method
 */
export const getMethodDescription = (method?: string): string => {
  if (!method) return METHOD_DESCRIPTIONS.default;
  return METHOD_DESCRIPTIONS[method] || METHOD_DESCRIPTIONS.default;
};

/**
 * Generate unique message ID
 */
export const generateMessageId = (): string => {
  return Date.now().toString();
};

/**
 * Format timestamp for display
 */
export const formatTimestamp = (date: Date): string => {
  return date.toLocaleTimeString();
};

/**
 * Calculate relevance score percentage
 */
export const formatRelevanceScore = (score?: number): string => {
  if (!score) return '';
  return `${Math.round(score * 100)}%`;
};