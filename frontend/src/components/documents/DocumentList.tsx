import { useState, useEffect } from 'react';
import { documentsApi } from '../../api/documents';
import { useApi } from '../../hooks/useApi';
import { StatusBadge } from '../common/StatusBadge';
import { FileIcon } from '../common/FileIcon';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ConfirmModal } from '../common/ConfirmModal';
import { Icon } from '../common/Icon';

export function DocumentList({ onRefresh }: { onRefresh?: number }) {
  const listApi = useApi(documentsApi.list);
  const deleteApi = useApi(documentsApi.delete);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<number | null>(null);

  useEffect(() => {
    listApi.execute();
  }, [onRefresh]);

  // Auto-refresh every 3 seconds if there are documents with INDEXING status
  useEffect(() => {
    const hasIndexing = listApi.data?.some(doc => doc.status === 'INDEXING');
    if (hasIndexing) {
      const interval = setInterval(() => {
        listApi.execute();
      }, 3000); // Refresh every 3 seconds while indexing
      return () => clearInterval(interval);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [listApi.data]);

  // Auto-cleanup stuck documents (INDEXING for more than 5 minutes) when component mounts
  useEffect(() => {
    const cleanupStuck = async () => {
      try {
        await documentsApi.cleanupStuck(5);
      } catch (err) {
        // Silently fail - cleanup is best effort
      }
    };
    cleanupStuck();
  }, []);

  const handleDelete = (id: number) => {
    setDocumentToDelete(id);
    setDeleteModalOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (documentToDelete === null) return;

    try {
      setDeletingId(documentToDelete);
      await deleteApi.execute(documentToDelete);
      listApi.execute();
    } catch (err) {
      // Error handled by useApi
    } finally {
      setDeletingId(null);
      setDocumentToDelete(null);
      setDeleteModalOpen(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  if (listApi.loading && !listApi.data) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="text-center">
          <LoadingSpinner size="lg" className="mb-4" />
          <div className="text-gray-500 dark:text-gray-400">Loading documents...</div>
        </div>
      </div>
    );
  }

  if (listApi.error && !listApi.data) {
    const isNetworkError = listApi.error.includes('Network error') || 
                           listApi.error.includes('Could not connect') ||
                           listApi.error.includes('CORS');
    
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <div className="flex items-start space-x-3">
          <svg className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="flex-1">
            <p className="text-sm font-medium text-red-800 dark:text-red-200 mb-2">
              Error loading documents
            </p>
            <p className="text-sm text-red-700 dark:text-red-300 mb-3">
              {listApi.error}
            </p>
            {isNetworkError && (
              <div className="mt-3 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded">
                <p className="text-xs font-medium text-yellow-800 dark:text-yellow-200 mb-1">
                  Quick Fix:
                </p>
                <p className="text-xs text-yellow-700 dark:text-yellow-300 font-mono">
                  bash ensure_backend_running.sh
                </p>
                <button
                  onClick={() => listApi.execute()}
                  className="mt-2 text-xs px-3 py-1 bg-yellow-500 hover:bg-yellow-600 text-white rounded transition-colors"
                >
                  Retry Connection
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  const documents = listApi.data || [];

  if (documents.length === 0) {
    return (
      <div className="text-center py-12 animate-fade-in">
        <div className="bg-white dark:bg-gray-800 rounded-2xl p-8 border border-gray-200 dark:border-gray-700 shadow-soft">
          <div className="mb-4">
            <div className="w-16 h-16 mx-auto bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-full flex items-center justify-center">
              <Icon name="document" size="xl" className="text-blue-500 dark:text-blue-400" />
            </div>
          </div>
          <p className="text-gray-600 dark:text-gray-300 text-base font-medium">
            No documents yet. Upload your first document to get started!
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <ConfirmModal
        isOpen={deleteModalOpen}
        onClose={() => {
          setDeleteModalOpen(false);
          setDocumentToDelete(null);
        }}
        onConfirm={handleConfirmDelete}
        title="Delete Document"
        message="Are you sure you want to delete this document? This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
      />
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-soft border border-gray-200 dark:border-gray-700 overflow-hidden animate-fade-in">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Your Documents ({documents.length})
        </h2>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200/50 dark:divide-gray-700/50">
          <thead className="bg-gray-50/60 dark:bg-gray-900/60 backdrop-blur-sm">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-bold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                Title
              </th>
              <th className="px-6 py-4 text-left text-xs font-bold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-4 text-left text-xs font-bold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                Chunks
              </th>
              <th className="px-6 py-4 text-left text-xs font-bold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-4 text-right text-xs font-bold text-gray-600 dark:text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white/50 dark:bg-gray-800/50 divide-y divide-gray-200/30 dark:divide-gray-700/30">
            {documents.map((doc, index) => (
              <tr 
                key={doc.id} 
                className="hover:bg-gray-50/80 dark:hover:bg-gray-700/50 transition-all duration-300 hover-lift animate-fade-in"
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                <td className="px-6 py-5 whitespace-nowrap">
                  <div className="flex items-center space-x-3">
                    <div className="hover-zoom">
                    <FileIcon type={doc.original_filename} size="sm" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-gray-900 dark:text-white">
                        {doc.title}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400 font-medium">
                        {doc.original_filename}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-5 whitespace-nowrap">
                  <StatusBadge status={doc.status} />
                </td>
                <td className="px-6 py-5 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400 font-semibold">
                  {doc.num_chunks}
                </td>
                <td className="px-6 py-5 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400 font-medium">
                  {formatDate(doc.created_at)}
                </td>
                <td className="px-6 py-5 whitespace-nowrap text-right text-sm font-medium">
                  <button
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingId === doc.id}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700 text-white font-semibold rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover-lift shadow-soft"
                  >
                    {deletingId === doc.id ? (
                      <>
                        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        <span>Deleting...</span>
                      </>
                    ) : (
                      <>
                        <Icon name="trash" size="sm" className="text-white" />
                        <span>Delete</span>
                      </>
                    )}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
    </>
  );
}

