import React, { useState, useEffect } from 'react';
import clsx from 'clsx';
import { documentsApi, Document } from '../../api/documents';
import { formatDistanceToNow } from 'date-fns';

interface DocumentListProps {
  refreshTrigger?: number;
}

export const DocumentList: React.FC<DocumentListProps> = ({ refreshTrigger }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await documentsApi.listDocuments();
      setDocuments(response.documents);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [refreshTrigger]);

  const handleDelete = async (documentId: string) => {
    if (!confirm('Are you sure you want to delete this document?')) {
      return;
    }

    try {
      setDeletingId(documentId);
      await documentsApi.deleteDocument(documentId);
      setDocuments((prev) => prev.filter((doc) => doc.document_id !== documentId));
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete document');
    } finally {
      setDeletingId(null);
    }
  };

  const getFileIcon = (contentType: string) => {
    if (contentType === 'application/pdf') {
      return (
        <svg
          className="w-5 h-5 text-red-500"
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path
            fillRule="evenodd"
            d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
            clipRule="evenodd"
          />
        </svg>
      );
    }
    return (
      <svg
        className="w-5 h-5 text-gray-500"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path
          fillRule="evenodd"
          d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
          clipRule="evenodd"
        />
      </svg>
    );
  };

  const getStatusBadge = (status: Document['status']) => {
    const styles = {
      pending: 'bg-yellow-100 text-yellow-800',
      processing: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      failed: 'bg-red-100 text-red-800',
    };

    return (
      <span
        className={clsx(
          'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium',
          styles[status]
        )}
      >
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center space-x-2">
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
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="text-sm text-red-800">{error}</p>
        </div>
        <button
          onClick={loadDocuments}
          className="mt-3 text-sm text-red-600 hover:text-red-800 font-medium"
        >
          Try again
        </button>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="text-center py-12">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No documents</h3>
        <p className="mt-1 text-sm text-gray-500">
          Get started by uploading your first document.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Documents ({documents.length})
        </h3>
        <button
          onClick={loadDocuments}
          className="text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          Refresh
        </button>
      </div>

      <div className="space-y-2">
        {documents.map((doc) => (
          <div
            key={doc.document_id}
            className="bg-white border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
          >
            <div className="flex items-start justify-between">
              {/* Document Info */}
              <div className="flex items-start space-x-3 flex-1 min-w-0">
                <div className="mt-0.5">{getFileIcon(doc.content_type)}</div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {doc.filename}
                  </p>
                  <div className="flex items-center space-x-3 mt-1">
                    <span className="text-xs text-gray-500">
                      {formatFileSize(doc.file_size)}
                    </span>
                    <span className="text-xs text-gray-500">
                      {formatDistanceToNow(new Date(doc.created_at), {
                        addSuffix: true,
                      })}
                    </span>
                    {getStatusBadge(doc.status)}
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center space-x-2 ml-4">
                <button
                  onClick={() => handleDelete(doc.document_id)}
                  disabled={deletingId === doc.document_id}
                  className={clsx(
                    'p-1.5 rounded-lg transition-colors',
                    deletingId === doc.document_id
                      ? 'text-gray-400 cursor-not-allowed'
                      : 'text-gray-400 hover:text-red-600 hover:bg-red-50'
                  )}
                  title="Delete document"
                >
                  {deletingId === doc.document_id ? (
                    <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  )}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
