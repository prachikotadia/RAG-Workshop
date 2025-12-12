import { useState } from 'react';
import { Icon } from '../common/Icon';
import { DocumentPreview } from './DocumentPreview';

interface SearchResult {
  document_id: number;
  document_title: string;
  chunk_id: number;
  chunk_index: number;
  text: string;
  highlighted_text: string;
  relevance_score: number;
}

interface SearchResultsProps {
  results: SearchResult[];
  query: string;
  onResultClick?: (result: SearchResult) => void;
}

export function SearchResults({ results, query, onResultClick }: SearchResultsProps) {
  const [previewResult, setPreviewResult] = useState<SearchResult | null>(null);

  if (results.length === 0) {
    return (
      <div className="text-center py-8">
        <Icon name="search" size="lg" className="text-gray-400 mx-auto mb-2" />
        <p className="text-gray-500 dark:text-gray-400">No results found</p>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-3">
        {results.map((result) => (
          <div
            key={`${result.document_id}-${result.chunk_index}`}
            className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => {
              if (onResultClick) {
                onResultClick(result);
              } else {
                setPreviewResult(result);
              }
            }}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <Icon name="document" size="sm" className="text-blue-500" />
                  <span className="font-semibold text-gray-900 dark:text-white">
                    {result.document_title}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    Chunk {result.chunk_index + 1}
                  </span>
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                  Relevance: {(result.relevance_score * 100).toFixed(1)}%
                </div>
              </div>
            </div>
            <div
              className="text-sm text-gray-700 dark:text-gray-300 line-clamp-3"
              dangerouslySetInnerHTML={{ __html: result.highlighted_text }}
            />
          </div>
        ))}
      </div>

      {previewResult && (
        <DocumentPreview
          documentId={previewResult.document_id}
          documentTitle={previewResult.document_title}
          chunkIndex={previewResult.chunk_index}
          chunkText={previewResult.text}
          query={query}
          onClose={() => setPreviewResult(null)}
        />
      )}
    </>
  );
}
