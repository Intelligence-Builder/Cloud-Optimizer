# 6.5 Chat Interface + Dashboard UI

## Parent Epic
Epic 6: MVP Phase 1 - Container Product Foundation

## Overview

Build the chat-first user interface that enables trial customers to interact with Cloud Optimizer through natural language. The UI provides security Q&A chat, document upload for analysis, trial status display, and basic navigation.

## Background

The MVP uses a **chat-first design** because:
- Trial customers want immediate value (ask a question, get an answer)
- Chat interface is intuitive for security Q&A use case
- Reduces learning curve vs. complex dashboard
- Enables document analysis workflow (upload → ask questions)

## Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|---------------------|
| UI-001 | Chat interface layout | Full-height chat panel, message history, input area with send button |
| UI-002 | Message display | User/assistant bubbles, markdown rendering, code syntax highlighting |
| UI-003 | Streaming responses | SSE-based streaming, typing indicator, progressive text display |
| UI-004 | Document upload | Drag-drop or file picker, PDF/TXT support, upload progress indicator |
| UI-005 | Document context | Show attached documents in chat, reference in responses |
| UI-006 | Trial status banner | Days remaining, usage meters, upgrade CTA |
| UI-007 | Chat history | Persist conversations, list previous chats, resume capability |
| UI-008 | Mobile responsive | Works on tablet/mobile, touch-friendly input |
| UI-009 | Error handling | Connection errors, rate limits, graceful degradation |
| UI-010 | Loading states | Skeleton loaders, progress indicators, button states |

## Technical Specification

### Tech Stack

```yaml
Frontend:
  Framework: React 18 with TypeScript
  Styling: Tailwind CSS
  State: React Context (simple state) + React Query (server state)
  Markdown: react-markdown with remark-gfm
  Code Highlighting: Prism.js or highlight.js
  Icons: Heroicons or Lucide
  Build: Vite

Backend Integration:
  HTTP: Fetch API with error handling
  Streaming: EventSource (SSE)
  Auth: JWT in Authorization header
```

### Component Architecture

```
src/
├── components/
│   ├── chat/
│   │   ├── ChatContainer.tsx      # Main chat layout
│   │   ├── ChatMessage.tsx        # Individual message bubble
│   │   ├── ChatInput.tsx          # Input area with send
│   │   ├── ChatHistory.tsx        # Sidebar conversation list
│   │   ├── StreamingMessage.tsx   # Handles SSE streaming
│   │   └── TypingIndicator.tsx    # "Assistant is typing..."
│   ├── document/
│   │   ├── DocumentUpload.tsx     # Drag-drop file upload
│   │   ├── DocumentList.tsx       # Attached documents
│   │   └── DocumentPreview.tsx    # PDF/text preview
│   ├── trial/
│   │   ├── TrialBanner.tsx        # Top banner with status
│   │   ├── UsageMeters.tsx        # Usage progress bars
│   │   └── UpgradeCTA.tsx         # Marketplace link button
│   ├── layout/
│   │   ├── AppLayout.tsx          # Main app shell
│   │   ├── Sidebar.tsx            # Navigation sidebar
│   │   └── Header.tsx             # Top header with user menu
│   └── common/
│       ├── Button.tsx
│       ├── Input.tsx
│       ├── Modal.tsx
│       ├── Spinner.tsx
│       └── ErrorBoundary.tsx
├── hooks/
│   ├── useChat.ts                 # Chat state and actions
│   ├── useStreaming.ts            # SSE streaming hook
│   ├── useAuth.ts                 # Auth context hook
│   ├── useTrial.ts                # Trial status hook
│   └── useDocuments.ts            # Document management
├── services/
│   ├── api.ts                     # Base API client
│   ├── chatService.ts             # Chat API calls
│   ├── authService.ts             # Auth API calls
│   ├── trialService.ts            # Trial API calls
│   └── documentService.ts         # Document API calls
├── types/
│   ├── chat.ts                    # Chat types
│   ├── auth.ts                    # Auth types
│   └── trial.ts                   # Trial types
└── App.tsx
```

### Chat Message Component

```tsx
// src/components/chat/ChatMessage.tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';

interface ChatMessageProps {
  message: {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    documents?: Document[];
  };
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        {/* Attached documents */}
        {message.documents?.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2">
            {message.documents.map((doc) => (
              <DocumentChip key={doc.id} document={doc} />
            ))}
          </div>
        )}

        {/* Message content with markdown */}
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code({ node, inline, className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || '');
              return !inline && match ? (
                <SyntaxHighlighter
                  language={match[1]}
                  PreTag="div"
                  {...props}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              ) : (
                <code className={className} {...props}>
                  {children}
                </code>
              );
            },
          }}
        >
          {message.content}
        </ReactMarkdown>

        {/* Timestamp */}
        <div
          className={`mt-1 text-xs ${
            isUser ? 'text-blue-200' : 'text-gray-500'
          }`}
        >
          {formatTime(message.timestamp)}
        </div>
      </div>
    </div>
  );
}
```

### Streaming Hook

