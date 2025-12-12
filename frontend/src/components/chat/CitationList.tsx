import { useState } from 'react';
import { Citation } from '../../api/chat';
import { DocumentPreview } from '../documents/DocumentPreview';
import { Icon } from '../common/Icon';

interface CitationListProps {
  citations: Citation[];
  query?: string; // Query string for highlighting
}

export function CitationList({ citations, query }: CitationListProps) {
  const [previewCitation, setPreviewCitation] = useState<Citation | null>(null);

  if (citations.length === 0) {
    return null;
  }

  return (
    <>
      <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-md border border-gray-200 dark:border-gray-600">
        <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-2 flex items-center gap-2">
          <Icon name="book" size="xs" className="text-gray-500 dark:text-gray-400" />
          <span>Sources ({citations.length}):</span>
        </div>
        <div className="space-y-1">
          {citations.map((citation, index) => (
            <button
              key={index}
              onClick={() => setPreviewCitation(citation)}
              className="w-full text-left text-xs text-gray-700 dark:text-gray-300 flex items-start hover:bg-gray-100 dark:hover:bg-gray-600 rounded px-2 py-1.5 transition-colors group"
            >
              <span className="font-medium mr-2 text-blue-600 dark:text-blue-400">[{index + 1}]</span>
              <span className="flex-1">
                <span className="font-medium group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                  {citation.document_title}
                </span>
                {' '}• Chunk {citation.chunk_index}
                {' '}• Score: {citation.score.toFixed(3)}
              </span>
              <Icon name="document" size="xs" className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity text-blue-500" />
            </button>
          ))}
        </div>
      </div>

      {previewCitation && (
        <DocumentPreview
          documentId={previewCitation.document_id}
          documentTitle={previewCitation.document_title}
          chunkIndex={previewCitation.chunk_index}
          query={query}
          onClose={() => setPreviewCitation(null)}
        />
      )}
    </>
  );
}

