/**
 * Centralized theme color management system
 * Provides consistent color values for light and dark modes
 */

export interface ColorScheme {
  background: string;
  backgroundHover?: string;
  border: string;
  borderHover?: string;
  text: string;
  textMuted: string;
  icon: string;
  gradient?: {
    from: string;
    to: string;
    via?: string;
  };
  glass?: {
    background: string;
    backdropBlur: string;
    border: string;
  };
}

export interface ThemeColors {
  light: ColorScheme;
  dark: ColorScheme;
}

// Main theme colors for document categories
export const THEME_COLORS: Record<string, ThemeColors> = {
  Financial: {
    light: {
      background: 'rgba(240, 253, 244, 0.8)', // Very light green with transparency
      backgroundHover: 'rgba(220, 252, 231, 0.9)',
      border: 'rgba(134, 239, 172, 0.5)', // green-300 with transparency
      borderHover: 'rgba(74, 222, 128, 0.7)',
      text: 'rgb(22, 101, 52)', // green-800
      textMuted: 'rgb(21, 128, 61)', // green-700
      icon: 'rgb(34, 197, 94)', // green-500
      gradient: {
        from: 'rgba(240, 253, 244, 0.9)',
        to: 'rgba(220, 252, 231, 0.9)',
        via: 'rgba(187, 247, 208, 0.5)',
      },
      glass: {
        background: 'rgba(255, 255, 255, 0.7)',
        backdropBlur: 'blur(12px)',
        border: 'rgba(134, 239, 172, 0.3)',
      },
    },
    dark: {
      background: 'rgba(5, 46, 22, 0.4)', // green-950 with transparency
      backgroundHover: 'rgba(5, 46, 22, 0.6)',
      border: 'rgba(34, 197, 94, 0.3)', // green-500 with transparency
      borderHover: 'rgba(34, 197, 94, 0.5)',
      text: 'rgb(187, 247, 208)', // green-200
      textMuted: 'rgb(134, 239, 172)', // green-300
      icon: 'rgb(74, 222, 128)', // green-400
      gradient: {
        from: 'rgba(5, 46, 22, 0.5)',
        to: 'rgba(20, 83, 45, 0.5)',
        via: 'rgba(22, 101, 52, 0.3)',
      },
      glass: {
        background: 'rgba(5, 46, 22, 0.3)',
        backdropBlur: 'blur(16px)',
        border: 'rgba(34, 197, 94, 0.2)',
      },
    },
  },
  Healthcare: {
    light: {
      background: 'rgba(254, 242, 242, 0.8)', // Very light red
      backgroundHover: 'rgba(254, 226, 226, 0.9)',
      border: 'rgba(252, 165, 165, 0.5)', // red-300
      borderHover: 'rgba(248, 113, 113, 0.7)',
      text: 'rgb(153, 27, 27)', // red-800
      textMuted: 'rgb(185, 28, 28)', // red-700
      icon: 'rgb(239, 68, 68)', // red-500
      gradient: {
        from: 'rgba(254, 242, 242, 0.9)',
        to: 'rgba(254, 226, 226, 0.9)',
        via: 'rgba(254, 202, 202, 0.5)',
      },
      glass: {
        background: 'rgba(255, 255, 255, 0.7)',
        backdropBlur: 'blur(12px)',
        border: 'rgba(252, 165, 165, 0.3)',
      },
    },
    dark: {
      background: 'rgba(69, 10, 10, 0.4)', // red-950
      backgroundHover: 'rgba(69, 10, 10, 0.6)',
      border: 'rgba(239, 68, 68, 0.3)', // red-500
      borderHover: 'rgba(239, 68, 68, 0.5)',
      text: 'rgb(254, 202, 202)', // red-200
      textMuted: 'rgb(252, 165, 165)', // red-300
      icon: 'rgb(248, 113, 113)', // red-400
      gradient: {
        from: 'rgba(69, 10, 10, 0.5)',
        to: 'rgba(127, 29, 29, 0.5)',
        via: 'rgba(153, 27, 27, 0.3)',
      },
      glass: {
        background: 'rgba(69, 10, 10, 0.3)',
        backdropBlur: 'blur(16px)',
        border: 'rgba(239, 68, 68, 0.2)',
      },
    },
  },
  Legal: {
    light: {
      background: 'rgba(239, 246, 255, 0.8)', // Very light blue
      backgroundHover: 'rgba(219, 234, 254, 0.9)',
      border: 'rgba(147, 197, 253, 0.5)', // blue-300
      borderHover: 'rgba(96, 165, 250, 0.7)',
      text: 'rgb(30, 58, 138)', // blue-800
      textMuted: 'rgb(29, 78, 216)', // blue-700
      icon: 'rgb(59, 130, 246)', // blue-500
      gradient: {
        from: 'rgba(239, 246, 255, 0.9)',
        to: 'rgba(219, 234, 254, 0.9)',
        via: 'rgba(191, 219, 254, 0.5)',
      },
      glass: {
        background: 'rgba(255, 255, 255, 0.7)',
        backdropBlur: 'blur(12px)',
        border: 'rgba(147, 197, 253, 0.3)',
      },
    },
    dark: {
      background: 'rgba(23, 37, 84, 0.4)', // blue-950
      backgroundHover: 'rgba(23, 37, 84, 0.6)',
      border: 'rgba(59, 130, 246, 0.3)', // blue-500
      borderHover: 'rgba(59, 130, 246, 0.5)',
      text: 'rgb(191, 219, 254)', // blue-200
      textMuted: 'rgb(147, 197, 253)', // blue-300
      icon: 'rgb(96, 165, 250)', // blue-400
      gradient: {
        from: 'rgba(23, 37, 84, 0.5)',
        to: 'rgba(30, 64, 175, 0.5)',
        via: 'rgba(30, 58, 138, 0.3)',
      },
      glass: {
        background: 'rgba(23, 37, 84, 0.3)',
        backdropBlur: 'blur(16px)',
        border: 'rgba(59, 130, 246, 0.2)',
      },
    },
  },
  Professional: {
    light: {
      background: 'rgba(250, 245, 255, 0.8)', // Very light purple
      backgroundHover: 'rgba(243, 232, 255, 0.9)',
      border: 'rgba(196, 181, 253, 0.5)', // purple-300
      borderHover: 'rgba(167, 139, 250, 0.7)',
      text: 'rgb(88, 28, 135)', // purple-800
      textMuted: 'rgb(107, 33, 168)', // purple-700
      icon: 'rgb(168, 85, 247)', // purple-500
      gradient: {
        from: 'rgba(250, 245, 255, 0.9)',
        to: 'rgba(243, 232, 255, 0.9)',
        via: 'rgba(233, 213, 255, 0.5)',
      },
      glass: {
        background: 'rgba(255, 255, 255, 0.7)',
        backdropBlur: 'blur(12px)',
        border: 'rgba(196, 181, 253, 0.3)',
      },
    },
    dark: {
      background: 'rgba(59, 7, 100, 0.4)', // purple-950
      backgroundHover: 'rgba(59, 7, 100, 0.6)',
      border: 'rgba(168, 85, 247, 0.3)', // purple-500
      borderHover: 'rgba(168, 85, 247, 0.5)',
      text: 'rgb(233, 213, 255)', // purple-200
      textMuted: 'rgb(196, 181, 253)', // purple-300
      icon: 'rgb(167, 139, 250)', // purple-400
      gradient: {
        from: 'rgba(59, 7, 100, 0.5)',
        to: 'rgba(88, 28, 135, 0.5)',
        via: 'rgba(107, 33, 168, 0.3)',
      },
      glass: {
        background: 'rgba(59, 7, 100, 0.3)',
        backdropBlur: 'blur(16px)',
        border: 'rgba(168, 85, 247, 0.2)',
      },
    },
  },
  Personal: {
    light: {
      background: 'rgba(255, 247, 237, 0.8)', // Very light orange
      backgroundHover: 'rgba(254, 237, 213, 0.9)',
      border: 'rgba(253, 186, 116, 0.5)', // orange-300
      borderHover: 'rgba(251, 146, 60, 0.7)',
      text: 'rgb(154, 52, 18)', // orange-800
      textMuted: 'rgb(194, 65, 12)', // orange-700
      icon: 'rgb(249, 115, 22)', // orange-500
      gradient: {
        from: 'rgba(255, 247, 237, 0.9)',
        to: 'rgba(254, 237, 213, 0.9)',
        via: 'rgba(254, 215, 170, 0.5)',
      },
      glass: {
        background: 'rgba(255, 255, 255, 0.7)',
        backdropBlur: 'blur(12px)',
        border: 'rgba(253, 186, 116, 0.3)',
      },
    },
    dark: {
      background: 'rgba(67, 20, 7, 0.4)', // orange-950
      backgroundHover: 'rgba(67, 20, 7, 0.6)',
      border: 'rgba(249, 115, 22, 0.3)', // orange-500
      borderHover: 'rgba(249, 115, 22, 0.5)',
      text: 'rgb(254, 215, 170)', // orange-200
      textMuted: 'rgb(253, 186, 116)', // orange-300
      icon: 'rgb(251, 146, 60)', // orange-400
      gradient: {
        from: 'rgba(67, 20, 7, 0.5)',
        to: 'rgba(124, 45, 18, 0.5)',
        via: 'rgba(154, 52, 18, 0.3)',
      },
      glass: {
        background: 'rgba(67, 20, 7, 0.3)',
        backdropBlur: 'blur(16px)',
        border: 'rgba(249, 115, 22, 0.2)',
      },
    },
  },
  Unclassified: {
    light: {
      background: 'rgba(249, 250, 251, 0.8)', // Very light gray
      backgroundHover: 'rgba(243, 244, 246, 0.9)',
      border: 'rgba(209, 213, 219, 0.5)', // gray-300
      borderHover: 'rgba(156, 163, 175, 0.7)',
      text: 'rgb(55, 65, 81)', // gray-700
      textMuted: 'rgb(75, 85, 99)', // gray-600
      icon: 'rgb(107, 114, 128)', // gray-500
      gradient: {
        from: 'rgba(249, 250, 251, 0.9)',
        to: 'rgba(243, 244, 246, 0.9)',
        via: 'rgba(229, 231, 235, 0.5)',
      },
      glass: {
        background: 'rgba(255, 255, 255, 0.7)',
        backdropBlur: 'blur(12px)',
        border: 'rgba(209, 213, 219, 0.3)',
      },
    },
    dark: {
      background: 'rgba(17, 24, 39, 0.4)', // gray-900
      backgroundHover: 'rgba(17, 24, 39, 0.6)',
      border: 'rgba(107, 114, 128, 0.3)', // gray-500
      borderHover: 'rgba(107, 114, 128, 0.5)',
      text: 'rgb(229, 231, 235)', // gray-200
      textMuted: 'rgb(209, 213, 219)', // gray-300
      icon: 'rgb(156, 163, 175)', // gray-400
      gradient: {
        from: 'rgba(17, 24, 39, 0.5)',
        to: 'rgba(31, 41, 55, 0.5)',
        via: 'rgba(55, 65, 81, 0.3)',
      },
      glass: {
        background: 'rgba(17, 24, 39, 0.3)',
        backdropBlur: 'blur(16px)',
        border: 'rgba(107, 114, 128, 0.2)',
      },
    },
  },
  Processing: {
    light: {
      background: 'rgba(254, 249, 235, 0.8)', // Very light yellow
      backgroundHover: 'rgba(254, 243, 199, 0.9)',
      border: 'rgba(253, 224, 71, 0.5)', // yellow-300
      borderHover: 'rgba(250, 204, 21, 0.7)',
      text: 'rgb(146, 64, 14)', // yellow-800
      textMuted: 'rgb(161, 98, 7)', // yellow-700
      icon: 'rgb(234, 179, 8)', // yellow-500
      gradient: {
        from: 'rgba(254, 249, 235, 0.9)',
        to: 'rgba(254, 243, 199, 0.9)',
        via: 'rgba(254, 240, 138, 0.5)',
      },
      glass: {
        background: 'rgba(255, 255, 255, 0.7)',
        backdropBlur: 'blur(12px)',
        border: 'rgba(253, 224, 71, 0.3)',
      },
    },
    dark: {
      background: 'rgba(66, 32, 6, 0.4)', // yellow-950
      backgroundHover: 'rgba(66, 32, 6, 0.6)',
      border: 'rgba(234, 179, 8, 0.3)', // yellow-500
      borderHover: 'rgba(234, 179, 8, 0.5)',
      text: 'rgb(254, 240, 138)', // yellow-200
      textMuted: 'rgb(253, 224, 71)', // yellow-300
      icon: 'rgb(250, 204, 21)', // yellow-400
      gradient: {
        from: 'rgba(66, 32, 6, 0.5)',
        to: 'rgba(113, 63, 18, 0.5)',
        via: 'rgba(146, 64, 14, 0.3)',
      },
      glass: {
        background: 'rgba(66, 32, 6, 0.3)',
        backdropBlur: 'blur(16px)',
        border: 'rgba(234, 179, 8, 0.2)',
      },
    },
  },
};

