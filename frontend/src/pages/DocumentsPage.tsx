import { useState } from 'react';
import { DocumentUpload } from '../components/documents/DocumentUpload';
import { DocumentList } from '../components/documents/DocumentList';

export function DocumentsPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleUploadSuccess = () => {
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <div className="h-full overflow-y-auto bg-gradient-to-br from-slate-50 via-blue-50/20 to-indigo-50/20 dark:from-slate-900 dark:via-indigo-950/30 dark:to-slate-900">
      <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8 py-4 md:py-8">
        <DocumentUpload onUploadSuccess={handleUploadSuccess} />
        <DocumentList onRefresh={refreshKey} />
      </div>
    </div>
  );
}
