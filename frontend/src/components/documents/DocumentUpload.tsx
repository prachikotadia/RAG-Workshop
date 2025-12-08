import { documentsApi } from '../../api/documents';
import { useApi } from '../../hooks/useApi';
import { DocumentUploadPanel } from './DocumentUploadPanel';

interface DocumentUploadProps {
  onUploadSuccess: () => void;
}

export function DocumentUpload({ onUploadSuccess }: DocumentUploadProps) {
  const uploadApi = useApi(documentsApi.upload);

  const handleUpload = async (files: File[]) => {
    if (files.length === 0) {
      return;
    }

    try {
      const result = await uploadApi.execute(files);
      // Immediately refresh the list after upload
      onUploadSuccess();
      // Also trigger a refresh after a short delay to catch any documents still processing
      setTimeout(() => {
        onUploadSuccess();
      }, 2000);
    } catch (err) {
      // Error is handled by useApi hook
    }
  };

  return (
    <div className="mb-6">
      <DocumentUploadPanel
        onUpload={handleUpload}
        isUploading={uploadApi.loading}
      />
      {uploadApi.error && (
        <div className="mt-4 p-4 glass dark:glass-dark backdrop-blur-sm bg-red-50/90 dark:bg-red-900/30 border border-red-200/50 dark:border-red-800/50 rounded-xl">
          <p className="text-sm text-red-800 dark:text-red-200 font-medium">
            {uploadApi.error}
          </p>
        </div>
      )}
    </div>
  );
}
