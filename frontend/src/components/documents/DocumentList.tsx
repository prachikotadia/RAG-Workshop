import { useState, useEffect } from 'react';
import { documentsApi } from '../../api/documents';
import { useApi } from '../../hooks/useApi';
import { StatusBadge } from '../common/StatusBadge';
import { FileIcon } from '../common/FileIcon';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ConfirmModal } from '../common/ConfirmModal';

export function DocumentList({ onRefresh }: { onRefresh?: number }) {
  const listApi = useApi(documentsApi.list);
  const deleteApi = useApi(documentsApi.delete);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<number | null>(null);

  useEffect(() => {
    listApi.execute();
  }, [onRefresh]);

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
    return (
      <div className="p-4 glass dark:glass-dark backdrop-blur-sm bg-red-50/90 dark:bg-red-900/30 border border-red-200/50 dark:border-red-800/50 rounded-xl">
        <p className="text-sm text-red-800 dark:text-red-200">
          Error loading documents: {listApi.error}
        </p>
      </div>
    );
  }

  const documents = listApi.data || [];

  if (documents.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="glass dark:glass-dark backdrop-blur-sm bg-white/60 dark:bg-gray-800/60 rounded-2xl p-8 border border-gray-200/50 dark:border-gray-700/50">
          <p className="text-gray-600 dark:text-gray-300 text-lg">
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
      <div className="glass dark:glass-dark backdrop-blur-md bg-white/90 dark:bg-gray-800/90 rounded-2xl shadow-xl border border-gray-200/50 dark:border-gray-700/50 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200/50 dark:border-gray-700/50 bg-gradient-to-r from-blue-50/50 to-purple-50/50 dark:from-blue-900/20 dark:to-purple-900/20">
        <h2 className="text-xl font-semibold bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400 bg-clip-text text-transparent">
          Your Documents ({documents.length})
        </h2>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50/80 dark:bg-gray-900/80 backdrop-blur-sm">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Title
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Chunks
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {documents.map((doc) => (
              <tr key={doc.id} className="hover:bg-gray-50/80 dark:hover:bg-gray-700/50 transition-colors duration-200">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center space-x-2">
                    <FileIcon type={doc.original_filename} size="sm" />
                    <div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {doc.title}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {doc.original_filename}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <StatusBadge status={doc.status} />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {doc.num_chunks}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                  {formatDate(doc.created_at)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button
                    onClick={() => handleDelete(doc.id)}
                    disabled={deletingId === doc.id}
                    className="px-4 py-2 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 dark:from-red-500 dark:to-red-600 dark:hover:from-red-600 dark:hover:to-red-700 text-white font-medium rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover-lift shadow-md hover:shadow-lg"
                  >
                    {deletingId === doc.id ? 'Deleting...' : 'Delete'}
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