```tsx
// src/hooks/useStreaming.ts
import { useState, useCallback, useRef } from 'react';

interface UseStreamingOptions {
  onChunk?: (chunk: string) => void;
  onComplete?: (fullText: string) => void;
  onError?: (error: Error) => void;
}

export function useStreaming(options: UseStreamingOptions = {}) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [content, setContent] = useState('');
  const eventSourceRef = useRef<EventSource | null>(null);

  const startStream = useCallback(
    async (url: string, body: object, token: string) => {
      setIsStreaming(true);
      setContent('');

      try {
        // First, POST to initiate the stream
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(body),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const streamId = response.headers.get('X-Stream-ID');

        // Connect to SSE endpoint
        const eventSource = new EventSource(
          `/api/v1/chat/stream/${streamId}`,
        );
        eventSourceRef.current = eventSource;

        let fullContent = '';

        eventSource.onmessage = (event) => {
          const data = JSON.parse(event.data);

          if (data.type === 'chunk') {
            fullContent += data.content;
            setContent(fullContent);
            options.onChunk?.(data.content);
          } else if (data.type === 'done') {
            eventSource.close();
            setIsStreaming(false);
            options.onComplete?.(fullContent);
          } else if (data.type === 'error') {
            eventSource.close();
            setIsStreaming(false);
            options.onError?.(new Error(data.message));
          }
        };

        eventSource.onerror = () => {
          eventSource.close();
          setIsStreaming(false);
          options.onError?.(new Error('Stream connection failed'));
        };
      } catch (error) {
        setIsStreaming(false);
        options.onError?.(error as Error);
      }
    },
    [options],
  );

  const stopStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  return {
    isStreaming,
    content,
    startStream,
    stopStream,
  };
}
```

### Document Upload Component

```tsx
// src/components/document/DocumentUpload.tsx
import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';

interface DocumentUploadProps {
  onUpload: (files: File[]) => Promise<void>;
  maxFiles?: number;
  maxSize?: number; // bytes
}

export function DocumentUpload({
  onUpload,
  maxFiles = 5,
  maxSize = 10 * 1024 * 1024, // 10MB
}: DocumentUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setUploading(true);
      setProgress(0);

      try {
        await onUpload(acceptedFiles);
      } finally {
        setUploading(false);
        setProgress(0);
      }
    },
    [onUpload],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
    },
    maxFiles,
    maxSize,
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
        isDragActive
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-300 hover:border-gray-400'
      }`}
    >
      <input {...getInputProps()} />

      {uploading ? (
        <div className="space-y-2">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-sm text-gray-600">Uploading...</p>
        </div>
      ) : (
        <>
          <DocumentIcon className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-2 text-sm text-gray-600">
            {isDragActive
              ? 'Drop files here...'
              : 'Drag & drop files, or click to select'}
          </p>
          <p className="mt-1 text-xs text-gray-500">
            PDF or TXT, max {maxFiles} files, {formatBytes(maxSize)} each
          </p>
        </>
      )}
    </div>
  );
}
```

### Trial Status Banner

```tsx
// src/components/trial/TrialBanner.tsx
interface TrialBannerProps {
  trial: {
    status: 'active' | 'expired' | 'converted';
    daysRemaining: number;
    usage: {
      scans: { current: number; limit: number };
      chatQuestions: { current: number; limit: number };
      documents: { current: number; limit: number };
    };
  };
}

export function TrialBanner({ trial }: TrialBannerProps) {
  if (trial.status === 'converted') return null;

  const isExpired = trial.status === 'expired';
  const isLow = trial.daysRemaining <= 3;

  return (
    <div
      className={`px-4 py-2 text-sm ${
        isExpired
          ? 'bg-red-600 text-white'
          : isLow
          ? 'bg-yellow-500 text-yellow-900'
          : 'bg-blue-600 text-white'
      }`}
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-4">
          {isExpired ? (
            <span>Trial expired</span>
          ) : (
            <>
              <span>{trial.daysRemaining} days left in trial</span>
              <UsageMeters usage={trial.usage} compact />
            </>
          )}
        </div>

        <a
          href="https://aws.amazon.com/marketplace/pp/xxx"
          target="_blank"
          rel="noopener noreferrer"
          className="px-3 py-1 bg-white text-blue-600 rounded-md text-sm font-medium hover:bg-gray-100"
        >
          Upgrade Now
        </a>
      </div>
    </div>
  );
}
```

### API Service

```typescript
// src/services/chatService.ts
import { api } from './api';

export interface SendMessageRequest {
  conversationId?: string;
  message: string;
  documentIds?: string[];
}

export interface ChatMessage {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant';
  content: string;
  documentIds?: string[];
  createdAt: string;
}

export interface Conversation {
  id: string;
  title: string;
  lastMessage?: string;
  createdAt: string;
  updatedAt: string;
}

