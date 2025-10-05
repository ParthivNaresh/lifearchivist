/**
 * Constants and configuration for VaultPage
 */

import React from 'react';
import {
  DollarSign,
  Heart,
  Scale,
  Briefcase,
  User,
  Folder,
  Loader2,
  Landmark,
  Calculator,
  TrendingUp,
  Shield,
  HandCoins,
  Banknote,
  Receipt,
  Building2,
  CreditCard,
  FileText,
  FileBarChart,
  PiggyBank,
  ScrollText,
  FileCheck,
  Home,
  Users,
  Gavel,
  FileSignature,
  UserCheck,
  Building,
  AlertCircle,
  FileX,
  Handshake,
  Mail
} from 'lucide-react';
import { ThemeConfig, CategoryConfig } from './types';

// Cache durations
export const CACHE_DURATIONS = {
  VAULT_INFO: 30 * 1000,        // 30 seconds
  DOCUMENTS: 5 * 60 * 1000,     // 5 minutes
  POLLING_INTERVAL: 5000,       // 5 seconds for processing documents
} as const;

// Theme order for sorting
export const THEME_ORDER = [
  'Financial',
  'Healthcare',
  'Legal',
  'Professional',
  'Personal',
  'Unclassified',
  'Processing'
] as const;

// Map of subclassifications to their parent subtheme categories
export const SUBTHEME_CATEGORIES: Record<string, string> = {
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
  
  // Legal > Contracts and Agreements
  'Lease Agreement': 'Contracts and Agreements',
  'Employment Agreement': 'Contracts and Agreements',
  'Service Contract': 'Contracts and Agreements',
  'Purchase Agreement': 'Contracts and Agreements',
  'NDA': 'Contracts and Agreements',
  
  // Legal > Estate and Family
  'Will': 'Estate and Family',
  'Power of Attorney': 'Estate and Family',
  'Trust Document': 'Estate and Family',
  'Divorce Document': 'Estate and Family',
  'Marriage Certificate': 'Estate and Family',
  
  // Legal > Property and Real Estate
  'Property Deed': 'Property and Real Estate',
  'Mortgage Document': 'Property and Real Estate',
  'Title Document': 'Property and Real Estate',
  'HOA Document': 'Property and Real Estate',
  'Property Transfer': 'Property and Real Estate',
  
  // Legal > Court and Legal Proceedings
  'Court Order': 'Court and Legal Proceedings',
  'Legal Notice': 'Court and Legal Proceedings',
  'Court Filing': 'Court and Legal Proceedings',
  'Settlement Agreement': 'Court and Legal Proceedings',
  'Legal Correspondence': 'Court and Legal Proceedings',
};

// Subtheme (category) configuration with icons only
// Colors are managed by the centralized theme-colors.ts
export const SUBTHEME_CATEGORY_CONFIG: Record<string, CategoryConfig> = {
  // Financial Categories
  'Banking': {
    icon: <Landmark className="h-5 w-5" />,
    description: 'Bank accounts and credit cards'
  },
  'Tax': {
    icon: <Calculator className="h-5 w-5" />,
    description: 'Tax forms and returns'
  },
  'Investment': {
    icon: <TrendingUp className="h-5 w-5" />,
    description: 'Investment and retirement accounts'
  },
  'Insurance': {
    icon: <Shield className="h-5 w-5" />,
    description: 'Insurance policies and claims'
  },
  'Loan': {
    icon: <HandCoins className="h-5 w-5" />,
    description: 'Loans and mortgages'
  },
  'Income': {
    icon: <Banknote className="h-5 w-5" />,
    description: 'Income and earnings'
  },
  'Transaction': {
    icon: <Receipt className="h-5 w-5" />,
    description: 'Invoices and receipts'
  },
  // Legal Categories
  'Contracts and Agreements': {
    icon: <FileSignature className="h-5 w-5" />,
    description: 'Legal contracts and agreements'
  },
  'Estate and Family': {
    icon: <Users className="h-5 w-5" />,
    description: 'Estate planning and family documents'
  },
  'Property and Real Estate': {
    icon: <Home className="h-5 w-5" />,
    description: 'Property and real estate documents'
  },
  'Court and Legal Proceedings': {
    icon: <Gavel className="h-5 w-5" />,
    description: 'Court documents and legal proceedings'
  },
  'Other': {
    icon: <Folder className="h-5 w-5" />,
    description: 'Other documents'
  },
  'default': {
    icon: <Folder className="h-5 w-5" />,
    description: 'Other documents'
  }
};

