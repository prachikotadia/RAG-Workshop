import { useState } from 'react';
import { DocumentUpload } from '../components/documents/DocumentUpload';
import { DocumentList } from '../components/documents/DocumentList';
import { DocumentSearch } from '../components/documents/DocumentSearch';

export function DocumentsPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [showSearch, setShowSearch] = useState(false);

  const handleUploadSuccess = () => {
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <div className="h-full overflow-y-auto relative">
      <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8 py-4 md:py-8 space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Documents</h1>
          <button
            onClick={() => setShowSearch(!showSearch)}
            className="px-4 py-2 bg-blue-500 hover:bg-blue-600 dark:bg-blue-400 dark:hover:bg-blue-500 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            {showSearch ? 'Hide Search' : 'Full-Text Search'}
          </button>
        </div>

        {showSearch && (
          <DocumentSearch />
        )}

        <DocumentUpload onUploadSuccess={handleUploadSuccess} />
        <DocumentList onRefresh={refreshKey} />
      </div>
    </div>
  );
}
