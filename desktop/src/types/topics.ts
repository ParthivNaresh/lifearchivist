export interface Topic {
  name: string;
  document_count: number;
  recent_count: number;
  file_types: string[];
  trend: 'new' | 'growing' | 'stable';
  last_activity: string | null;
  size_tier: 'small' | 'medium' | 'large';
}

export interface TopicLandscapeData {
  topics: Topic[];
  total_topics: number;
  generated_at: string;
}

export interface TopicCardProps {
  topic: Topic;
  onClick?: (topic: Topic) => void;
  className?: string;
}