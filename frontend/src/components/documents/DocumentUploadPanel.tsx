import { useState, useRef, DragEvent } from 'react';
import { FileIcon } from '../common/FileIcon';
import { LoadingSpinner } from '../common/LoadingSpinner';

interface DocumentUploadPanelProps {
  onUpload: (files: File[]) => Promise<void>;
  isUploading?: boolean;
  acceptedTypes?: string;
}

export function DocumentUploadPanel({
  onUpload,
  isUploading = false,
  acceptedTypes = '.pdf,.txt,.md,.jpg,.jpeg,.png,.gif,.webp,.bmp,.heic,.heif,.tiff,.tif,.svg,.ico',
}: DocumentUploadPanelProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    setSelectedFiles(files);
    handleUpload(files);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files);
      setSelectedFiles(files);
      handleUpload(files);
    }
  };

  const handleUpload = async (files: File[]) => {
    if (files.length > 0 && !isUploading) {
      try {
      await onUpload(files);
        // Clear selected files only after successful upload
      setSelectedFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
        }
      } catch (error) {
        // Keep files selected if upload fails so user can retry
        console.error('Upload failed:', error);
      }
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-soft border border-gray-200 dark:border-gray-700 p-6 mb-6 animate-fade-in">
      <div
        className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all duration-200 ${
          isDragging
            ? 'border-blue-500 dark:border-blue-400 bg-blue-50/50 dark:bg-blue-900/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500'
        } ${isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={acceptedTypes}
          onChange={handleFileSelect}
          className="hidden"
          disabled={isUploading}
        />

        {isUploading ? (
          <div className="flex flex-col items-center relative z-10">
            <LoadingSpinner size="lg" className="mb-4" />
            <p className="text-gray-700 dark:text-gray-300 font-semibold text-lg">
              Uploading and processing files...
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              This may take a moment for images and large documents
            </p>
          </div>
        ) : (
          <>
            <div className="flex justify-center mb-4">
              <div className="p-4 bg-blue-100 dark:bg-blue-900/30 rounded-full">
                <svg
                  className="w-12 h-12 text-blue-600 dark:text-blue-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                  />
                </svg>
              </div>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Drop files here or click to upload
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Maximum file size: 50 MB. Supported formats: PDF, TXT, MD, images (JPG, PNG, GIF, WEBP, etc.), JSON, CSV, DOCX, PPTX
            </p>
            <button
              type="button"
              className="px-6 py-3 bg-blue-500 hover:bg-blue-600 dark:bg-blue-400 dark:hover:bg-blue-500 text-white font-semibold rounded-xl transition-all duration-200 shadow-soft hover:shadow-medium hover-lift"
            >
              Select Files
            </button>
          </>
        )}
      </div>

      {selectedFiles.length > 0 && !isUploading && (
        <div className="mt-4 space-y-2 animate-fade-in">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Selected files:
          </p>
          {selectedFiles.map((file, index) => (
            <div
              key={index}
              className="flex items-center space-x-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600"
            >
              <FileIcon type={file.name} size="sm" />
              <span className="text-sm text-gray-700 dark:text-gray-300 truncate flex-1">
                {file.name}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

