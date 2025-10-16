import React from 'react';
import { ChevronRight, Loader2 } from 'lucide-react';
import { useThemeColors } from '../../../hooks/useThemeColors';
import { cn } from '../../../utils/cn';

interface ThemeCardProps {
  themeName: string;
  displayName: string;
  icon: React.ReactNode;
  description: string;
  itemCount: number;
  processingCount?: number;
  size: number;
  onClick: () => void;
  className?: string;
}

export const ThemeCard: React.FC<ThemeCardProps> = ({
  themeName,
  displayName,
  icon,
  description,
  itemCount,
  processingCount,
  size,
  onClick,
  className
}) => {
  const { cardStyles, colors, isDark } = useThemeColors(themeName);
  
  const formatFileSize = (bytes: number): string => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div
      className={cn(
        "group relative rounded-xl p-6 cursor-pointer transition-all duration-300",
        "hover:scale-[1.02] hover:shadow-xl",
        className
      )}
      style={{
        ...cardStyles,
        boxShadow: isDark 
          ? '0 4px 20px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05)'
          : '0 4px 20px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.8)'
      }}
      onClick={onClick}
      onMouseEnter={(e) => {
        if (colors.borderHover) {
          e.currentTarget.style.borderColor = colors.borderHover;
        }
        if (colors.backgroundHover) {
          const gradient = colors.gradient;
          if (gradient) {
            e.currentTarget.style.background = `linear-gradient(135deg, ${gradient.from} 0%, ${gradient.via || gradient.to} 50%, ${gradient.to} 100%)`;
          } else {
            e.currentTarget.style.backgroundColor = colors.backgroundHover;
          }
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = colors.border;
        if (colors.gradient) {
          e.currentTarget.style.background = `linear-gradient(135deg, ${colors.gradient.from} 0%, ${colors.gradient.via || colors.gradient.to} 50%, ${colors.gradient.to} 100%)`;
        } else {
          e.currentTarget.style.backgroundColor = colors.background;
        }
      }}
    >
      {/* Glass overlay for depth */}
      <div 
        className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
        style={{
          background: isDark 
            ? 'radial-gradient(circle at 50% 0%, rgba(255, 255, 255, 0.05), transparent 70%)'
            : 'radial-gradient(circle at 50% 0%, rgba(255, 255, 255, 0.4), transparent 70%)'
        }}
      />
      
      {/* Content */}
      <div className="relative z-10">
        {/* Top section with icon and count */}
        <div className="flex items-start justify-between mb-4">
          <div 
            className="p-3 rounded-lg transition-all duration-200 group-hover:scale-110"
            style={{
              backgroundColor: isDark ? 'rgba(0, 0, 0, 0.2)' : 'rgba(255, 255, 255, 0.8)',
              backdropFilter: 'blur(8px)',
              boxShadow: isDark 
                ? 'inset 0 1px 0 rgba(255, 255, 255, 0.05), 0 2px 8px rgba(0, 0, 0, 0.3)'
                : 'inset 0 1px 0 rgba(255, 255, 255, 0.9), 0 2px 8px rgba(0, 0, 0, 0.05)'
            }}
          >
            <div style={{ color: colors.icon }}>
              {icon}
            </div>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold" style={{ color: colors.text }}>
              {itemCount}
            </p>
            <p className="text-xs" style={{ color: colors.textMuted }}>
              {itemCount === 1 ? 'document' : 'documents'}
            </p>
            {processingCount && processingCount > 0 && (
              <div className="flex items-center justify-end mt-1 space-x-1">
                <Loader2 className="h-3 w-3 animate-spin" style={{ color: colors.icon }} />
                <p className="text-xs" style={{ color: colors.icon }}>
                  {processingCount} processing
                </p>
              </div>
            )}
          </div>
        </div>
        
        {/* Theme name */}
        <h3 className="font-semibold text-base mb-1" style={{ color: colors.text }}>
          {displayName}
        </h3>
        
        {/* Description */}
        <p className="text-xs mb-3 line-clamp-2" style={{ color: colors.textMuted }}>
          {description}
        </p>
        
        {/* Bottom metadata */}
        <div className="flex items-center justify-between">
          <span className="text-xs" style={{ color: colors.textMuted }}>
            {formatFileSize(size)}
          </span>
          <ChevronRight 
            className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-all duration-300 group-hover:translate-x-1" 
            style={{ color: colors.icon }}
          />
        </div>
      </div>
      
      {/* Bottom accent line */}
      <div 
        className="absolute bottom-0 left-0 right-0 h-0.5 rounded-b-xl opacity-30"
        style={{
          background: `linear-gradient(90deg, transparent, ${colors.icon}, transparent)`
        }}
      />
    </div>
  );
};