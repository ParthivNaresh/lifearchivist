import React, { useState, useEffect } from 'react';
import { Loader2, MapPin, TrendingUp, Eye, RefreshCw } from 'lucide-react';
import axios from 'axios';
import { TopicLandscapeData, Topic } from '../../../../types/topics';
import { TopicCard } from './TopicCard';

interface TopicLandscapeProps {
  onTopicClick?: (topic: Topic) => void;
}

export const TopicLandscape: React.FC<TopicLandscapeProps> = ({ onTopicClick }) => {
  const [data, setData] = useState<TopicLandscapeData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [hasInitialized, setHasInitialized] = useState(false);

  const fetchTopics = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get<TopicLandscapeData>('http://localhost:8000/api/topics');
      setData(response.data);
      setLastRefresh(new Date());
      setHasInitialized(true);
    } catch (err: any) {
      console.error('Failed to fetch topics:', err);
      // Only show error if this isn't the first load
      if (hasInitialized) {
        setError(err.response?.data?.detail || 'Failed to load topics');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Delay initial load to give backend time to start
    const timer = setTimeout(() => {
      fetchTopics();
    }, 1000);
    
    return () => clearTimeout(timer);
  }, []);

  const handleTopicClick = (topic: Topic) => {
    // Default behavior: navigate to documents page with filter
    if (onTopicClick) {
      onTopicClick(topic);
    } else {
      // Fallback: navigate to documents page with tag filter
      window.location.href = `/documents?tag=${encodeURIComponent(topic.name)}`;
    }
  };

  const getTotalDocuments = () => {
    return data?.topics.reduce((sum, topic) => sum + topic.document_count, 0) || 0;
  };

  const getActiveTopics = () => {
    return data?.topics.filter(topic => topic.recent_count > 0).length || 0;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground">Analyzing your knowledge landscape...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="glass-card p-6 rounded-xl max-w-md mx-auto">
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={fetchTopics}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors flex items-center space-x-2 mx-auto"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Retry</span>
          </button>
        </div>
      </div>
    );
  }

  // Show initial state if not initialized and no data
  if (!hasInitialized && !data) {
    return (
      <div className="text-center py-12">
        <div className="glass-card p-8 rounded-xl max-w-md mx-auto">
          <MapPin className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Knowledge Landscape</h3>
          <p className="text-muted-foreground text-sm mb-4">
            Your topics will appear here once documents are uploaded and processed.
          </p>
          <button
            onClick={fetchTopics}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            Load Topics
          </button>
        </div>
      </div>
    );
  }

  if (!data || data.topics.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="glass-card p-8 rounded-xl max-w-md mx-auto">
          <MapPin className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">No Topics Yet</h3>
          <p className="text-muted-foreground text-sm">
            Upload some documents to see your knowledge landscape appear here. 
            The system will automatically categorize and organize your content.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Stats */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold flex items-center space-x-2">
            <MapPin className="w-5 h-5 text-primary" />
            <span>Knowledge Landscape</span>
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Explore your {getTotalDocuments().toLocaleString()} documents across {data.topics.length} topics
          </p>
        </div>

        <div className="flex items-center space-x-4 text-sm text-muted-foreground">
          <div className="flex items-center space-x-1">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span>{getActiveTopics()} growing</span>
          </div>
          <div className="flex items-center space-x-1">
            <Eye className="w-4 h-4" />
            <span>Updated {lastRefresh.toLocaleTimeString()}</span>
          </div>
          <button
            onClick={fetchTopics}
            className="p-1 rounded-md hover:bg-muted/50 transition-colors"
            title="Refresh landscape"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Topic Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 auto-rows-max">
        {data.topics.map((topic) => (
          <TopicCard
            key={topic.name}
            topic={topic}
            onClick={handleTopicClick}
          />
        ))}
      </div>

      {/* Footer Info */}
      <div className="text-center">
        <p className="text-xs text-muted-foreground">
          Topics are automatically generated from your document content and updated in real-time
        </p>
      </div>
    </div>
  );
};