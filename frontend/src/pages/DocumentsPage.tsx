import React, { useState } from 'react';
import { DocumentUpload } from '../components/document/DocumentUpload';
import { DocumentList } from '../components/document/DocumentList';

export const DocumentsPage: React.FC = () => {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleUploadComplete = () => {
    // Trigger DocumentList refresh
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto p-6 space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
          <p className="text-sm text-gray-600 mt-1">
            Upload and manage your documents for analysis
          </p>
        </div>

        {/* Upload Section */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Upload Documents
          </h2>
          <DocumentUpload onUploadComplete={handleUploadComplete} />
        </div>

        {/* Document List Section */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <DocumentList refreshTrigger={refreshTrigger} />
        </div>
      </div>
    </div>
  );
};
