/**
 * Theme color configuration for timeline visualization
 */

export interface ThemeColors {
  bg: string;
  bgHover: string;
  border: string;
  borderHover: string;
  accent: string;
  text: string;
  badge: string;
  icon: string;
}

export const THEME_COLORS: Record<string, ThemeColors> = {
  Financial: {
    bg: 'bg-emerald-50/50 dark:bg-emerald-950/20',
    bgHover: 'hover:bg-emerald-100/70 dark:hover:bg-emerald-950/40',
    border: 'border-emerald-200 dark:border-emerald-800/50',
    borderHover: 'hover:border-emerald-400 dark:hover:border-emerald-600',
    accent: 'bg-emerald-500',
    text: 'text-emerald-700 dark:text-emerald-300',
    badge: 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300',
    icon: '💰',
  },
  Legal: {
    bg: 'bg-blue-50/50 dark:bg-blue-950/20',
    bgHover: 'hover:bg-blue-100/70 dark:hover:bg-blue-950/40',
    border: 'border-blue-200 dark:border-blue-800/50',
    borderHover: 'hover:border-blue-400 dark:hover:border-blue-600',
    accent: 'bg-blue-500',
    text: 'text-blue-700 dark:text-blue-300',
    badge: 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300',
    icon: '⚖️',
  },
  Healthcare: {
    bg: 'bg-red-50/50 dark:bg-red-950/20',
    bgHover: 'hover:bg-red-100/70 dark:hover:bg-red-950/40',
    border: 'border-red-200 dark:border-red-800/50',
    borderHover: 'hover:border-red-400 dark:hover:border-red-600',
    accent: 'bg-red-500',
    text: 'text-red-700 dark:text-red-300',
    badge: 'bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300',
    icon: '🏥',
  },
  Personal: {
    bg: 'bg-purple-50/50 dark:bg-purple-950/20',
    bgHover: 'hover:bg-purple-100/70 dark:hover:bg-purple-950/40',
    border: 'border-purple-200 dark:border-purple-800/50',
    borderHover: 'hover:border-purple-400 dark:hover:border-purple-600',
    accent: 'bg-purple-500',
    text: 'text-purple-700 dark:text-purple-300',
    badge: 'bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300',
    icon: '👤',
  },
  Education: {
    bg: 'bg-amber-50/50 dark:bg-amber-950/20',
    bgHover: 'hover:bg-amber-100/70 dark:hover:bg-amber-950/40',
    border: 'border-amber-200 dark:border-amber-800/50',
    borderHover: 'hover:border-amber-400 dark:hover:border-amber-600',
    accent: 'bg-amber-500',
    text: 'text-amber-700 dark:text-amber-300',
    badge: 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300',
    icon: '🎓',
  },
  Travel: {
    bg: 'bg-cyan-50/50 dark:bg-cyan-950/20',
    bgHover: 'hover:bg-cyan-100/70 dark:hover:bg-cyan-950/40',
    border: 'border-cyan-200 dark:border-cyan-800/50',
    borderHover: 'hover:border-cyan-400 dark:hover:border-cyan-600',
    accent: 'bg-cyan-500',
    text: 'text-cyan-700 dark:text-cyan-300',
    badge: 'bg-cyan-100 dark:bg-cyan-900/50 text-cyan-700 dark:text-cyan-300',
    icon: '✈️',
  },
  Unclassified: {
    bg: 'bg-gray-50/50 dark:bg-gray-900/20',
    bgHover: 'hover:bg-gray-100/70 dark:hover:bg-gray-900/40',
    border: 'border-gray-200 dark:border-gray-700/50',
    borderHover: 'hover:border-gray-400 dark:hover:border-gray-600',
    accent: 'bg-gray-500',
    text: 'text-gray-700 dark:text-gray-300',
    badge: 'bg-gray-100 dark:bg-gray-800/50 text-gray-700 dark:text-gray-300',
    icon: '📄',
  },
};

/**
 * Get theme colors for a given theme name
 */
export function getThemeColors(theme: string | null | undefined): ThemeColors {
  if (!theme || !THEME_COLORS[theme]) {
    return THEME_COLORS.Unclassified;
  }
  return THEME_COLORS[theme];
}

/**
 * Get the dominant theme from a list of documents
 */
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

/**
 * Get theme distribution for a list of documents
 */
export function getThemeDistribution(documents: Array<{ theme: string | null }>): Record<string, number> {
  const distribution: Record<string, number> = {};
  
  documents.forEach(doc => {
    const theme = doc.theme || 'Unclassified';
    distribution[theme] = (distribution[theme] || 0) + 1;
  });
  
  return distribution;
}
