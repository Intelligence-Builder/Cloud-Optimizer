import React, { useEffect, useRef } from 'react';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { useChat, ChatMessage as ChatMessageType } from '../../hooks/useChat';

interface ChatContainerProps {
  sessionId?: string;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({ sessionId }) => {
  const {
    messages,
    isLoading,
    error,
    sendMessage,
    loadMessages,
    stopStreaming,
  } = useChat(sessionId);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  // Load messages when session changes
  useEffect(() => {
    if (sessionId) {
      loadMessages(sessionId);
    }
  }, [sessionId, loadMessages]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto bg-gray-50 p-4"
      >
        <div className="max-w-4xl mx-auto">
          {/* Welcome message */}
          {messages.length === 0 && !isLoading && (
            <div className="flex items-center justify-center h-full text-center">
              <div>
                <svg
                  className="mx-auto h-12 w-12 text-gray-400 mb-4"
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
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Start a Conversation
                </h3>
                <p className="text-gray-500">
                  Ask me anything about your cloud infrastructure, security, or optimization
                  strategies.
                </p>
              </div>
            </div>
          )}

          {/* Error banner */}
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-start">
                <svg
                  className="h-5 w-5 text-red-400 mt-0.5 mr-2"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-red-800">Error</h3>
                  <p className="text-sm text-red-700 mt-1">{error}</p>
                </div>
                {isLoading && (
                  <button
                    onClick={stopStreaming}
                    className="ml-3 text-sm font-medium text-red-600 hover:text-red-500"
                  >
                    Stop
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Messages list */}
          {messages.map((message: ChatMessageType) => (
            <ChatMessage
              key={message.id}
              role={message.role}
              content={message.content}
              timestamp={message.timestamp}
              isStreaming={message.isStreaming}
            />
          ))}

          {/* Loading indicator */}
          {isLoading && messages.length === 0 && (
            <div className="flex justify-center py-8">
              <div className="flex items-center space-x-2 text-gray-500">
                <svg
                  className="animate-spin h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                <span>Loading messages...</span>
              </div>
            </div>
          )}

          {/* Scroll anchor */}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <ChatInput onSendMessage={sendMessage} isLoading={isLoading} />
    </div>
  );
};
