import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { formatDistanceToNow } from 'date-fns';
import clsx from 'clsx';
import 'highlight.js/styles/github-dark.css';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  role,
  content,
  timestamp,
  isStreaming = false,
}) => {
  const isUser = role === 'user';

  return (
    <div className={clsx('flex w-full mb-4', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={clsx(
          'chat-message',
          isUser ? 'chat-message-user' : 'chat-message-assistant',
          'relative'
        )}
      >
        {/* Role indicator */}
        <div className="flex items-center mb-2">
          <div
            className={clsx(
              'w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold mr-2',
              isUser ? 'bg-primary-700' : 'bg-gray-600 text-white'
            )}
          >
            {isUser ? 'U' : 'AI'}
          </div>
          <span className={clsx('text-xs', isUser ? 'text-primary-100' : 'text-gray-500')}>
            {formatDistanceToNow(timestamp, { addSuffix: true })}
          </span>
        </div>

        {/* Message content */}
        {isUser ? (
          <div className="whitespace-pre-wrap">{content}</div>
        ) : (
          <div className="markdown-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
              {content}
            </ReactMarkdown>
            {isStreaming && (
              <span className="inline-block w-2 h-4 bg-gray-400 ml-1 animate-pulse" />
            )}
          </div>
        )}
      </div>
    </div>
  );
};
