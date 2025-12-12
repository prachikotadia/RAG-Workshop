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
      await uploadApi.execute(files);
      // Immediately refresh the list after upload to show new documents
      onUploadSuccess();
      // Continue refreshing every 2 seconds for up to 30 seconds to catch documents still processing
      let refreshCount = 0;
      const maxRefreshes = 15; // 15 * 2s = 30 seconds
      const refreshInterval = setInterval(() => {
        refreshCount++;
        onUploadSuccess();
        if (refreshCount >= maxRefreshes) {
          clearInterval(refreshInterval);
        }
      }, 2000);
    } catch (err) {
      // Error handled by useApi - will be displayed in the error message below
      console.error('Upload error:', err);
    }
  };

  return (
    <div className="mb-6">
      <DocumentUploadPanel
        onUpload={handleUpload}
        isUploading={uploadApi.loading}
      />
      {uploadApi.error && (
        <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg animate-fade-in">
          <div className="flex items-start space-x-2">
            <svg className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <p className="text-sm font-medium text-red-800 dark:text-red-200">
                Upload Error
              </p>
              <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                {uploadApi.error}
              </p>
              <p className="text-xs text-red-600 dark:text-red-400 mt-2">
                Please check the file format and size, then try again.
                <br />
                <span className="font-medium">Limits:</span> Max 50 MB. Supported: PDF, TXT, MD, images (JPG, PNG, GIF, WEBP, etc.), JSON, CSV, DOCX, PPTX
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