// Subclassification configuration with icons only
// Colors are managed by the centralized theme-colors.ts
export const SUBCLASSIFICATION_CONFIG: Record<string, CategoryConfig> = {
  // Financial Subthemes
  'Bank Statement': {
    icon: <Landmark className="h-5 w-5" />,
    description: 'Monthly bank account statements'
  },
  'Credit Card Statement': {
    icon: <CreditCard className="h-5 w-5" />,
    description: 'Credit card bills and statements'
  },
  'W-2 Form': {
    icon: <FileText className="h-5 w-5" />,
    description: 'Annual wage and tax statements'
  },
  '1099 Form': {
    icon: <FileBarChart className="h-5 w-5" />,
    description: 'Independent contractor income'
  },
  'Tax Return': {
    icon: <Calculator className="h-5 w-5" />,
    description: 'Filed tax returns'
  },
  'Brokerage Statement': {
    icon: <TrendingUp className="h-5 w-5" />,
    description: 'Investment account statements'
  },
  '401(k) Statement': {
    icon: <PiggyBank className="h-5 w-5" />,
    description: 'Retirement account statements'
  },
  'Insurance Policy': {
    icon: <Shield className="h-5 w-5" />,
    description: 'Insurance policy documents'
  },
  'Mortgage Statement': {
    icon: <Building2 className="h-5 w-5" />,
    description: 'Home loan statements'
  },
  'Pay Stub': {
    icon: <Banknote className="h-5 w-5" />,
    description: 'Paycheck stubs'
  },
  'Invoice': {
    icon: <ScrollText className="h-5 w-5" />,
    description: 'Bills and invoices'
  },
  'Receipt': {
    icon: <Receipt className="h-5 w-5" />,
    description: 'Purchase receipts'
  },
  'Loan Agreement': {
    icon: <HandCoins className="h-5 w-5" />,
    description: 'Loan contracts and agreements'
  },
  // Legal Subclassifications
  'Lease Agreement': {
    icon: <Home className="h-5 w-5" />,
    description: 'Rental and lease agreements'
  },
  'Employment Agreement': {
    icon: <Briefcase className="h-5 w-5" />,
    description: 'Employment contracts'
  },
  'Service Contract': {
    icon: <FileSignature className="h-5 w-5" />,
    description: 'Service agreements'
  },
  'Purchase Agreement': {
    icon: <Receipt className="h-5 w-5" />,
    description: 'Purchase and sale agreements'
  },
  'NDA': {
    icon: <Shield className="h-5 w-5" />,
    description: 'Non-disclosure agreements'
  },
  'Will': {
    icon: <ScrollText className="h-5 w-5" />,
    description: 'Last will and testament'
  },
  'Power of Attorney': {
    icon: <UserCheck className="h-5 w-5" />,
    description: 'Power of attorney documents'
  },
  'Trust Document': {
    icon: <Shield className="h-5 w-5" />,
    description: 'Trust agreements'
  },
  'Divorce Document': {
    icon: <FileX className="h-5 w-5" />,
    description: 'Divorce decrees and agreements'
  },
  'Marriage Certificate': {
    icon: <Users className="h-5 w-5" />,
    description: 'Marriage certificates'
  },
  'Property Deed': {
    icon: <Building className="h-5 w-5" />,
    description: 'Property deeds and titles'
  },
  'Mortgage Document': {
    icon: <Building2 className="h-5 w-5" />,
    description: 'Mortgage agreements'
  },
  'Title Document': {
    icon: <FileText className="h-5 w-5" />,
    description: 'Title documents'
  },
  'HOA Document': {
    icon: <Home className="h-5 w-5" />,
    description: 'HOA agreements and bylaws'
  },
  'Property Transfer': {
    icon: <Building className="h-5 w-5" />,
    description: 'Property transfer documents'
  },
  'Court Order': {
    icon: <Gavel className="h-5 w-5" />,
    description: 'Court orders and judgments'
  },
  'Legal Notice': {
    icon: <AlertCircle className="h-5 w-5" />,
    description: 'Legal notices and summons'
  },
  'Court Filing': {
    icon: <FileText className="h-5 w-5" />,
    description: 'Court filings and motions'
  },
  'Settlement Agreement': {
    icon: <Handshake className="h-5 w-5" />,
    description: 'Settlement agreements'
  },
  'Legal Correspondence': {
    icon: <Mail className="h-5 w-5" />,
    description: 'Legal letters and correspondence'
  },
  // Default fallback
  'default': {
    icon: <Folder className="h-5 w-5" />,
    description: 'Document subcategory'
  }
};

// Theme configuration with icons only
// Colors and gradients are managed by the centralized theme-colors.ts
export const THEME_CONFIG: Record<string, ThemeConfig> = {
  'Financial': {
    icon: <DollarSign className="h-8 w-8" />,
    description: 'Financial documents, statements, and transactions'
  },
  'Healthcare': {
    icon: <Heart className="h-8 w-8" />,
    description: 'Medical records, prescriptions, and health documents'
  },
  'Legal': {
    icon: <Scale className="h-8 w-8" />,
    description: 'Legal agreements, contracts, and court documents'
  },
  'Professional': {
    icon: <Briefcase className="h-8 w-8" />,
    description: 'Career and education documents'
  },
  'Personal': {
    icon: <User className="h-8 w-8" />,
    description: 'Personal documents and government IDs'
  },
  'Unclassified': {
    icon: <Folder className="h-8 w-8" />,
    description: 'Documents without theme classification'
  },
  'Processing': {
    icon: <Loader2 className="h-8 w-8 animate-spin" />,
    description: 'Documents being processed'
  }
};

// UI Text constants
export const UI_TEXT = {
  PAGE_TITLE: 'Document Vault',
  PAGE_SUBTITLE: 'Browse your documents organized by theme',
  BREADCRUMB_HOME: 'All Documents',
  LOADING: 'Loading documents...',
  NO_DOCUMENTS: 'No documents in vault',
  NO_DOCUMENTS_SUBTITLE: 'Upload some documents to get started',
  NO_MATCHES: 'No matches found',
  NO_MATCHES_SUBTITLE: 'Try a different search term',
  SEARCH_PLACEHOLDER: 'Search in current folder...',
  CLEAR_VAULT_CONFIRM: 'Are you sure you want to clear the entire vault? This will permanently delete all files and their associated document records. This cannot be undone.',
  GRID_VIEW: 'Grid view',
  LIST_VIEW: 'List view',
  REFRESH: 'Refresh',
  CLEAR_VAULT: 'Clear vault',
  VIEW_DETAILS: 'View details',
} as const;