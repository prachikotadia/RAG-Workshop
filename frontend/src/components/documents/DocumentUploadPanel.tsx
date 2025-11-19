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
      await onUpload(files);
      setSelectedFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="glass dark:glass-dark backdrop-blur-md bg-white/90 dark:bg-gray-800/90 rounded-2xl shadow-xl border border-gray-200/50 dark:border-gray-700/50 p-6 mb-6">
      <div
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 ${
          isDragging
            ? 'border-blue-500 dark:border-blue-400 bg-blue-50/80 dark:bg-blue-900/30 shadow-lg'
            : 'border-gray-300/80 dark:border-gray-600/80 hover:border-blue-400/80 dark:hover:border-blue-500/80 hover:shadow-md'
        } ${isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover-lift'}`}
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
          <div className="flex flex-col items-center">
            <LoadingSpinner size="lg" className="mb-4" />
            <p className="text-gray-600 dark:text-gray-300 font-medium">
              Uploading documents...
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              Please wait while we process your files
            </p>
          </div>
        ) : (
          <>
            <div className="flex justify-center mb-4">
              <div className="p-4 bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/40 dark:to-purple-900/40 rounded-full shadow-lg">
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
            <h3 className="text-lg font-semibold bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400 bg-clip-text text-transparent mb-2">
              Drop files here or click to upload
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Supports PDF, TXT, MD, and images (JPG, PNG, GIF, WEBP, etc.)
            </p>
            <button
              type="button"
              className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 dark:from-blue-500 dark:to-purple-500 dark:hover:from-blue-600 dark:hover:to-purple-600 text-white font-semibold rounded-xl transition-all duration-300 shadow-lg hover:shadow-xl hover-lift hover-glow transform hover:scale-105 active:scale-95"
            >
              Select Files
            </button>
          </>
        )}
      </div>

      {selectedFiles.length > 0 && !isUploading && (
        <div className="mt-4 space-y-2">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Selected files:
          </p>
          {selectedFiles.map((file, index) => (
            <div
              key={index}
              className="flex items-center space-x-2 p-3 glass dark:glass-dark backdrop-blur-sm bg-white/60 dark:bg-gray-700/60 rounded-lg border border-gray-200/50 dark:border-gray-600/50"
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

