import { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { analyticsApi } from '../api/analytics';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { Icon } from '../components/common/Icon';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

export function AnalyticsPage() {
  const [days, setDays] = useState(30);
  const usageApi = useApi(() => analyticsApi.getUsage(days));
  const insightsApi = useApi(analyticsApi.getDocumentInsights);
  const activityApi = useApi(() => analyticsApi.getUserActivity(days));
  const performanceApi = useApi(() => analyticsApi.getPerformance(24));

  useEffect(() => {
    usageApi.execute();
    insightsApi.execute();
    activityApi.execute();
    performanceApi.execute();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days]);

  const usageData = usageApi.data;
  const insightsData = insightsApi.data;
  const activityData = activityApi.data;
  const performanceData = performanceApi.data;

  const isLoading = usageApi.loading || insightsApi.loading || activityApi.loading || performanceApi.loading;
  const hasError = usageApi.error || insightsApi.error || activityApi.error || performanceApi.error;

  if (isLoading && !usageData && !insightsData && !activityData && !performanceData) {
    return (
      <div className="flex justify-center items-center h-full">
        <div className="text-center">
          <LoadingSpinner size="lg" className="mb-4" />
          <div className="text-gray-500 dark:text-gray-400">Loading analytics...</div>
        </div>
      </div>
    );
  }

  if (hasError && !usageData && !insightsData && !activityData && !performanceData) {
    return (
      <div className="flex justify-center items-center h-full">
        <div className="text-center bg-white dark:bg-gray-800 rounded-xl p-8 border border-gray-200 dark:border-gray-700">
          <p className="text-red-600 dark:text-red-400 font-semibold mb-2">Error loading analytics</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {usageApi.error || insightsApi.error || activityApi.error || performanceApi.error}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Analytics Dashboard</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Insights into your usage and performance</p>
          </div>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Total Queries"
            value={usageData?.total_queries || 0}
            subtitle={`Over ${days} days`}
            icon={<Icon name="chat" size="lg" className="text-blue-500 dark:text-blue-400" />}
          />
          <MetricCard
            title="Documents Uploaded"
            value={activityData?.documents_uploaded || 0}
            subtitle={`Over ${days} days`}
            icon={<Icon name="document" size="lg" className="text-indigo-500 dark:text-indigo-400" />}
          />
          <MetricCard
            title="Average Session"
            value={`${(activityData?.average_session_duration_minutes || 0).toFixed(1)} min`}
            subtitle="Duration"
            icon={<Icon name="clock" size="lg" className="text-purple-500 dark:text-purple-400" />}
          />
          <MetricCard
            title="Total Chunks"
            value={performanceData?.total_chunks_indexed || 0}
            subtitle="Indexed"
            icon={<Icon name="search" size="lg" className="text-pink-500 dark:text-pink-400" />}
          />
        </div>

        {/* Charts Row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Queries Per Day */}
          <ChartCard title="Queries Per Day" icon={<Icon name="line-chart" size="md" className="text-blue-500 dark:text-blue-400" />}>
            {usageData?.queries_by_day && usageData.queries_by_day.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={usageData.queries_by_day}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis
                    dataKey="date"
                    stroke="#6B7280"
                    style={{ fontSize: '12px' }}
                    tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  />
                  <YAxis stroke="#6B7280" style={{ fontSize: '12px' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #E5E7EB',
                      borderRadius: '8px',
                    }}
                    labelFormatter={(value) => new Date(value).toLocaleDateString()}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="count"
                    stroke="#3B82F6"
                    strokeWidth={2}
                    dot={{ fill: '#3B82F6', r: 4 }}
                    name="Queries"
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-400">
                No data available
              </div>
            )}
          </ChartCard>

          {/* Popular Documents */}
          <ChartCard title="Most Referenced Documents" icon={<Icon name="book" size="md" className="text-indigo-500 dark:text-indigo-400" />}>
            {insightsData?.most_referenced_documents && insightsData.most_referenced_documents.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={insightsData.most_referenced_documents.slice(0, 5)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis
                    dataKey="title"
                    stroke="#6B7280"
                    style={{ fontSize: '12px' }}
                    angle={-45}
                    textAnchor="end"
                    height={80}
                  />
                  <YAxis stroke="#6B7280" style={{ fontSize: '12px' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #E5E7EB',
                      borderRadius: '8px',
                    }}
                  />
                  <Bar dataKey="times_referenced" fill="#3B82F6" name="References" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-400">
                No data available
              </div>
            )}
          </ChartCard>
        </div>

        {/* Charts Row 2 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Daily Activity */}
          <ChartCard title="Daily Activity" icon={<Icon name="trending-up" size="md" className="text-purple-500 dark:text-purple-400" />}>
            {activityData?.daily_activity && activityData.daily_activity.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={activityData.daily_activity}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis
                    dataKey="date"
                    stroke="#6B7280"
                    style={{ fontSize: '12px' }}
                    tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  />
                  <YAxis stroke="#6B7280" style={{ fontSize: '12px' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #E5E7EB',
                      borderRadius: '8px',
                    }}
                    labelFormatter={(value) => new Date(value).toLocaleDateString()}
                  />
                  <Bar dataKey="messages" fill="#8B5CF6" name="Messages" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-400">
                No data available
              </div>
            )}
          </ChartCard>

          {/* Chunk Quality Metrics */}
          <ChartCard title="Chunk Quality" icon={<Icon name="bar-chart" size="md" className="text-pink-500 dark:text-pink-400" />}>
            {insightsData?.chunk_quality ? (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {insightsData.chunk_quality.average_tokens.toFixed(0)}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Avg Tokens</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {insightsData.chunk_quality.total_chunks}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Total Chunks</p>
                  </div>
                </div>
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">Min:</span>
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {insightsData.chunk_quality.min_tokens} tokens
                    </span>
                  </div>
                  <div className="flex justify-between text-sm mt-2">
                    <span className="text-gray-600 dark:text-gray-400">Max:</span>
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {insightsData.chunk_quality.max_tokens} tokens
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-gray-400">
                No data available
              </div>
            )}
          </ChartCard>
        </div>

        {/* Query Performance Analytics */}
        {performanceData?.query_analytics && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ChartCard
              title="Query Performance Analytics"
              icon={<Icon name="trending-up" size="md" className="text-purple-500 dark:text-purple-400" />}
            >
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-xs text-gray-500 dark:text-gray-400">Total Queries</span>
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">
                      {performanceData.query_analytics.total_queries}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500 dark:text-gray-400">Avg Latency</span>
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">
                      {performanceData.query_analytics.avg_latency_ms.toFixed(0)}ms
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500 dark:text-gray-400">P95 Latency</span>
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">
                      {performanceData.query_analytics.p95_latency_ms.toFixed(0)}ms
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500 dark:text-gray-400">Cache Hit Rate</span>
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">
                      {performanceData.query_analytics.cache_hit_rate.toFixed(1)}%
                    </p>
                  </div>
                </div>
                {performanceData.slow_queries && performanceData.slow_queries.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">Slow Queries ({performanceData.slow_queries.length})</p>
                    <div className="space-y-2 max-h-32 overflow-y-auto">
                      {performanceData.slow_queries.slice(0, 3).map((query: any, idx: number) => (
                        <div key={idx} className="text-xs text-gray-600 dark:text-gray-400">
                          <span className="font-medium">{query.latency_ms.toFixed(0)}ms</span>
                          {' - '}
                          <span className="truncate">{query.query.substring(0, 40)}...</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </ChartCard>
            
            {/* Strategy Comparison */}
            {performanceData.strategy_comparison && Object.keys(performanceData.strategy_comparison).length > 0 && (
              <ChartCard
                title="RAG Strategy Comparison"
                icon={<Icon name="bar-chart" size="md" className="text-indigo-500 dark:text-indigo-400" />}
              >
                <div className="space-y-3">
                  {Object.entries(performanceData.strategy_comparison).map(([strategy, stats]: [string, any]) => (
                    <div key={strategy} className="flex justify-between items-center">
                      <div>
                        <span className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                          {strategy.replace('_', ' ')}
                        </span>
                        <p className="text-xs text-gray-500 dark:text-gray-400">{stats.count} queries</p>
                      </div>
                      <div className="text-right">
                        <span className="text-sm font-semibold text-gray-900 dark:text-white">
                          {stats.avg_latency_ms.toFixed(0)}ms
                        </span>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {stats.cache_hit_rate.toFixed(1)}% cache
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </ChartCard>
            )}
          </div>
        )}

        {/* Performance Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            title="Avg Chunks/Doc"
            value={(performanceData?.average_chunks_per_document || 0).toFixed(1)}
            subtitle="Average"
            icon={<Icon name="package" size="lg" className="text-cyan-500 dark:text-cyan-400" />}
          />
          <MetricCard
            title="Total Sessions"
            value={activityData?.total_sessions || 0}
            subtitle="Active"
            icon={<Icon name="message" size="lg" className="text-blue-500 dark:text-blue-400" />}
          />
          <MetricCard
            title="Questions Asked"
            value={activityData?.questions_asked || 0}
            subtitle={`Over ${days} days`}
            icon={<Icon name="question" size="lg" className="text-amber-500 dark:text-amber-400" />}
          />
        </div>
      </div>
    </div>
  );
}

function MetricCard({ title, value, subtitle, icon }: { title: string; value: string | number; subtitle: string; icon: React.ReactNode }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-soft hover-lift transition-all duration-300 hover:shadow-lg">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">{value}</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{subtitle}</p>
        </div>
        <div className="ml-4 flex-shrink-0">{icon}</div>
      </div>
    </div>
  );
}

function ChartCard({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-soft transition-all duration-300 hover:shadow-lg">
      <div className="flex items-center gap-3 mb-4">
        {icon}
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h2>
      </div>
      {children}
    </div>
  );
}

