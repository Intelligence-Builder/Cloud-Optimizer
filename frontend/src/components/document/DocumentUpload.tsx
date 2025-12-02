import React, { useState, useCallback, useRef } from 'react';
import clsx from 'clsx';
import { documentsApi } from '../../api/documents';

interface DocumentUploadProps {
  onUploadComplete?: () => void;
  maxFiles?: number;
}

interface UploadingFile {
  file: File;
  progress: number;
  status: 'uploading' | 'success' | 'error';
  error?: string;
}

const ALLOWED_TYPES = ['application/pdf', 'text/plain'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB in bytes

export const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onUploadComplete,
  maxFiles = 5,
}) => {
  const [uploadingFiles, setUploadingFiles] = useState<Map<string, UploadingFile>>(
    new Map()
  );
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounter = useRef(0);

  const validateFile = (file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return 'Only PDF and TXT files are allowed';
    }
    if (file.size > MAX_FILE_SIZE) {
      return 'File size must be less than 10MB';
    }
    return null;
  };

  const uploadFile = async (file: File) => {
    const fileId = `${file.name}-${Date.now()}`;

    setUploadingFiles((prev) => {
      const newMap = new Map(prev);
      newMap.set(fileId, {
        file,
        progress: 0,
        status: 'uploading',
      });
      return newMap;
    });

    try {
      await documentsApi.uploadDocument(file, (progress) => {
        setUploadingFiles((prev) => {
          const newMap = new Map(prev);
          const existing = newMap.get(fileId);
          if (existing) {
            newMap.set(fileId, { ...existing, progress });
          }
          return newMap;
        });
      });

      setUploadingFiles((prev) => {
        const newMap = new Map(prev);
        const existing = newMap.get(fileId);
        if (existing) {
          newMap.set(fileId, { ...existing, status: 'success', progress: 100 });
        }
        return newMap;
      });

      // Remove from list after 2 seconds
      setTimeout(() => {
        setUploadingFiles((prev) => {
          const newMap = new Map(prev);
          newMap.delete(fileId);
          return newMap;
        });
      }, 2000);

      if (onUploadComplete) {
        onUploadComplete();
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Upload failed';

      setUploadingFiles((prev) => {
        const newMap = new Map(prev);
        const existing = newMap.get(fileId);
        if (existing) {
          newMap.set(fileId, {
            ...existing,
            status: 'error',
            error: errorMessage,
          });
        }
        return newMap;
      });
    }
  };

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files) return;

      const filesArray = Array.from(files);
      const currentUploading = uploadingFiles.size;

      if (currentUploading + filesArray.length > maxFiles) {
        alert(`You can only upload up to ${maxFiles} files at once`);
        return;
      }

      for (const file of filesArray) {
        const validationError = validateFile(file);
        if (validationError) {
          const fileId = `${file.name}-${Date.now()}`;
          setUploadingFiles((prev) => {
            const newMap = new Map(prev);
            newMap.set(fileId, {
              file,
              progress: 0,
              status: 'error',
              error: validationError,
            });
            return newMap;
          });

          // Remove error after 5 seconds
          setTimeout(() => {
            setUploadingFiles((prev) => {
              const newMap = new Map(prev);
              newMap.delete(fileId);
              return newMap;
            });
          }, 5000);
        } else {
          await uploadFile(file);
        }
      }
    },
    [uploadingFiles.size, maxFiles]
  );

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current++;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current--;
    if (dragCounter.current === 0) {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      dragCounter.current = 0;

      const files = e.dataTransfer.files;
      handleFiles(files);
    },
    [handleFiles]
  );

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      handleFiles(e.target.files);
      // Reset input so same file can be selected again
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    },
    [handleFiles]
  );

  const handleClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={handleClick}
        className={clsx(
          'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all',
          isDragging
            ? 'border-primary-600 bg-primary-50'
            : 'border-gray-300 hover:border-gray-400 bg-gray-50 hover:bg-gray-100'
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt,application/pdf,text/plain"
          onChange={handleFileInputChange}
          className="hidden"
        />

        <div className="flex flex-col items-center space-y-3">
          {/* Upload Icon */}
          <div
            className={clsx(
              'w-12 h-12 rounded-full flex items-center justify-center transition-colors',
              isDragging ? 'bg-primary-600' : 'bg-gray-400'
            )}
          >
            <svg
              className="w-6 h-6 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          </div>

          {/* Text */}
          <div>
            <p className="text-base font-medium text-gray-900">
              {isDragging ? 'Drop files here' : 'Drop files or click to upload'}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              PDF and TXT files only, up to 10MB each
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Maximum {maxFiles} files at once
            </p>
          </div>
        </div>
      </div>

      {/* Uploading Files List */}
      {uploadingFiles.size > 0 && (
        <div className="space-y-2">
          {Array.from(uploadingFiles.entries()).map(([fileId, uploadData]) => (
            <div
              key={fileId}
              className="bg-white border border-gray-200 rounded-lg p-4"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {uploadData.file.name}
                  </p>
                  <p className="text-xs text-gray-500">
                    {(uploadData.file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>

                {/* Status Icon */}
                <div className="ml-4">
                  {uploadData.status === 'uploading' && (
                    <div className="w-5 h-5 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
                  )}
                  {uploadData.status === 'success' && (
                    <svg
                      className="w-5 h-5 text-green-500"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                  )}
                  {uploadData.status === 'error' && (
                    <svg
                      className="w-5 h-5 text-red-500"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  )}
                </div>
              </div>

              {/* Progress Bar */}
              {uploadData.status === 'uploading' && (
                <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-primary-600 h-2 transition-all duration-300"
                    style={{ width: `${uploadData.progress}%` }}
                  />
                </div>
              )}

              {/* Error Message */}
              {uploadData.status === 'error' && uploadData.error && (
                <p className="text-sm text-red-600 mt-1">{uploadData.error}</p>
              )}

              {/* Success Message */}
              {uploadData.status === 'success' && (
                <p className="text-sm text-green-600 mt-1">Upload complete</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
