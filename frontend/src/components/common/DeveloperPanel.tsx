import { useState } from 'react';
import { api } from '../../api/client';

interface DeveloperPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function DeveloperPanel({ isOpen, onClose }: DeveloperPanelProps) {
  const [metrics, setMetrics] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadMetrics = async () => {
    setLoading(true);
    try {
      const [metricsData, healthData] = await Promise.all([
        api.get('/admin/metrics/json'),
        api.get('/health'),
      ]);
      setMetrics(metricsData);
      setHealth(healthData);
    } catch (error) {
      console.error('Failed to load debug data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-4xl mx-4 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 max-h-[90vh] overflow-hidden flex flex-col">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Developer Panel</h2>
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
          >
            ✕
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4">
          <div className="mb-4">
            <button
              onClick={loadMetrics}
              disabled={loading}
              className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg disabled:opacity-50"
            >
              {loading ? 'Loading...' : 'Load Debug Data'}
            </button>
          </div>
          
          {health && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Health Status</h3>
              <pre className="bg-gray-100 dark:bg-gray-900 p-4 rounded-lg overflow-x-auto text-sm">
                {JSON.stringify(health, null, 2)}
              </pre>
            </div>
          )}
          
          {metrics && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Metrics</h3>
              <pre className="bg-gray-100 dark:bg-gray-900 p-4 rounded-lg overflow-x-auto text-sm">
                {JSON.stringify(metrics, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