// Subtheme colors for financial documents
export const SUBTHEME_COLORS: Record<string, ThemeColors> = {
  // Subtheme Categories (folders within themes)
  Banking: {
    light: {
      background: 'rgba(239, 246, 255, 1)',
      border: 'rgba(147, 197, 253, 1)',
      text: 'rgb(30, 58, 138)',
      textMuted: 'rgb(29, 78, 216)',
      icon: '#3b82f6',
    },
    dark: {
      background: 'rgba(59, 130, 246, 0.15)',
      border: 'rgba(59, 130, 246, 0.4)',
      text: 'rgb(191, 219, 254)',
      textMuted: 'rgb(147, 197, 253)',
      icon: '#3b82f6',
    },
  },
  Tax: {
    light: {
      background: 'rgba(250, 245, 255, 1)',
      border: 'rgba(196, 181, 253, 1)',
      text: 'rgb(88, 28, 135)',
      textMuted: 'rgb(107, 33, 168)',
      icon: '#a855f7',
    },
    dark: {
      background: 'rgba(168, 85, 247, 0.15)',
      border: 'rgba(168, 85, 247, 0.4)',
      text: 'rgb(233, 213, 255)',
      textMuted: 'rgb(196, 181, 253)',
      icon: '#a855f7',
    },
  },
  Investment: {
    light: {
      background: 'rgba(240, 253, 244, 1)',
      border: 'rgba(134, 239, 172, 1)',
      text: 'rgb(22, 101, 52)',
      textMuted: 'rgb(21, 128, 61)',
      icon: '#22c55e',
    },
    dark: {
      background: 'rgba(34, 197, 94, 0.15)',
      border: 'rgba(34, 197, 94, 0.4)',
      text: 'rgb(187, 247, 208)',
      textMuted: 'rgb(134, 239, 172)',
      icon: '#22c55e',
    },
  },
  Insurance: {
    light: {
      background: 'rgba(236, 254, 255, 1)',
      border: 'rgba(103, 232, 249, 1)',
      text: 'rgb(21, 94, 117)',
      textMuted: 'rgb(14, 116, 144)',
      icon: '#06b6d4',
    },
    dark: {
      background: 'rgba(6, 182, 212, 0.15)',
      border: 'rgba(6, 182, 212, 0.4)',
      text: 'rgb(165, 243, 252)',
      textMuted: 'rgb(103, 232, 249)',
      icon: '#06b6d4',
    },
  },
  Loan: {
    light: {
      background: 'rgba(255, 247, 237, 1)',
      border: 'rgba(253, 186, 116, 1)',
      text: 'rgb(154, 52, 18)',
      textMuted: 'rgb(194, 65, 12)',
      icon: '#f97316',
    },
    dark: {
      background: 'rgba(249, 115, 22, 0.15)',
      border: 'rgba(249, 115, 22, 0.4)',
      text: 'rgb(254, 215, 170)',
      textMuted: 'rgb(253, 186, 116)',
      icon: '#f97316',
    },
  },
  Income: {
    light: {
      background: 'rgba(247, 254, 231, 1)',
      border: 'rgba(190, 242, 100, 1)',
      text: 'rgb(63, 98, 18)',
      textMuted: 'rgb(77, 124, 15)',
      icon: '#84cc16',
    },
    dark: {
      background: 'rgba(132, 204, 22, 0.15)',
      border: 'rgba(132, 204, 22, 0.4)',
      text: 'rgb(217, 249, 157)',
      textMuted: 'rgb(190, 242, 100)',
      icon: '#84cc16',
    },
  },
  Transaction: {
    light: {
      background: 'rgba(254, 249, 235, 1)',
      border: 'rgba(252, 211, 77, 1)',
      text: 'rgb(146, 64, 14)',
      textMuted: 'rgb(180, 83, 9)',
      icon: '#f59e0b',
    },
    dark: {
      background: 'rgba(245, 158, 11, 0.15)',
      border: 'rgba(245, 158, 11, 0.4)',
      text: 'rgb(253, 230, 138)',
      textMuted: 'rgb(252, 211, 77)',
      icon: '#f59e0b',
    },
  },
  'Test Results': {
    light: {
      background: 'rgba(254, 242, 242, 1)',
      border: 'rgba(252, 165, 165, 1)',
      text: 'rgb(153, 27, 27)',
      textMuted: 'rgb(185, 28, 28)',
      icon: '#ef4444',
    },
    dark: {
      background: 'rgba(239, 68, 68, 0.15)',
      border: 'rgba(239, 68, 68, 0.4)',
      text: 'rgb(254, 202, 202)',
      textMuted: 'rgb(252, 165, 165)',
      icon: '#ef4444',
    },
  },
  // Legal Subtheme Categories
  'Contracts and Agreements': {
    light: {
      background: 'rgba(239, 246, 255, 1)',
      border: 'rgba(147, 197, 253, 1)',
      text: 'rgb(30, 58, 138)',
      textMuted: 'rgb(29, 78, 216)',
      icon: '#3b82f6',
    },
    dark: {
      background: 'rgba(59, 130, 246, 0.15)',
      border: 'rgba(59, 130, 246, 0.4)',
      text: 'rgb(191, 219, 254)',
      textMuted: 'rgb(147, 197, 253)',
      icon: '#3b82f6',
    },
  },
  'Estate and Family': {
    light: {
      background: 'rgba(250, 245, 255, 1)',
      border: 'rgba(196, 181, 253, 1)',
      text: 'rgb(88, 28, 135)',
      textMuted: 'rgb(107, 33, 168)',
      icon: '#a855f7',
    },
    dark: {
      background: 'rgba(168, 85, 247, 0.15)',
      border: 'rgba(168, 85, 247, 0.4)',
      text: 'rgb(233, 213, 255)',
      textMuted: 'rgb(196, 181, 253)',
      icon: '#a855f7',
    },
  },
  'Property and Real Estate': {
    light: {
      background: 'rgba(240, 253, 244, 1)',
      border: 'rgba(134, 239, 172, 1)',
      text: 'rgb(22, 101, 52)',
      textMuted: 'rgb(21, 128, 61)',
      icon: '#22c55e',
    },
    dark: {
      background: 'rgba(34, 197, 94, 0.15)',
      border: 'rgba(34, 197, 94, 0.4)',
      text: 'rgb(187, 247, 208)',
      textMuted: 'rgb(134, 239, 172)',
      icon: '#22c55e',
    },
  },
  'Court and Legal Proceedings': {
    light: {
      background: 'rgba(254, 249, 235, 1)',
      border: 'rgba(253, 224, 71, 1)',
      text: 'rgb(146, 64, 14)',
      textMuted: 'rgb(161, 98, 7)',
      icon: '#eab308',
    },
    dark: {
      background: 'rgba(234, 179, 8, 0.15)',
      border: 'rgba(234, 179, 8, 0.4)',
      text: 'rgb(254, 240, 138)',
      textMuted: 'rgb(253, 224, 71)',
      icon: '#eab308',
    },
  },
  Other: {
    light: {
      background: 'rgba(249, 250, 251, 1)',
      border: 'rgba(209, 213, 219, 1)',
      text: 'rgb(55, 65, 81)',
      textMuted: 'rgb(75, 85, 99)',
      icon: '#6b7280',
    },
    dark: {
      background: 'rgba(107, 114, 128, 0.15)',
      border: 'rgba(107, 114, 128, 0.4)',
      text: 'rgb(229, 231, 235)',
      textMuted: 'rgb(209, 213, 219)',
      icon: '#6b7280',
    },
  },
  // Individual document types (subclassifications)
  'Bank Statement': {
    light: {
      background: 'rgba(236, 253, 245, 1)',
      border: 'rgba(167, 243, 208, 1)',
      text: 'rgb(6, 78, 59)',
      textMuted: 'rgb(4, 120, 87)',
      icon: '#10b981',
    },
    dark: {
      background: 'rgba(16, 185, 129, 0.15)',
      border: 'rgba(16, 185, 129, 0.4)',
      text: 'rgb(167, 243, 208)',
      textMuted: 'rgb(110, 231, 183)',
      icon: '#10b981',
    },
  },
  'Credit Card Statement': {
    light: {
      background: 'rgba(239, 246, 255, 1)',
      border: 'rgba(191, 219, 254, 1)',
      text: 'rgb(30, 58, 138)',
      textMuted: 'rgb(29, 78, 216)',
      icon: '#3b82f6',
    },
    dark: {
      background: 'rgba(59, 130, 246, 0.15)',
      border: 'rgba(59, 130, 246, 0.4)',
      text: 'rgb(191, 219, 254)',
      textMuted: 'rgb(147, 197, 253)',
      icon: '#3b82f6',
    },
  },
  'W-2 Form': {
    light: {
      background: 'rgba(250, 245, 255, 1)',
      border: 'rgba(221, 214, 254, 1)',
      text: 'rgb(88, 28, 135)',
      textMuted: 'rgb(107, 33, 168)',
      icon: '#a855f7',
    },
    dark: {
      background: 'rgba(168, 85, 247, 0.15)',
      border: 'rgba(168, 85, 247, 0.4)',
      text: 'rgb(233, 213, 255)',
      textMuted: 'rgb(196, 181, 253)',
      icon: '#a855f7',
    },
  },
  '1099 Form': {
    light: {
      background: 'rgba(238, 242, 255, 1)',
      border: 'rgba(199, 210, 254, 1)',
      text: 'rgb(67, 56, 202)',
      textMuted: 'rgb(79, 70, 229)',
      icon: '#6366f1',
    },
    dark: {
      background: 'rgba(99, 102, 241, 0.15)',
      border: 'rgba(99, 102, 241, 0.4)',
      text: 'rgb(199, 210, 254)',
      textMuted: 'rgb(165, 180, 252)',
      icon: '#6366f1',
    },
  },
  'Tax Return': {
    light: {
      background: 'rgba(254, 242, 242, 1)',
      border: 'rgba(254, 202, 202, 1)',
      text: 'rgb(153, 27, 27)',
      textMuted: 'rgb(185, 28, 28)',
      icon: '#ef4444',
    },
    dark: {
      background: 'rgba(239, 68, 68, 0.15)',
      border: 'rgba(239, 68, 68, 0.4)',
      text: 'rgb(254, 202, 202)',
      textMuted: 'rgb(252, 165, 165)',
      icon: '#ef4444',
    },
  },
  'Brokerage Statement': {
    light: {
      background: 'rgba(240, 253, 244, 1)',
      border: 'rgba(187, 247, 208, 1)',
      text: 'rgb(22, 101, 52)',
      textMuted: 'rgb(21, 128, 61)',
      icon: '#22c55e',
    },
    dark: {
      background: 'rgba(34, 197, 94, 0.15)',
      border: 'rgba(34, 197, 94, 0.4)',
      text: 'rgb(187, 247, 208)',
      textMuted: 'rgb(134, 239, 172)',
      icon: '#22c55e',
    },
  },
  '401(k) Statement': {
    light: {
      background: 'rgba(240, 253, 250, 1)',
      border: 'rgba(153, 246, 228, 1)',
      text: 'rgb(19, 78, 74)',
      textMuted: 'rgb(17, 94, 89)',
      icon: '#14b8a6',
    },
    dark: {
      background: 'rgba(20, 184, 166, 0.15)',
      border: 'rgba(20, 184, 166, 0.4)',
      text: 'rgb(153, 246, 228)',
      textMuted: 'rgb(94, 234, 212)',
      icon: '#14b8a6',
    },
  },
  'Insurance Policy': {
    light: {
      background: 'rgba(236, 254, 255, 1)',
      border: 'rgba(165, 243, 252, 1)',
      text: 'rgb(21, 94, 117)',
      textMuted: 'rgb(14, 116, 144)',
      icon: '#06b6d4',
    },
    dark: {
      background: 'rgba(6, 182, 212, 0.15)',
      border: 'rgba(6, 182, 212, 0.4)',
      text: 'rgb(165, 243, 252)',
      textMuted: 'rgb(103, 232, 249)',
      icon: '#06b6d4',
    },
  },
  'Mortgage Statement': {
    light: {
      background: 'rgba(255, 247, 237, 1)',
      border: 'rgba(254, 215, 170, 1)',
      text: 'rgb(154, 52, 18)',
      textMuted: 'rgb(194, 65, 12)',
      icon: '#f97316',
    },
    dark: {
      background: 'rgba(249, 115, 22, 0.15)',
      border: 'rgba(249, 115, 22, 0.4)',
      text: 'rgb(254, 215, 170)',
      textMuted: 'rgb(253, 186, 116)',
      icon: '#f97316',
    },
  },
  'Pay Stub': {
    light: {
      background: 'rgba(247, 254, 231, 1)',
      border: 'rgba(217, 249, 157, 1)',
      text: 'rgb(63, 98, 18)',
      textMuted: 'rgb(77, 124, 15)',
      icon: '#84cc16',
    },
    dark: {
      background: 'rgba(132, 204, 22, 0.15)',
      border: 'rgba(132, 204, 22, 0.4)',
      text: 'rgb(217, 249, 157)',
      textMuted: 'rgb(190, 242, 100)',
      icon: '#84cc16',
    },
  },
  Invoice: {
    light: {
      background: 'rgba(254, 249, 235, 1)',
      border: 'rgba(253, 230, 138, 1)',
      text: 'rgb(146, 64, 14)',
      textMuted: 'rgb(180, 83, 9)',
      icon: '#f59e0b',
    },
    dark: {
      background: 'rgba(245, 158, 11, 0.15)',
      border: 'rgba(245, 158, 11, 0.4)',
      text: 'rgb(253, 230, 138)',
      textMuted: 'rgb(252, 211, 77)',
      icon: '#f59e0b',
    },
  },
  Receipt: {
    light: {
      background: 'rgba(253, 242, 248, 1)',
      border: 'rgba(251, 207, 232, 1)',
      text: 'rgb(157, 23, 77)',
      textMuted: 'rgb(190, 24, 93)',
      icon: '#ec4899',
    },
    dark: {
      background: 'rgba(236, 72, 153, 0.15)',
      border: 'rgba(236, 72, 153, 0.4)',
      text: 'rgb(251, 207, 232)',
      textMuted: 'rgb(249, 168, 212)',
      icon: '#ec4899',
    },
  },
  'Loan Agreement': {
    light: {
      background: 'rgba(245, 243, 255, 1)',
      border: 'rgba(221, 214, 254, 1)',
      text: 'rgb(88, 28, 135)',
      textMuted: 'rgb(107, 33, 168)',
      icon: '#8b5cf6',
    },
    dark: {
      background: 'rgba(139, 92, 246, 0.15)',
      border: 'rgba(139, 92, 246, 0.4)',
      text: 'rgb(221, 214, 254)',
      textMuted: 'rgb(196, 181, 253)',
      icon: '#8b5cf6',
    },
  },
  'IRA Statement': {
    light: {
      background: 'rgba(240, 253, 250, 1)',
      border: 'rgba(153, 246, 228, 1)',
      text: 'rgb(19, 78, 74)',
      textMuted: 'rgb(17, 94, 89)',
      icon: '#14b8a6',
    },
    dark: {
      background: 'rgba(20, 184, 166, 0.15)',
      border: 'rgba(20, 184, 166, 0.4)',
      text: 'rgb(153, 246, 228)',
      textMuted: 'rgb(94, 234, 212)',
      icon: '#14b8a6',
    },
  },
  'Trade Confirmation': {
    light: {
      background: 'rgba(240, 253, 244, 1)',
      border: 'rgba(187, 247, 208, 1)',
      text: 'rgb(22, 101, 52)',
      textMuted: 'rgb(21, 128, 61)',
      icon: '#22c55e',
    },
    dark: {
      background: 'rgba(34, 197, 94, 0.15)',
      border: 'rgba(34, 197, 94, 0.4)',
      text: 'rgb(187, 247, 208)',
      textMuted: 'rgb(134, 239, 172)',
      icon: '#22c55e',
    },
  },
  'Investment Prospectus': {
    light: {
      background: 'rgba(240, 253, 244, 1)',
      border: 'rgba(187, 247, 208, 1)',
      text: 'rgb(22, 101, 52)',
      textMuted: 'rgb(21, 128, 61)',
      icon: '#22c55e',
    },
    dark: {
      background: 'rgba(34, 197, 94, 0.15)',
      border: 'rgba(34, 197, 94, 0.4)',
      text: 'rgb(187, 247, 208)',
      textMuted: 'rgb(134, 239, 172)',
      icon: '#22c55e',
    },
  },
  'Insurance Claim': {
    light: {
      background: 'rgba(236, 254, 255, 1)',
      border: 'rgba(165, 243, 252, 1)',
      text: 'rgb(21, 94, 117)',
      textMuted: 'rgb(14, 116, 144)',
      icon: '#06b6d4',
    },
    dark: {
      background: 'rgba(6, 182, 212, 0.15)',
      border: 'rgba(6, 182, 212, 0.4)',
      text: 'rgb(165, 243, 252)',
      textMuted: 'rgb(103, 232, 249)',
      icon: '#06b6d4',
    },
  },
  'Explanation of Benefits': {
    light: {
      background: 'rgba(236, 254, 255, 1)',
      border: 'rgba(165, 243, 252, 1)',
      text: 'rgb(21, 94, 117)',
      textMuted: 'rgb(14, 116, 144)',
      icon: '#06b6d4',
    },
    dark: {
      background: 'rgba(6, 182, 212, 0.15)',
      border: 'rgba(6, 182, 212, 0.4)',
      text: 'rgb(165, 243, 252)',
      textMuted: 'rgb(103, 232, 249)',
      icon: '#06b6d4',
    },
  },
  'Student Loan': {
    light: {
      background: 'rgba(255, 247, 237, 1)',
      border: 'rgba(254, 215, 170, 1)',
      text: 'rgb(154, 52, 18)',
      textMuted: 'rgb(194, 65, 12)',
      icon: '#f97316',
    },
    dark: {
      background: 'rgba(249, 115, 22, 0.15)',
      border: 'rgba(249, 115, 22, 0.4)',
      text: 'rgb(254, 215, 170)',
      textMuted: 'rgb(253, 186, 116)',
      icon: '#f97316',
    },
  },
  'Auto Loan': {
    light: {
      background: 'rgba(255, 247, 237, 1)',
      border: 'rgba(254, 215, 170, 1)',
      text: 'rgb(154, 52, 18)',
      textMuted: 'rgb(194, 65, 12)',
      icon: '#f97316',
    },
    dark: {
      background: 'rgba(249, 115, 22, 0.15)',
      border: 'rgba(249, 115, 22, 0.4)',
      text: 'rgb(254, 215, 170)',
      textMuted: 'rgb(253, 186, 116)',
      icon: '#f97316',
    },
  },
  'Personal Loan': {
    light: {
      background: 'rgba(255, 247, 237, 1)',
      border: 'rgba(254, 215, 170, 1)',
      text: 'rgb(154, 52, 18)',
      textMuted: 'rgb(194, 65, 12)',
      icon: '#f97316',
    },
    dark: {
      background: 'rgba(249, 115, 22, 0.15)',
      border: 'rgba(249, 115, 22, 0.4)',
      text: 'rgb(254, 215, 170)',
      textMuted: 'rgb(253, 186, 116)',
      icon: '#f97316',
    },
  },
  'Purchase Order': {
    light: {
      background: 'rgba(254, 249, 235, 1)',
      border: 'rgba(253, 230, 138, 1)',
      text: 'rgb(146, 64, 14)',
      textMuted: 'rgb(180, 83, 9)',
      icon: '#f59e0b',
    },
    dark: {
      background: 'rgba(245, 158, 11, 0.15)',
      border: 'rgba(245, 158, 11, 0.4)',
      text: 'rgb(253, 230, 138)',
      textMuted: 'rgb(252, 211, 77)',
      icon: '#f59e0b',
    },
  },
  Bill: {
    light: {
      background: 'rgba(254, 249, 235, 1)',
      border: 'rgba(253, 230, 138, 1)',
      text: 'rgb(146, 64, 14)',
      textMuted: 'rgb(180, 83, 9)',
      icon: '#f59e0b',
    },
    dark: {
      background: 'rgba(245, 158, 11, 0.15)',
      border: 'rgba(245, 158, 11, 0.4)',
      text: 'rgb(253, 230, 138)',
      textMuted: 'rgb(252, 211, 77)',
      icon: '#f59e0b',
    },
  },
  // Legal Subclassifications - Contracts and Agreements
  'Lease Agreement': {
    light: {
      background: 'rgba(219, 234, 254, 1)',
      border: 'rgba(96, 165, 250, 1)',
      text: 'rgb(30, 58, 138)',
      textMuted: 'rgb(29, 78, 216)',
      icon: '#3b82f6',
    },
    dark: {
      background: 'rgba(59, 130, 246, 0.15)',
      border: 'rgba(59, 130, 246, 0.4)',
      text: 'rgb(191, 219, 254)',
      textMuted: 'rgb(147, 197, 253)',
      icon: '#3b82f6',
    },
  },
  'Employment Agreement': {
    light: {
      background: 'rgba(224, 231, 255, 1)',
      border: 'rgba(129, 140, 248, 1)',
      text: 'rgb(49, 46, 129)',
      textMuted: 'rgb(67, 56, 202)',
      icon: '#6366f1',
    },
    dark: {
      background: 'rgba(99, 102, 241, 0.15)',
      border: 'rgba(99, 102, 241, 0.4)',
      text: 'rgb(199, 210, 254)',
      textMuted: 'rgb(165, 180, 252)',
      icon: '#6366f1',
    },
  },
  'Service Contract': {
    light: {
      background: 'rgba(238, 242, 255, 1)',
      border: 'rgba(165, 180, 252, 1)',
      text: 'rgb(49, 46, 129)',
      textMuted: 'rgb(67, 56, 202)',
      icon: '#818cf8',
    },
    dark: {
      background: 'rgba(129, 140, 248, 0.15)',
      border: 'rgba(129, 140, 248, 0.4)',
      text: 'rgb(199, 210, 254)',
      textMuted: 'rgb(165, 180, 252)',
      icon: '#818cf8',
    },
  },
  'Purchase Agreement': {
    light: {
      background: 'rgba(239, 246, 255, 1)',
      border: 'rgba(147, 197, 253, 1)',
      text: 'rgb(30, 58, 138)',
      textMuted: 'rgb(29, 78, 216)',
      icon: '#60a5fa',
    },
    dark: {
      background: 'rgba(96, 165, 250, 0.15)',
      border: 'rgba(96, 165, 250, 0.4)',
      text: 'rgb(191, 219, 254)',
      textMuted: 'rgb(147, 197, 253)',
      icon: '#60a5fa',
    },
  },
  NDA: {
    light: {
      background: 'rgba(219, 234, 254, 1)',
      border: 'rgba(96, 165, 250, 1)',
      text: 'rgb(30, 58, 138)',
      textMuted: 'rgb(29, 78, 216)',
      icon: '#2563eb',
    },
    dark: {
      background: 'rgba(37, 99, 235, 0.15)',
      border: 'rgba(37, 99, 235, 0.4)',
      text: 'rgb(191, 219, 254)',
      textMuted: 'rgb(147, 197, 253)',
      icon: '#2563eb',
    },
  },
  // Legal Subclassifications - Estate and Family
  Will: {
    light: {
      background: 'rgba(250, 245, 255, 1)',
      border: 'rgba(196, 181, 253, 1)',
      text: 'rgb(88, 28, 135)',
      textMuted: 'rgb(107, 33, 168)',
      icon: '#a855f7',
    },
    dark: {
      background: 'rgba(168, 85, 247, 0.15)',
      border: 'rgba(168, 85, 247, 0.4)',
      text: 'rgb(233, 213, 255)',
      textMuted: 'rgb(196, 181, 253)',
      icon: '#a855f7',
    },
  },
  'Power of Attorney': {
    light: {
      background: 'rgba(243, 232, 255, 1)',
      border: 'rgba(167, 139, 250, 1)',
      text: 'rgb(88, 28, 135)',
      textMuted: 'rgb(107, 33, 168)',
      icon: '#9333ea',
    },
    dark: {
      background: 'rgba(147, 51, 234, 0.15)',
      border: 'rgba(147, 51, 234, 0.4)',
      text: 'rgb(233, 213, 255)',
      textMuted: 'rgb(196, 181, 253)',
      icon: '#9333ea',
    },
  },
  'Trust Document': {
    light: {
      background: 'rgba(245, 243, 255, 1)',
      border: 'rgba(196, 181, 253, 1)',
      text: 'rgb(88, 28, 135)',
      textMuted: 'rgb(107, 33, 168)',
      icon: '#8b5cf6',
    },
    dark: {
      background: 'rgba(139, 92, 246, 0.15)',
      border: 'rgba(139, 92, 246, 0.4)',
      text: 'rgb(221, 214, 254)',
      textMuted: 'rgb(196, 181, 253)',
      icon: '#8b5cf6',
    },
  },
  'Divorce Document': {
    light: {
      background: 'rgba(254, 242, 242, 1)',
      border: 'rgba(252, 165, 165, 1)',
      text: 'rgb(153, 27, 27)',
      textMuted: 'rgb(185, 28, 28)',
      icon: '#ef4444',
    },
    dark: {
      background: 'rgba(239, 68, 68, 0.15)',
      border: 'rgba(239, 68, 68, 0.4)',
      text: 'rgb(254, 202, 202)',
      textMuted: 'rgb(252, 165, 165)',
      icon: '#ef4444',
    },
  },
  'Marriage Certificate': {
    light: {
      background: 'rgba(253, 242, 248, 1)',
      border: 'rgba(251, 207, 232, 1)',
      text: 'rgb(157, 23, 77)',
      textMuted: 'rgb(190, 24, 93)',
      icon: '#ec4899',
    },
    dark: {
      background: 'rgba(236, 72, 153, 0.15)',
      border: 'rgba(236, 72, 153, 0.4)',
      text: 'rgb(251, 207, 232)',
      textMuted: 'rgb(249, 168, 212)',
      icon: '#ec4899',
    },
  },
  // Legal Subclassifications - Property and Real Estate
  'Property Deed': {
    light: {
      background: 'rgba(240, 253, 244, 1)',
      border: 'rgba(134, 239, 172, 1)',
      text: 'rgb(22, 101, 52)',
      textMuted: 'rgb(21, 128, 61)',
      icon: '#22c55e',
    },
    dark: {
      background: 'rgba(34, 197, 94, 0.15)',
      border: 'rgba(34, 197, 94, 0.4)',
      text: 'rgb(187, 247, 208)',
      textMuted: 'rgb(134, 239, 172)',
      icon: '#22c55e',
    },
  },
  'Mortgage Document': {
    light: {
      background: 'rgba(236, 253, 245, 1)',
      border: 'rgba(110, 231, 183, 1)',
      text: 'rgb(19, 78, 74)',
      textMuted: 'rgb(17, 94, 89)',
      icon: '#10b981',
    },
    dark: {
      background: 'rgba(16, 185, 129, 0.15)',
      border: 'rgba(16, 185, 129, 0.4)',
      text: 'rgb(167, 243, 208)',
      textMuted: 'rgb(110, 231, 183)',
      icon: '#10b981',
    },
  },
  'Title Document': {
    light: {
      background: 'rgba(240, 253, 250, 1)',
      border: 'rgba(94, 234, 212, 1)',
      text: 'rgb(19, 78, 74)',
      textMuted: 'rgb(17, 94, 89)',
      icon: '#14b8a6',
    },
    dark: {
      background: 'rgba(20, 184, 166, 0.15)',
      border: 'rgba(20, 184, 166, 0.4)',
      text: 'rgb(153, 246, 228)',
      textMuted: 'rgb(94, 234, 212)',
      icon: '#14b8a6',
    },
  },
  'HOA Document': {
    light: {
      background: 'rgba(247, 254, 231, 1)',
      border: 'rgba(190, 242, 100, 1)',
      text: 'rgb(63, 98, 18)',
      textMuted: 'rgb(77, 124, 15)',
      icon: '#84cc16',
    },
    dark: {
      background: 'rgba(132, 204, 22, 0.15)',
      border: 'rgba(132, 204, 22, 0.4)',
      text: 'rgb(217, 249, 157)',
      textMuted: 'rgb(190, 242, 100)',
      icon: '#84cc16',
    },
  },
  'Property Transfer': {
    light: {
      background: 'rgba(236, 252, 203, 1)',
      border: 'rgba(163, 230, 53, 1)',
      text: 'rgb(63, 98, 18)',
      textMuted: 'rgb(77, 124, 15)',
      icon: '#65a30d',
    },
    dark: {
      background: 'rgba(101, 163, 13, 0.15)',
      border: 'rgba(101, 163, 13, 0.4)',
      text: 'rgb(217, 249, 157)',
      textMuted: 'rgb(190, 242, 100)',
      icon: '#65a30d',
    },
  },
  // Legal Subclassifications - Court and Legal Proceedings
  'Court Order': {
    light: {
      background: 'rgba(254, 249, 235, 1)',
      border: 'rgba(253, 224, 71, 1)',
      text: 'rgb(146, 64, 14)',
      textMuted: 'rgb(161, 98, 7)',
      icon: '#eab308',
    },
    dark: {
      background: 'rgba(234, 179, 8, 0.15)',
      border: 'rgba(234, 179, 8, 0.4)',
      text: 'rgb(254, 240, 138)',
      textMuted: 'rgb(253, 224, 71)',
      icon: '#eab308',
    },
  },
  'Legal Notice': {
    light: {
      background: 'rgba(254, 243, 199, 1)',
      border: 'rgba(252, 211, 77, 1)',
      text: 'rgb(146, 64, 14)',
      textMuted: 'rgb(161, 98, 7)',
      icon: '#facc15',
    },
    dark: {
      background: 'rgba(250, 204, 21, 0.15)',
      border: 'rgba(250, 204, 21, 0.4)',
      text: 'rgb(254, 240, 138)',
      textMuted: 'rgb(253, 224, 71)',
      icon: '#facc15',
    },
  },
  'Court Filing': {
    light: {
      background: 'rgba(255, 247, 237, 1)',
      border: 'rgba(253, 186, 116, 1)',
      text: 'rgb(154, 52, 18)',
      textMuted: 'rgb(194, 65, 12)',
      icon: '#f97316',
    },
    dark: {
      background: 'rgba(249, 115, 22, 0.15)',
      border: 'rgba(249, 115, 22, 0.4)',
      text: 'rgb(254, 215, 170)',
      textMuted: 'rgb(253, 186, 116)',
      icon: '#f97316',
    },
  },
  'Settlement Agreement': {
    light: {
      background: 'rgba(254, 240, 138, 1)',
      border: 'rgba(250, 204, 21, 1)',
      text: 'rgb(146, 64, 14)',
      textMuted: 'rgb(161, 98, 7)',
      icon: '#fbbf24',
    },
    dark: {
      background: 'rgba(251, 191, 36, 0.15)',
      border: 'rgba(251, 191, 36, 0.4)',
      text: 'rgb(254, 240, 138)',
      textMuted: 'rgb(253, 224, 71)',
      icon: '#fbbf24',
    },
  },
  'Legal Correspondence': {
    light: {
      background: 'rgba(254, 249, 235, 1)',
      border: 'rgba(253, 230, 138, 1)',
      text: 'rgb(146, 64, 14)',
      textMuted: 'rgb(180, 83, 9)',
      icon: '#f59e0b',
    },
    dark: {
      background: 'rgba(245, 158, 11, 0.15)',
      border: 'rgba(245, 158, 11, 0.4)',
      text: 'rgb(253, 230, 138)',
      textMuted: 'rgb(252, 211, 77)',
      icon: '#f59e0b',
    },
  },
};

