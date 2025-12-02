import React, { useState } from 'react';
import { ChatSession } from '../../api/chat';
import { formatRelativeTime, truncateText } from '../../utils/dateUtils';
import clsx from 'clsx';

interface ChatHistoryProps {
  sessions: ChatSession[];
  currentSessionId?: string;
  onSelectSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  onNewChat: () => void;
  isLoading?: boolean;
}

export const ChatHistory: React.FC<ChatHistoryProps> = ({
  sessions,
  currentSessionId,
  onSelectSession,
  onDeleteSession,
  onNewChat,
  isLoading = false,
}) => {
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const handleDeleteClick = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteConfirmId(sessionId);
  };

  const handleConfirmDelete = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    onDeleteSession(sessionId);
    setDeleteConfirmId(null);
  };

  const handleCancelDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteConfirmId(null);
  };

  // Get title from first user message or use fallback
  const getSessionTitle = (session: ChatSession): string => {
    const firstUserMessage = session.messages.find((msg) => msg.role === 'user');
    if (firstUserMessage) {
      return truncateText(firstUserMessage.content, 50);
    }
    return 'New Conversation';
  };

  // Get preview from last message
  const getSessionPreview = (session: ChatSession): string => {
    if (session.messages.length === 0) {
      return 'No messages yet';
    }
    const lastMessage = session.messages[session.messages.length - 1];
    return truncateText(lastMessage.content, 80);
  };

  // Filter sessions based on search query
  const filteredSessions = sessions.filter((session) => {
    if (!searchQuery) return true;
    const title = getSessionTitle(session).toLowerCase();
    const preview = getSessionPreview(session).toLowerCase();
    const query = searchQuery.toLowerCase();
    return title.includes(query) || preview.includes(query);
  });

  // Sort sessions by updated_at (most recent first)
  const sortedSessions = [...filteredSessions].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  );

  return (
    <div className="flex flex-col h-full bg-white border-r border-gray-200">
      {/* Header with New Chat button */}
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={onNewChat}
          className="w-full flex items-center justify-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <svg
            className="w-5 h-5 mr-2"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          New Chat
        </button>
      </div>

      {/* Search bar */}
      <div className="p-4 border-b border-gray-200">
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
          <svg
            className="absolute left-3 top-2.5 w-5 h-5 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
      </div>

      {/* Conversations list */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          // Loading skeleton
          <div className="p-4 space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className="animate-pulse bg-gray-100 rounded-lg p-3 h-20"
              />
            ))}
          </div>
        ) : sortedSessions.length === 0 ? (
          // Empty state
          <div className="flex items-center justify-center h-full p-4 text-center">
            <div>
              <svg
                className="mx-auto h-12 w-12 text-gray-400 mb-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
              <p className="text-sm text-gray-500">
                {searchQuery ? 'No conversations found' : 'No conversations yet'}
              </p>
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="mt-2 text-sm text-primary-600 hover:text-primary-700"
                >
                  Clear search
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="p-2">
            {sortedSessions.map((session) => (
              <div
                key={session.session_id}
                onClick={() => onSelectSession(session.session_id)}
                className={clsx(
                  'group relative p-3 mb-2 rounded-lg cursor-pointer transition-colors',
                  currentSessionId === session.session_id
                    ? 'bg-primary-50 border border-primary-200'
                    : 'hover:bg-gray-50 border border-transparent'
                )}
              >
                {/* Session content */}
                <div className="pr-8">
                  <h3
                    className={clsx(
                      'text-sm font-medium mb-1 line-clamp-1',
                      currentSessionId === session.session_id
                        ? 'text-primary-900'
                        : 'text-gray-900'
                    )}
                  >
                    {getSessionTitle(session)}
                  </h3>
                  <p className="text-xs text-gray-500 line-clamp-2 mb-1">
                    {getSessionPreview(session)}
                  </p>
                  <p className="text-xs text-gray-400">
                    {formatRelativeTime(session.updated_at)}
                  </p>
                </div>

                {/* Delete button */}
                {deleteConfirmId === session.session_id ? (
                  <div className="absolute top-2 right-2 flex items-center space-x-1 bg-white rounded-lg shadow-lg border border-gray-200 p-1">
                    <button
                      onClick={(e) => handleConfirmDelete(session.session_id, e)}
                      className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
                      title="Confirm delete"
                    >
                      Delete
                    </button>
                    <button
                      onClick={handleCancelDelete}
                      className="px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                      title="Cancel"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={(e) => handleDeleteClick(session.session_id, e)}
                    className={clsx(
                      'absolute top-2 right-2 p-1 rounded hover:bg-gray-200 transition-opacity',
                      'opacity-0 group-hover:opacity-100'
                    )}
                    title="Delete conversation"
                  >
                    <svg
                      className="w-4 h-4 text-gray-500 hover:text-red-600"
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
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
