import { useState } from 'react';
import { documentsApi } from '../../api/documents';
import { useApi } from '../../hooks/useApi';
import { Icon } from '../common/Icon';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { SearchResults } from './SearchResults';

interface DocumentSearchProps {
  documentId?: number; // Optional: search within specific document
}

export function DocumentSearch({ documentId }: DocumentSearchProps) {
  const [query, setQuery] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const searchApi = useApi(() => {
    if (!searchQuery.trim()) return Promise.resolve({ query: '', results: [], total_results: 0 });
    return documentsApi.search(searchQuery, documentId);
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      setSearchQuery(query.trim());
      searchApi.execute();
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 shadow-soft">
      <div className="flex items-center gap-3 mb-4">
        <Icon name="search" size="md" className="text-blue-500 dark:text-blue-400" />
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          {documentId ? 'Search in Document' : 'Search All Documents'}
        </h2>
      </div>

      <form onSubmit={handleSearch} className="mb-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={documentId ? "Search within this document..." : "Search across all documents..."}
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
          />
          <button
            type="submit"
            disabled={!query.trim() || searchApi.loading}
            className="px-6 py-2 bg-blue-500 hover:bg-blue-600 dark:bg-blue-400 dark:hover:bg-blue-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {searchApi.loading ? (
              <LoadingSpinner size="sm" />
            ) : (
              <Icon name="search" size="sm" />
            )}
          </button>
        </div>
      </form>

      {searchQuery && (
        <div>
          {searchApi.loading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner size="lg" />
            </div>
          ) : searchApi.error ? (
            <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-sm text-red-800 dark:text-red-200">
                Error: {searchApi.error}
              </p>
            </div>
          ) : searchApi.data ? (
            <div>
              <div className="mb-4 text-sm text-gray-600 dark:text-gray-400">
                Found {searchApi.data.total_results} result{searchApi.data.total_results !== 1 ? 's' : ''} for "{searchQuery}"
              </div>
              <SearchResults
                results={searchApi.data.results}
                query={searchQuery}
              />
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