/**
 * Get theme colors based on current mode
 */
export function getThemeColors(themeName: string, isDark: boolean): ColorScheme {
  const themeConfig = THEME_COLORS[themeName];

  if (!themeConfig) {
    // Fallback to Unclassified theme
    const fallbackConfig = THEME_COLORS.Unclassified ?? {
      light: {
        background: 'rgba(249, 250, 251, 0.8)',
        backgroundHover: 'rgba(243, 244, 246, 0.9)',
        border: 'rgba(209, 213, 219, 0.5)',
        borderHover: 'rgba(156, 163, 175, 0.7)',
        text: 'rgb(55, 65, 81)',
        textMuted: 'rgb(75, 85, 99)',
        icon: '📄',
      },
      dark: {
        background: 'rgba(17, 24, 39, 0.4)',
        backgroundHover: 'rgba(17, 24, 39, 0.6)',
        border: 'rgba(107, 114, 128, 0.3)',
        borderHover: 'rgba(107, 114, 128, 0.5)',
        text: 'rgb(229, 231, 235)',
        textMuted: 'rgb(209, 213, 219)',
        icon: '📄',
      },
    };
    return isDark ? fallbackConfig.dark : fallbackConfig.light;
  }

  return isDark ? themeConfig.dark : themeConfig.light;
}

