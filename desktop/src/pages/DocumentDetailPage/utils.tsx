import React from 'react';
import { FileText } from 'lucide-react';

/**
 * Format bytes into human-readable file size
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * Format date string into relative time or locale string
 */
export const formatDate = (dateString: string): string => {
  if (!dateString) return 'Unknown';
  const date = new Date(dateString);
  const now = new Date();
  const diffTime = Math.abs(now.getTime() - date.getTime());
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
  
  return date.toLocaleDateString();
};

/**
 * Get appropriate icon component based on MIME type
 */
export const getFileIcon = (mimeType: string): React.ReactNode => {
  if (!mimeType) return <FileText className="h-5 w-5" />;
  
  if (mimeType.includes('pdf')) return <FileText className="h-5 w-5 text-red-600" />;
  if (mimeType.includes('word')) return <FileText className="h-5 w-5 text-blue-600" />;
  if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return <FileText className="h-5 w-5 text-green-600" />;
  if (mimeType.includes('image')) return <FileText className="h-5 w-5 text-purple-600" />;
  if (mimeType.includes('text')) return <FileText className="h-5 w-5 text-gray-600" />;
  
  return <FileText className="h-5 w-5" />;
};

/**
 * Get human-readable file type name from MIME type
 */
export const getFileTypeName = (mimeType: string): string => {
  if (!mimeType) return 'Unknown';
  
  if (mimeType.includes('pdf')) return 'PDF Document';
  if (mimeType.includes('word')) return 'Word Document';
  if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return 'Spreadsheet';
  if (mimeType.includes('image')) return 'Image';
  if (mimeType.includes('text/plain')) return 'Text File';
  if (mimeType.includes('text')) return 'Text Document';
  
  return mimeType.split('/')[1]?.toUpperCase() || 'File';
};

/**
 * Check if a file type will download when clicked (can't be displayed inline)
 */
export const willFileDownload = (mimeType: string): boolean => {
  return mimeType.includes('word') || 
         mimeType.includes('excel') || 
         mimeType.includes('spreadsheet') ||
         mimeType.includes('rtf');
};

/**
 * Get the subtheme category for a subclassification
 */
export const getSubthemeCategory = (subclassification: string): string => {
  const SUBTHEME_CATEGORIES: Record<string, string> = {
    // Financial > Banking
    'Bank Statement': 'Banking',
    'Credit Card Statement': 'Banking',
    
    // Financial > Tax Documents
    'W-2 Form': 'Tax',
    '1099 Form': 'Tax',
    'Tax Return': 'Tax',
    
    // Financial > Investment
    'Brokerage Statement': 'Investment',
    '401(k) Statement': 'Investment',
    'IRA Statement': 'Investment',
    'Trade Confirmation': 'Investment',
    'Investment Prospectus': 'Investment',
    
    // Financial > Insurance
    'Insurance Policy': 'Insurance',
    'Insurance Claim': 'Insurance',
    'Explanation of Benefits': 'Insurance',
    
    // Financial > Loan
    'Mortgage Statement': 'Loan',
    'Loan Agreement': 'Loan',
    'Student Loan': 'Loan',
    'Auto Loan': 'Loan',
    'Personal Loan': 'Loan',
    
    // Financial > Income
    'Pay Stub': 'Income',
    
    // Financial > Transaction
    'Invoice': 'Transaction',
    'Receipt': 'Transaction',
    'Purchase Order': 'Transaction',
    'Bill': 'Transaction',
  };
  
  return SUBTHEME_CATEGORIES[subclassification] || 'Other';
};