import React, { useState, useEffect } from 'react';
import { ChatContainer } from '../components/chat/ChatContainer';
import { ChatHistory } from '../components/chat/ChatHistory';
import { Sidebar } from '../components/layout/Sidebar';
import { chatApi, ChatSession } from '../api/chat';

export const Chat: React.FC = () => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | undefined>(undefined);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);

  // Load sessions on mount
  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setIsLoadingSessions(true);
      const fetchedSessions = await chatApi.getSessions();
      setSessions(fetchedSessions);
    } catch (error) {
      console.error('Failed to load chat sessions:', error);
    } finally {
      setIsLoadingSessions(false);
    }
  };

  const handleSelectSession = (sessionId: string) => {
    setCurrentSessionId(sessionId);
    setIsSidebarOpen(false); // Close sidebar on mobile after selection
  };

  const handleNewChat = () => {
    setCurrentSessionId(undefined);
    setIsSidebarOpen(false); // Close sidebar on mobile after starting new chat
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await chatApi.deleteSession(sessionId);
      setSessions(sessions.filter((s) => s.session_id !== sessionId));

      // If the deleted session was the current one, clear it
      if (currentSessionId === sessionId) {
        setCurrentSessionId(undefined);
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  return (
    <div className="h-full flex">
      {/* Sidebar with chat history */}
      <Sidebar isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)}>
        <ChatHistory
          sessions={sessions}
          currentSessionId={currentSessionId}
          onSelectSession={handleSelectSession}
          onDeleteSession={handleDeleteSession}
          onNewChat={handleNewChat}
          isLoading={isLoadingSessions}
        />
      </Sidebar>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col h-full">
        {/* Mobile header with hamburger menu */}
        <div className="lg:hidden flex items-center justify-between p-4 border-b border-gray-200 bg-white">
          <button
            onClick={toggleSidebar}
            className="p-2 rounded-lg hover:bg-gray-100"
            aria-label="Toggle sidebar"
          >
            <svg
              className="w-6 h-6 text-gray-700"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
          <h2 className="text-lg font-semibold text-gray-900">Chat</h2>
          <div className="w-10" /> {/* Spacer for centering */}
        </div>

        {/* Desktop toggle button */}
        <div className="hidden lg:block absolute top-4 left-4 z-10">
          <button
            onClick={toggleSidebar}
            className="p-2 rounded-lg bg-white border border-gray-200 hover:bg-gray-50 shadow-sm"
            aria-label="Toggle sidebar"
          >
            <svg
              className="w-5 h-5 text-gray-700"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
        </div>

        {/* Chat container */}
        <div className="flex-1">
          <ChatContainer sessionId={currentSessionId} />
        </div>
      </div>
    </div>
  );
};