/**
 * Get subtheme colors based on current mode
 */
export function getSubthemeColors(subthemeName: string, isDark: boolean): ColorScheme {
  const subthemeConfig = SUBTHEME_COLORS[subthemeName];
  if (!subthemeConfig) {
    // Fallback to a default subtheme color
    return {
      background: isDark ? 'rgba(31, 41, 55, 0.3)' : 'rgba(249, 250, 251, 0.9)',
      border: isDark ? 'rgba(107, 114, 128, 0.3)' : 'rgba(209, 213, 219, 0.4)',
      text: isDark ? 'rgb(229, 231, 235)' : 'rgb(55, 65, 81)',
      textMuted: isDark ? 'rgb(209, 213, 219)' : 'rgb(75, 85, 99)',
      icon: isDark ? 'rgb(156, 163, 175)' : 'rgb(107, 114, 128)',
    };
  }
  return isDark ? subthemeConfig.dark : subthemeConfig.light;
}

/**
 * Hook to get current theme mode
 */
export function useThemeMode(): boolean {
  if (typeof window === 'undefined') return false;
  return document.documentElement.classList.contains('dark');
}

/**
 * Generate CSS variables for a color scheme
 */
export function generateCSSVariables(colors: ColorScheme, prefix: string): Record<string, string> {
  return {
    [`--${prefix}-bg`]: colors.background,
    [`--${prefix}-bg-hover`]: colors.backgroundHover ?? colors.background,
    [`--${prefix}-border`]: colors.border,
    [`--${prefix}-border-hover`]: colors.borderHover ?? colors.border,
    [`--${prefix}-text`]: colors.text,
    [`--${prefix}-text-muted`]: colors.textMuted,
    [`--${prefix}-icon`]: colors.icon,
  };
}

/**
 * Create inline styles for a theme card
 */
export function createThemeCardStyles(themeName: string, isDark: boolean): React.CSSProperties {
  const colors = getThemeColors(themeName, isDark);

  if (colors.gradient) {
    return {
      background: `linear-gradient(135deg, ${colors.gradient.from} 0%, ${colors.gradient.via ?? colors.gradient.to} 50%, ${colors.gradient.to} 100%)`,
      border: `2px solid ${colors.border}`,
      color: colors.text,
    };
  }

  return {
    backgroundColor: colors.background,
    border: `2px solid ${colors.border}`,
    color: colors.text,
  };
}

/**
 * Create glassmorphism styles
 */
export function createGlassStyles(themeName: string, isDark: boolean): React.CSSProperties {
  const colors = getThemeColors(themeName, isDark);

  if (colors.glass) {
    return {
      background: colors.glass.background,
      backdropFilter: colors.glass.backdropBlur,
      WebkitBackdropFilter: colors.glass.backdropBlur,
      border: `1px solid ${colors.glass.border}`,
    };
  }

  return {
    background: colors.background,
    border: `1px solid ${colors.border}`,
  };
}
