import { useState, useEffect } from 'react';
import { Icon } from '../common/Icon';
import { documentsApi } from '../../api/documents';

interface DocumentPreviewProps {
  documentId: number;
  documentTitle: string;
  chunkText?: string;
  chunkIndex?: number;
  query?: string; // Query string for highlighting
  onClose: () => void;
}

export function DocumentPreview({
  documentId,
  documentTitle,
  chunkText: initialChunkText,
  chunkIndex,
  query,
  onClose,
}: DocumentPreviewProps) {
  const [chunkData, setChunkData] = useState<{
    text: string;
    highlighted_text?: string;
    token_count?: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isImage, setIsImage] = useState(false);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  useEffect(() => {
    const fetchChunk = async () => {
      if (chunkIndex === undefined) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        
        const data = await documentsApi.getChunkContent(documentId, chunkIndex, query);
        setChunkData(data);
        
        // Check if document is an image
        const metadata = data.metadata || {};
        if (metadata.file_type === 'image' || metadata.source_path) {
          setIsImage(true);
          // Construct image URL
          const imageUrl = `${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}/documents/${documentId}/file`;
          setImageUrl(imageUrl);
        }
      } catch (err: any) {
        setError(err?.detail || 'Failed to load chunk content');
        // Fallback to initial chunk text if available
        if (initialChunkText) {
          setChunkData({ text: initialChunkText });
        }
      } finally {
        setLoading(false);
      }
    };

    fetchChunk();
  }, [documentId, chunkIndex, query, initialChunkText]);

  const displayText = chunkData?.highlighted_text || chunkData?.text || initialChunkText || '';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-4xl bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
          <div className="flex items-center gap-3">
            <Icon name="document" size="md" className="text-blue-500 dark:text-blue-400" />
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-white">{documentTitle}</h3>
              {chunkIndex !== undefined && (
                <p className="text-sm text-gray-500 dark:text-gray-400">Chunk {chunkIndex + 1}</p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
            aria-label="Close preview"
          >
            <Icon name="x" size="sm" className="text-gray-600 dark:text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p className="text-gray-500 dark:text-gray-400">Loading preview...</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <p className="text-red-500 dark:text-red-400 mb-2">{error}</p>
                {displayText && (
                  <div className="mt-4 prose dark:prose-invert max-w-none">
                    <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                      <p className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed">
                        {displayText}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : isImage && imageUrl ? (
            <div className="flex flex-col items-center justify-center">
              <img
                src={imageUrl}
                alt={documentTitle}
                className="max-w-full max-h-[60vh] rounded-lg shadow-lg object-contain"
              />
              {displayText && (
                <div className="mt-4 w-full prose dark:prose-invert max-w-none">
                  <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-2 font-semibold">Image Description:</p>
                    <p
                      className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed"
                      dangerouslySetInnerHTML={{ __html: displayText }}
                    />
                  </div>
                </div>
              )}
            </div>
          ) : displayText ? (
            <div className="prose dark:prose-invert max-w-none">
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <p
                  className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed"
                  dangerouslySetInnerHTML={{ __html: displayText }}
                />
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64">
              <p className="text-gray-500 dark:text-gray-400">Preview not available</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Document ID: {documentId}
            </p>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-blue-500 hover:bg-blue-600 dark:bg-blue-400 dark:hover:bg-blue-500 text-white rounded-lg font-medium transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
