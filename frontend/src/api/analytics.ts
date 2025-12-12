import { api } from './client';

export interface UsageAnalytics {
  queries_by_day: Array<{ date: string; count: number }>;
  popular_documents: Array<{
    document_id: number;
    title: string;
    reference_count: number;
  }>;
  total_queries: number;
  period_days: number;
}

export interface DocumentInsights {
  most_referenced_documents: Array<{
    document_id: number;
    title: string;
    num_chunks: number;
    times_referenced: number;
  }>;
  chunk_quality: {
    average_tokens: number;
    min_tokens: number;
    max_tokens: number;
    total_chunks: number;
  };
}

export interface UserActivity {
  questions_asked: number;
  documents_uploaded: number;
  average_session_duration_minutes: number;
  total_sessions: number;
  daily_activity: Array<{ date: string; messages: number }>;
  period_days: number;
}

export interface QueryAnalytics {
  total_queries: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  min_latency_ms: number;
  max_latency_ms: number;
  total_tokens: number;
  avg_tokens: number;
  cache_hit_rate: number;
  cache_hits: number;
  avg_confidence: number;
  avg_citations: number;
}

export interface SlowQuery {
  user_id: number;
  session_id: number;
  query: string;
  latency_ms: number;
  token_count: number;
  cache_hit: boolean;
  strategy: string;
  timestamp: string;
  confidence_score?: number;
  num_citations: number;
}

export type StrategyComparison = Record<string, {
  count: number;
  avg_latency_ms: number;
  avg_tokens: number;
  cache_hit_rate: number;
  avg_confidence: number;
}>;

export interface PerformanceMetrics {
  query_analytics: QueryAnalytics;
  slow_queries: SlowQuery[];
  strategy_comparison: StrategyComparison;
  average_chunks_per_document: number;
  total_chunks_indexed: number;
  total_documents_ready: number;
  average_response_time_ms: number;
  average_embedding_time_ms: number;
}

export const analyticsApi = {
  getUsage: async (days: number = 30): Promise<UsageAnalytics> => {
    return api.get<UsageAnalytics>(`/admin/analytics/usage?days=${days}`);
  },

  getDocumentInsights: async (): Promise<DocumentInsights> => {
    return api.get<DocumentInsights>('/admin/analytics/documents');
  },

  getUserActivity: async (days: number = 30): Promise<UserActivity> => {
    return api.get<UserActivity>(`/admin/analytics/activity?days=${days}`);
  },

  getPerformance: async (hours: number = 24): Promise<PerformanceMetrics> => {
    return api.get<PerformanceMetrics>(`/admin/analytics/performance?hours=${hours}`);
  },

  getStats: async () => {
    return api.get('/admin/stats');
  },
};