export const chatService = {
  async sendMessage(request: SendMessageRequest): Promise<ChatMessage> {
    return api.post('/api/v1/chat/message', request);
  },

  async streamMessage(
    request: SendMessageRequest,
  ): Promise<{ streamId: string }> {
    return api.post('/api/v1/chat/stream', request);
  },

  async getConversations(): Promise<Conversation[]> {
    return api.get('/api/v1/chat/conversations');
  },

  async getConversation(id: string): Promise<ChatMessage[]> {
    return api.get(`/api/v1/chat/conversations/${id}`);
  },

  async deleteConversation(id: string): Promise<void> {
    return api.delete(`/api/v1/chat/conversations/${id}`);
  },
};
```

## API Endpoints (Backend)

```
POST /api/v1/chat/message        # Send message (non-streaming)
POST /api/v1/chat/stream         # Initiate streaming response
GET  /api/v1/chat/stream/:id     # SSE endpoint for streaming
GET  /api/v1/chat/conversations  # List conversations
GET  /api/v1/chat/conversations/:id  # Get conversation messages
DELETE /api/v1/chat/conversations/:id  # Delete conversation

POST /api/v1/documents/upload    # Upload document(s)
GET  /api/v1/documents           # List user's documents
GET  /api/v1/documents/:id       # Get document metadata
DELETE /api/v1/documents/:id     # Delete document
```

## Files to Create

```
frontend/
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── index.html
├── public/
│   └── favicon.ico
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── index.css
    ├── components/           # As shown in architecture
    ├── hooks/
    ├── services/
    ├── types/
    └── utils/
        ├── formatters.ts     # Date, bytes, etc.
        └── constants.ts

src/cloud_optimizer/api/routers/
├── chat.py                   # Chat API endpoints
└── documents.py              # Document upload endpoints

src/cloud_optimizer/services/
├── chat.py                   # Chat service (calls IB)
└── document.py               # Document processing service
```

## Testing Requirements

### Unit Tests (Frontend)
- [ ] `ChatMessage.test.tsx` - Renders user/assistant messages correctly
- [ ] `useStreaming.test.ts` - SSE connection and chunk handling
- [ ] `DocumentUpload.test.tsx` - File validation and upload flow
- [ ] `TrialBanner.test.tsx` - Different trial states

### Integration Tests (Frontend)
- [ ] `Chat.integration.test.tsx` - Full chat flow with MSW mocks
- [ ] `Document.integration.test.tsx` - Upload and reference in chat

### E2E Tests
- [ ] `chat.e2e.test.ts` - Playwright test of full chat flow
- [ ] `document.e2e.test.ts` - Upload PDF, ask question, verify reference

### Backend Tests
- [ ] `test_chat_api.py` - Chat endpoints
- [ ] `test_document_api.py` - Document upload/retrieval
- [ ] `test_streaming.py` - SSE streaming

## Acceptance Criteria Checklist

- [ ] Chat interface loads and displays welcome message
- [ ] User can type message and send (button or Enter key)
- [ ] Assistant response streams progressively (not all at once)
- [ ] Markdown renders correctly (headers, code blocks, lists)
- [ ] Code blocks have syntax highlighting
- [ ] User can drag-drop PDF to upload
- [ ] Uploaded document appears as chip in chat
- [ ] Chat references document content in responses
- [ ] Trial banner shows days remaining and usage
- [ ] Usage meters update after each action
- [ ] Upgrade CTA links to AWS Marketplace
- [ ] Chat history persists across browser refresh
- [ ] Previous conversations accessible from sidebar
- [ ] Works on mobile viewport (responsive)
- [ ] Error states handled gracefully (connection lost, rate limit)
- [ ] 80%+ test coverage on frontend code

## Dependencies

- 6.3 Trial Management (trial status API)
- 6.4 Basic Authentication (auth endpoints)

## Blocked By

- 6.3 Trial Management
- 6.4 Basic Authentication

## Blocks

- 7.1 AWS Account Connection (needs UI for credential input)
- 8.1 NLU Pipeline (backend for chat)

## Estimated Effort

2 weeks

## Labels

`ui`, `frontend`, `chat`, `mvp`, `phase-1`, `P0`

## Design Reference

```
┌────────────────────────────────────────────────────────────────────┐
│  [Logo] Cloud Optimizer        Trial: 12 days │ ████░░ 65% │ [Upgrade] │
├──────────────┬─────────────────────────────────────────────────────┤
│              │                                                      │
│  Conversations│   ┌─────────────────────────────────────────────┐  │
│              │   │ 👤 I have patient data in S3 that goes      │  │
│  • New Chat  │   │    through Glue into Redshift...            │  │
│  • Security  │   │    📎 architecture.pdf                       │  │
│  • Cost...   │   └─────────────────────────────────────────────┘  │
│              │                                                      │
│              │   ┌─────────────────────────────────────────────┐  │
│              │   │ 🤖 Based on your architecture involving PHI │  │
│              │   │    data, here are the key security concerns:│  │
│              │   │                                              │  │
│              │   │    🔴 HIGH PRIORITY - HIPAA Compliance:     │  │
│              │   │    1. S3 Bucket Encryption...               │  │
│              │   └─────────────────────────────────────────────┘  │
│              │                                                      │
│              │   ┌─────────────────────────────────────────────┐  │
│              │   │ Type your message...        [📎] [Send →]   │  │
│              │   └─────────────────────────────────────────────┘  │
└──────────────┴─────────────────────────────────────────────────────┘
```
