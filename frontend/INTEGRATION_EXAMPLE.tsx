/**
 * INTEGRATION EXAMPLE
 *
 * This file shows how to integrate the DocumentUpload and DocumentList
 * components into your React Router setup.
 *
 * Add this to your main routing file (e.g., App.tsx or router.tsx)
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';

// Import the new Documents page
import { DocumentsPage } from './pages/DocumentsPage';

// Your existing pages
import { LoginPage } from './pages/LoginPage';
import { ChatPage } from './pages/ChatPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected routes with layout */}
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/chat" element={<ChatPage />} />

            {/* NEW: Documents route */}
            <Route path="/documents" element={<DocumentsPage />} />

            <Route path="/" element={<Navigate to="/chat" replace />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

/**
 * NAVIGATION EXAMPLE
 *
 * Add a link to the documents page in your navigation menu.
 * For example, in Layout.tsx:
 */

/*
import { Link, useLocation } from 'react-router-dom';

export const Layout = () => {
  const location = useLocation();

  return (
    <div className="h-screen flex">
      {// Sidebar or navigation
      <nav className="w-64 bg-gray-800 text-white p-4">
        <Link
          to="/chat"
          className={location.pathname === '/chat' ? 'active' : ''}
        >
          Chat
        </Link>

        <Link
          to="/documents"
          className={location.pathname === '/documents' ? 'active' : ''}
        >
          Documents
        </Link>
      </nav>

      {// Main content
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
};
*/

/**
 * STANDALONE USAGE EXAMPLE
 *
 * If you want to use the components individually in an existing page:
 */

/*
import React, { useState } from 'react';
import { DocumentUpload } from '../components/document/DocumentUpload';
import { DocumentList } from '../components/document/DocumentList';

function MyExistingPage() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  return (
    <div className="container mx-auto p-6">
      <h1>My Page</h1>

      {// Upload section
      <section className="my-8">
        <h2>Upload Documents</h2>
        <DocumentUpload
          onUploadComplete={() => setRefreshTrigger(prev => prev + 1)}
          maxFiles={3}  // Optional: customize max files
        />
      </section>

      {// List section
      <section className="my-8">
        <h2>Your Documents</h2>
        <DocumentList refreshTrigger={refreshTrigger} />
      </section>
    </div>
  );
}
*/

/**
 * CHAT INTEGRATION EXAMPLE
 *
 * If you want to show documents within the chat interface:
 */

/*
import React, { useState, useEffect } from 'react';
import { documentsApi, Document } from '../api/documents';
import { DocumentUpload } from '../components/document/DocumentUpload';

function ChatWithDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    const response = await documentsApi.listDocuments();
    setDocuments(response.documents);
  };

  const sendMessageWithContext = async (message: string) => {
    // Include selected document in context
    const context = selectedDoc
      ? `[Using document: ${selectedDoc}] ${message}`
      : message;

    // Send to chat API
  };

  return (
    <div className="flex">
      {// Sidebar with documents
      <aside className="w-64 border-r">
        <DocumentUpload onUploadComplete={loadDocuments} />

        <ul>
          {documents.map(doc => (
            <li
              key={doc.document_id}
              onClick={() => setSelectedDoc(doc.document_id)}
              className={selectedDoc === doc.document_id ? 'selected' : ''}
            >
              {doc.filename}
            </li>
          ))}
        </ul>
      </aside>

      {// Chat interface
      <main className="flex-1">
        {// Your chat component here
      </main>
    </div>
  );
}
*/
