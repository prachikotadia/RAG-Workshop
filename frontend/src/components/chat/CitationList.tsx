import { Citation } from '../../api/chat';

interface CitationListProps {
  citations: Citation[];
}

export function CitationList({ citations }: CitationListProps) {
  if (citations.length === 0) {
    return null;
  }

  return (
    <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-md border border-gray-200 dark:border-gray-600">
      <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-2">
        Sources ({citations.length}):
      </div>
      <div className="space-y-1">
        {citations.map((citation, index) => (
          <div
            key={index}
            className="text-xs text-gray-700 dark:text-gray-300 flex items-start"
          >
            <span className="font-medium mr-2">[{index + 1}]</span>
            <span>
              <span className="font-medium">{citation.document_title}</span>
              {' '}• Chunk {citation.chunk_index}
              {' '}• Score: {citation.score.toFixed(3)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

