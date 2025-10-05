import { useEffect, useState } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { 
  getThemeColors, 
  getSubthemeColors, 
  createThemeCardStyles,
  createGlassStyles,
  ColorScheme 
} from '../utils/theme-colors';

/**
 * Hook to get theme-aware colors and styles
 */
export function useThemeColors(themeName: string) {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  const [colors, setColors] = useState<ColorScheme>(() => getThemeColors(themeName, isDark));
  const [cardStyles, setCardStyles] = useState(() => createThemeCardStyles(themeName, isDark));
  const [glassStyles, setGlassStyles] = useState(() => createGlassStyles(themeName, isDark));

  useEffect(() => {
    setColors(getThemeColors(themeName, isDark));
    setCardStyles(createThemeCardStyles(themeName, isDark));
    setGlassStyles(createGlassStyles(themeName, isDark));
  }, [themeName, isDark]);

  return {
    colors,
    cardStyles,
    glassStyles,
    isDark
  };
}

/**
 * Hook to get subtheme-aware colors
 */
export function useSubthemeColors(subthemeName: string) {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  const [colors, setColors] = useState<ColorScheme>(() => getSubthemeColors(subthemeName, isDark));

  useEffect(() => {
    setColors(getSubthemeColors(subthemeName, isDark));
  }, [subthemeName, isDark]);

  return {
    colors,
    isDark
  };
}

/**
 * Hook to apply dynamic theme classes
 */
export function useThemeClasses() {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  return {
    // Glass morphism classes
    glass: isDark 
      ? 'bg-gray-900/20 backdrop-blur-xl border-gray-700/30' 
      : 'bg-white/70 backdrop-blur-xl border-gray-200/50',
    
    glassHover: isDark
      ? 'hover:bg-gray-900/30 hover:border-gray-600/40'
      : 'hover:bg-white/80 hover:border-gray-300/60',
    
    // Card classes
    card: isDark
      ? 'bg-gray-800/50 border-gray-700/50'
      : 'bg-white/90 border-gray-200/70',
    
    cardHover: isDark
      ? 'hover:bg-gray-800/60 hover:border-gray-600/60'
      : 'hover:bg-white/95 hover:border-gray-300/80',
    
    // Text classes
    textPrimary: isDark ? 'text-gray-100' : 'text-gray-900',
    textSecondary: isDark ? 'text-gray-300' : 'text-gray-700',
    textMuted: isDark ? 'text-gray-400' : 'text-gray-600',
    
    // Status classes
    success: isDark ? 'text-green-400' : 'text-green-600',
    warning: isDark ? 'text-yellow-400' : 'text-yellow-600',
    error: isDark ? 'text-red-400' : 'text-red-600',
    info: isDark ? 'text-blue-400' : 'text-blue-600',
  };
}