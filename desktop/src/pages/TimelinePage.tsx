import React, { useState } from 'react';
import { Calendar, ZoomIn, ZoomOut, Clock, FileText, Loader2, AlertCircle } from 'lucide-react';
import { useTimeline } from '../hooks/useTimeline';
import { ZoomLevel } from '../types/timeline';

const TimelinePage: React.FC = () => {
  const { state, actions } = useTimeline({
    initialZoomLevel: 'month',
    autoFetch: true
  });

  const zoomLevels = [
    { key: 'year' as ZoomLevel, label: 'Year', icon: Calendar },
    { key: 'month' as ZoomLevel, label: 'Month', icon: Calendar },
    { key: 'week' as ZoomLevel, label: 'Week', icon: Calendar },
    { key: 'day' as ZoomLevel, label: 'Day', icon: Clock },
  ] as const;

  const handleZoomChange = (level: ZoomLevel) => {
    actions.setZoomLevel(level);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className="p-6 h-full flex flex-col">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Content Timeline</h1>
            <p className="text-muted-foreground mt-1">
              Explore your documents based on their content dates and time periods
            </p>
          </div>
          
          {/* Zoom Controls and Date Navigation */}
          <div className="flex items-center space-x-4">
            {/* Date Range Info */}
            {state.periods && state.periods.earliest_date && state.periods.latest_date && (
              <div className="glass-card p-2 px-3 rounded-lg text-sm text-muted-foreground">
                Data from {formatDate(state.periods.earliest_date)} to {formatDate(state.periods.latest_date)}
              </div>
            )}
            
            {/* Quick Date Jumps */}
            {state.periods && state.periods.periods && state.periods.periods.length > 0 && (
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => {
                    console.log('Start clicked, earliest date:', state.periods!.earliest_date);
                    actions.navigateToDate(new Date(state.periods!.earliest_date));
                  }}
                  className="px-3 py-1 text-sm text-muted-foreground hover:text-foreground hover:bg-white/5 rounded-md transition-all"
                  title="Go to earliest date"
                >
                  Start
                </button>
                <button
                  onClick={() => {
                    console.log('Latest clicked, latest date:', state.periods!.latest_date);
                    actions.navigateToDate(new Date(state.periods!.latest_date));
                  }}
                  className="px-3 py-1 text-sm text-muted-foreground hover:text-foreground hover:bg-white/5 rounded-md transition-all"
                  title="Go to latest date"
                >
                  Latest
                </button>
              </div>
            )}
            
            {/* Period Navigation */}
            {state.periods && state.periods.periods && state.periods.periods.length > 0 && (
              <div className="flex items-center space-x-1 text-xs">
                <span className="text-muted-foreground mr-2">Jump to:</span>
                {state.periods.periods.slice(0, 6).map((period) => (
                  <button
                    key={period.period_label}
                    onClick={() => {
                      // Navigate to the 15th of that month
                      const jumpDate = new Date(period.year, period.month - 1, 15);
                      console.log(`Jumping to period ${period.period_label}:`, jumpDate);
                      actions.navigateToDate(jumpDate);
                    }}
                    className="px-2 py-1 bg-blue-500/10 text-blue-400 rounded text-xs hover:bg-blue-500/20 transition-colors"
                    title={`${period.document_count} documents`}
                  >
                    {period.period_label} ({period.document_count})
                  </button>
                ))}
                {state.periods.periods.length > 6 && (
                  <span className="text-muted-foreground">+{state.periods.periods.length - 6} more</span>
                )}
              </div>
            )}
            
            {/* Zoom Controls */}
            <div className="flex items-center space-x-2 glass-card p-2 rounded-lg">
              {zoomLevels.map((level) => (
                <button
                  key={level.key}
                  onClick={() => handleZoomChange(level.key)}
                  className={`px-3 py-1 text-sm rounded-md transition-all ${
                    state.zoomLevel === level.key
                      ? 'bg-primary/20 text-primary border border-primary/30'
                      : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
                  }`}
                >
                  {level.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Timeline Container */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full glass-card rounded-xl p-6 border border-border/30">
          
          {/* Loading State */}
          {state.loading && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
                <p className="text-muted-foreground">Loading timeline data...</p>
              </div>
            </div>
          )}

          {/* Error State */}
          {state.error && !state.loading && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-md">
                <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-foreground mb-2">Timeline Error</h3>
                <p className="text-muted-foreground mb-4">{state.error}</p>
                <button
                  onClick={() => actions.refreshData()}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                >
                  Try Again
                </button>
              </div>
            </div>
          )}

          {/* No Data State */}
          {!state.loading && !state.error && state.documents.length === 0 && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-lg">
                <div className="w-20 h-20 mx-auto mb-6 rounded-2xl glass-card border border-border/30 flex items-center justify-center">
                  <Calendar className="w-10 h-10 text-primary/60" />
                </div>
                <h3 className="text-xl font-semibold text-foreground mb-3">
                  No Timeline Data
                </h3>
                <p className="text-muted-foreground mb-6">
                  No documents with content dates found for the selected time period. 
                  Upload some documents to see your timeline.
                </p>
                <button
                  onClick={() => actions.refreshData()}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                >
                  Refresh Timeline
                </button>
              </div>
            </div>
          )}

          {/* Timeline Data */}
          {!state.loading && !state.error && state.documents.length > 0 && (
            <div className="h-full overflow-y-auto">
              <div className="space-y-4">
                <div className="flex items-center justify-between mb-6">
                  <div className="text-sm text-muted-foreground">
                    {state.documents.length} documents found
                    {state.dateRange && (
                      <span className="ml-2">
                        ({formatDate(state.dateRange.start.toISOString())} - {formatDate(state.dateRange.end.toISOString())})
                      </span>
                    )}
                    <br />
                    <span className="text-xs opacity-75">
                      Current view: {state.zoomLevel} | Selected: {formatDate(state.selectedDate.toISOString())}
                    </span>
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={async () => {
                        try {
                          const response = await fetch('http://localhost:8000/api/debug/content-dates');
                          const data = await response.json();
                          console.log('🔍 All content dates in database:', data);
                        } catch (error) {
                          console.error('Failed to fetch debug data:', error);
                        }
                      }}
                      className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
                      title="Debug: Show all content dates"
                    >
                      Debug
                    </button>
                    <button
                      onClick={async () => {
                        if (!confirm('This will clear all extracted dates and re-extract them with improved logic. Continue?')) return;
                        
                        try {
                          // Clear existing dates
                          console.log('🧹 Clearing old content dates...');
                          const clearResponse = await fetch('http://localhost:8000/api/debug/clear-content-dates', { method: 'POST' });
                          const clearData = await clearResponse.json();
                          console.log('✅ Cleared dates:', clearData);
                          
                          // Re-extract with new prompt
                          console.log('🔄 Re-extracting dates with improved prompt...');
                          const extractResponse = await fetch('http://localhost:8000/api/debug/re-extract-dates', { method: 'POST' });
                          const extractData = await extractResponse.json();
                          console.log('✅ Re-extracted dates:', extractData);
                          
                          // Refresh timeline
                          actions.refreshData();
                          
                        } catch (error) {
                          console.error('Failed to re-extract dates:', error);
                        }
                      }}
                      className="text-sm text-green-400 hover:text-green-300 transition-colors"
                      title="Clear and re-extract all content dates"
                    >
                      Re-extract
                    </button>
                    <button
                      onClick={() => actions.refreshData()}
                      className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                    >
                      Refresh
                    </button>
                  </div>
                </div>

                {/* Simple Timeline List (will be replaced with proper timeline components) */}
                <div className="space-y-3">
                  {state.documents.map((doc) => (
                    <div key={doc.id} className="glass-card p-4 rounded-lg border border-border/20 hover:border-border/40 transition-colors">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start space-x-3">
                          <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
                            <FileText className="w-4 h-4 text-primary" />
                          </div>
                          <div className="flex-1">
                            <h4 className="font-medium text-foreground mb-1">{doc.title}</h4>
                            <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                              <span className="flex items-center space-x-1">
                                <Calendar className="w-3 h-3" />
                                <span>{formatDate(doc.content_date)}</span>
                              </span>
                              <span>{formatFileSize(doc.size_bytes)}</span>
                              {doc.date_type && (
                                <span className="px-2 py-1 bg-blue-500/10 text-blue-400 rounded text-xs">
                                  {doc.date_type}
                                </span>
                              )}
                            </div>
                            <div className="mt-2 flex items-center space-x-2">
                              <div className="w-2 h-2 rounded-full bg-green-400"></div>
                              <span className="text-xs text-muted-foreground">
                                {Math.round(doc.confidence_score * 100)}% confidence
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};

export default TimelinePage;