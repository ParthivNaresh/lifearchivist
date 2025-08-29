import React from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  Sparkles,
  FileText,
  Image,
  File,
  Table,
  FileType,
  Archive
} from 'lucide-react';
import { Topic, TopicCardProps } from '../../types/topics';

const getTrendIcon = (trend: Topic['trend']) => {
  switch (trend) {
    case 'new':
      return <Sparkles className="w-4 h-4 text-purple-400" />;
    case 'growing':
      return <TrendingUp className="w-4 h-4 text-emerald-400" />;
    case 'stable':
      return <Minus className="w-4 h-4 text-blue-400" />;
    default:
      return <Minus className="w-4 h-4 text-gray-400" />;
  }
};

const getFileTypeIcon = (fileType: string) => {
  switch (fileType) {
    case 'PDF':
      return <FileText className="w-3 h-3" />;
    case 'Document':
      return <File className="w-3 h-3" />;
    case 'Image':
      return <Image className="w-3 h-3" />;
    case 'Spreadsheet':
      return <Table className="w-3 h-3" />;
    case 'Text':
      return <FileType className="w-3 h-3" />;
    default:
      return <Archive className="w-3 h-3" />;
  }
};

const getCardSize = (sizeTier: Topic['size_tier']) => {
  switch (sizeTier) {
    case 'large':
      return 'col-span-2 row-span-2';
    case 'medium':
      return 'col-span-1 row-span-2';
    case 'small':
    default:
      return 'col-span-1 row-span-1';
  }
};

const getGradientColors = (topic: Topic) => {
  const baseColors = [
    'from-purple-500/20 via-blue-500/20 to-purple-600/20',
    'from-blue-500/20 via-cyan-500/20 to-blue-600/20',
    'from-emerald-500/20 via-teal-500/20 to-emerald-600/20',
    'from-amber-500/20 via-orange-500/20 to-amber-600/20',
    'from-pink-500/20 via-rose-500/20 to-pink-600/20',
    'from-indigo-500/20 via-purple-500/20 to-indigo-600/20',
  ];
  
  // Generate consistent color based on topic name
  const index = topic.name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) % baseColors.length;
  return baseColors[index];
};

const formatTimeAgo = (timestamp: string | null): string => {
  if (!timestamp) return 'No activity';
  
  const now = new Date();
  const date = new Date(timestamp);
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffMins = Math.floor(diffMs / (1000 * 60));

  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
};

export const TopicCard: React.FC<TopicCardProps> = ({ topic, onClick, className = '' }) => {
  const gradientColors = getGradientColors(topic);
  const cardSize = getCardSize(topic.size_tier);

  return (
    <div 
      className={`group relative upload-item-glass rounded-2xl p-6 cursor-pointer transition-all duration-300 hover:scale-[1.02] hover:-translate-y-1 ${cardSize} ${className}`}
      onClick={() => onClick?.(topic)}
      style={{
        background: `linear-gradient(135deg, ${gradientColors})`,
      }}
    >
      {/* Hover Effect Overlay */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

      {/* Content */}
      <div className="relative z-10 h-full flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-white/90 truncate mb-1">
              {topic.name}
            </h3>
            <div className="flex items-center space-x-2">
              <span className="text-2xl font-bold text-white">
                {topic.document_count}
              </span>
              <span className="text-sm text-white/60">
                document{topic.document_count !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {getTrendIcon(topic.trend)}
          </div>
        </div>

        {/* Recent Activity */}
        {topic.recent_count > 0 && (
          <div className="mb-4 px-3 py-1 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 w-fit">
            <span className="text-xs text-white/80">
              +{topic.recent_count} this week
            </span>
          </div>
        )}

        {/* File Types */}
        <div className="flex flex-wrap gap-2 mb-4">
          {topic.file_types.slice(0, 4).map((fileType, index) => (
            <div 
              key={fileType}
              className="flex items-center space-x-1 px-2 py-1 rounded-lg bg-white/10 backdrop-blur-sm border border-white/20"
            >
              {getFileTypeIcon(fileType)}
              <span className="text-xs text-white/80">{fileType}</span>
            </div>
          ))}
          {topic.file_types.length > 4 && (
            <div className="flex items-center px-2 py-1 rounded-lg bg-white/10 backdrop-blur-sm border border-white/20">
              <span className="text-xs text-white/60">
                +{topic.file_types.length - 4} more
              </span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-auto flex items-center justify-between text-xs text-white/60">
          <span>{formatTimeAgo(topic.last_activity)}</span>
          <div className="flex items-center space-x-1">
            <div className="w-2 h-2 rounded-full bg-emerald-400/60" />
            <span>Active</span>
          </div>
        </div>
      </div>

      {/* Shimmer Effect on Hover */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-20 transition-opacity duration-500">
        <div className="absolute inset-0 shimmer" />
      </div>
    </div>
  );
};