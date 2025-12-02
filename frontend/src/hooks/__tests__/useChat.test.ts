import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useChat } from '../useChat';
import { chatApi, ChatStreamClient } from '../../api/chat';

// Mock the chat API
vi.mock('../../api/chat', () => ({
  chatApi: {
    getSession: vi.fn(),
  },
  ChatStreamClient: vi.fn(),
}));

describe('useChat', () => {
  const mockSession = {
    session_id: 'session-123',
    user_id: 'user-456',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    messages: [
      {
        message_id: 'msg-1',
        session_id: 'session-123',
        role: 'user' as const,
        content: 'Hello',
        created_at: '2024-01-01T00:00:00Z',
      },
      {
        message_id: 'msg-2',
        session_id: 'session-123',
        role: 'assistant' as const,
        content: 'Hi there!',
        created_at: '2024-01-01T00:01:00Z',
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Initialization', () => {
    it('initializes with empty messages', () => {
      const { result } = renderHook(() => useChat(undefined));

      expect(result.current.messages).toEqual([]);
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it('accepts a session ID on initialization', () => {
      const { result } = renderHook(() => useChat('session-123'));

      expect(result.current.currentSessionId).toBe('session-123');
    });
  });

  describe('Loading Messages', () => {
    it('loads messages from a session', async () => {
      vi.mocked(chatApi.getSession).mockResolvedValue(mockSession);

      const { result } = renderHook(() => useChat(undefined));

      await act(async () => {
        await result.current.loadMessages('session-123');
      });

      expect(chatApi.getSession).toHaveBeenCalledWith('session-123');
      expect(result.current.messages).toHaveLength(2);
      expect(result.current.messages[0].content).toBe('Hello');
      expect(result.current.messages[1].content).toBe('Hi there!');
    });

    it('sets loading state while loading messages', async () => {
      vi.mocked(chatApi.getSession).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockSession), 100))
      );

      const { result } = renderHook(() => useChat(undefined));

      act(() => {
        result.current.loadMessages('session-123');
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });

    it('handles errors when loading messages fails', async () => {
      vi.mocked(chatApi.getSession).mockRejectedValue(
        new Error('Failed to load session')
      );

      const { result } = renderHook(() => useChat(undefined));

      await act(async () => {
        await result.current.loadMessages('session-123');
      });

      expect(result.current.error).toBe('Failed to load session');
      expect(result.current.isLoading).toBe(false);
    });

    it('converts API message format to ChatMessage format', async () => {
      vi.mocked(chatApi.getSession).mockResolvedValue(mockSession);

      const { result } = renderHook(() => useChat(undefined));

      await act(async () => {
        await result.current.loadMessages('session-123');
      });

      const message = result.current.messages[0];
      expect(message.id).toBe('msg-1');
      expect(message.role).toBe('user');
      expect(message.content).toBe('Hello');
      expect(message.timestamp).toBeInstanceOf(Date);
    });
  });

  describe('Sending Messages', () => {
    it('adds user message immediately when sending', () => {
      const mockStreamClient = {
        streamMessage: vi.fn(),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat(undefined));

      act(() => {
        result.current.sendMessage('Hello!');
      });

      expect(result.current.messages).toHaveLength(2); // User + assistant placeholder
      expect(result.current.messages[0].role).toBe('user');
      expect(result.current.messages[0].content).toBe('Hello!');
    });

    it('creates assistant message placeholder for streaming', () => {
      const mockStreamClient = {
        streamMessage: vi.fn(),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat(undefined));

      act(() => {
        result.current.sendMessage('Hello!');
      });

      expect(result.current.messages).toHaveLength(2);
      expect(result.current.messages[1].role).toBe('assistant');
      expect(result.current.messages[1].content).toBe('');
      expect(result.current.messages[1].isStreaming).toBe(true);
    });

    it('initializes ChatStreamClient for streaming', () => {
      const mockStreamClient = {
        streamMessage: vi.fn(),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat(undefined));

      act(() => {
        result.current.sendMessage('Hello!');
      });

      expect(ChatStreamClient).toHaveBeenCalled();
      expect(mockStreamClient.streamMessage).toHaveBeenCalled();
    });

    it('sets loading state while sending message', () => {
      const mockStreamClient = {
        streamMessage: vi.fn(),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat(undefined));

      act(() => {
        result.current.sendMessage('Hello!');
      });

      expect(result.current.isLoading).toBe(true);
    });
  });

  describe('Streaming Messages', () => {
    it('updates assistant message content as chunks arrive', () => {
      let onChunkCallback: ((chunk: string) => void) | undefined;

      const mockStreamClient = {
        streamMessage: vi.fn((message, sessionId, onChunk, onComplete, onError) => {
          onChunkCallback = onChunk;
        }),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat(undefined));

      act(() => {
        result.current.sendMessage('Hello!');
      });

      // Simulate streaming chunks
      act(() => {
        if (onChunkCallback) {
          onChunkCallback('Hello');
        }
      });

      expect(result.current.messages[1].content).toBe('Hello');

      act(() => {
        if (onChunkCallback) {
          onChunkCallback(' there!');
        }
      });

      expect(result.current.messages[1].content).toBe('Hello there!');
    });

    it('marks message as complete when streaming finishes', () => {
      let onCompleteCallback: ((messageId: string, sessionId: string) => void) | undefined;

      const mockStreamClient = {
        streamMessage: vi.fn((message, sessionId, onChunk, onComplete, onError) => {
          onCompleteCallback = onComplete;
        }),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat(undefined));

      act(() => {
        result.current.sendMessage('Hello!');
      });

      expect(result.current.messages[1].isStreaming).toBe(true);

      act(() => {
        if (onCompleteCallback) {
          onCompleteCallback('msg-final', 'session-new');
        }
      });

      expect(result.current.messages[1].isStreaming).toBe(false);
      expect(result.current.messages[1].id).toBe('msg-final');
      expect(result.current.currentSessionId).toBe('session-new');
      expect(result.current.isLoading).toBe(false);
    });

    it('handles streaming errors', () => {
      let onErrorCallback: ((error: Error) => void) | undefined;

      const mockStreamClient = {
        streamMessage: vi.fn((message, sessionId, onChunk, onComplete, onError) => {
          onErrorCallback = onError;
        }),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat(undefined));

      act(() => {
        result.current.sendMessage('Hello!');
      });

      act(() => {
        if (onErrorCallback) {
          onErrorCallback(new Error('Stream failed'));
        }
      });

      expect(result.current.error).toBe('Stream failed');
      expect(result.current.isLoading).toBe(false);
      // Assistant placeholder should be removed on error
      expect(result.current.messages).toHaveLength(1);
      expect(result.current.messages[0].role).toBe('user');
    });

    it('reuses existing stream client if available', () => {
      const mockStreamClient = {
        streamMessage: vi.fn(),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat(undefined));

      act(() => {
        result.current.sendMessage('First message');
      });

      expect(ChatStreamClient).toHaveBeenCalledTimes(1);

      // Simulate completion
      const onComplete = mockStreamClient.streamMessage.mock.calls[0][3];
      act(() => {
        onComplete('msg-1', 'session-1');
      });

      act(() => {
        result.current.sendMessage('Second message');
      });

      // Should reuse the same client, not create new one
      expect(ChatStreamClient).toHaveBeenCalledTimes(1);
      expect(mockStreamClient.streamMessage).toHaveBeenCalledTimes(2);
    });
  });

  describe('Clear Messages', () => {
    it('clears all messages', async () => {
      vi.mocked(chatApi.getSession).mockResolvedValue(mockSession);

      const { result } = renderHook(() => useChat(undefined));

      await act(async () => {
        await result.current.loadMessages('session-123');
      });

      expect(result.current.messages).toHaveLength(2);

      act(() => {
        result.current.clearMessages();
      });

      expect(result.current.messages).toHaveLength(0);
    });

    it('resets current session ID', async () => {
      vi.mocked(chatApi.getSession).mockResolvedValue(mockSession);

      const { result } = renderHook(() => useChat('session-123'));

      await act(async () => {
        await result.current.loadMessages('session-123');
      });

      expect(result.current.currentSessionId).toBe('session-123');

      act(() => {
        result.current.clearMessages();
      });

      expect(result.current.currentSessionId).toBeUndefined();
    });
  });

  describe('Stop Streaming', () => {
    it('closes stream client when stopping', () => {
      const mockStreamClient = {
        streamMessage: vi.fn(),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat(undefined));

      act(() => {
        result.current.sendMessage('Hello!');
      });

      act(() => {
        result.current.stopStreaming();
      });

      expect(mockStreamClient.close).toHaveBeenCalled();
    });

    it('sets loading to false when stopping', () => {
      const mockStreamClient = {
        streamMessage: vi.fn(),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat(undefined));

      act(() => {
        result.current.sendMessage('Hello!');
      });

      expect(result.current.isLoading).toBe(true);

      act(() => {
        result.current.stopStreaming();
      });

      expect(result.current.isLoading).toBe(false);
    });

    it('marks all streaming messages as complete', () => {
      const mockStreamClient = {
        streamMessage: vi.fn(),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat(undefined));

      act(() => {
        result.current.sendMessage('Hello!');
      });

      expect(result.current.messages[1].isStreaming).toBe(true);

      act(() => {
        result.current.stopStreaming();
      });

      expect(result.current.messages[1].isStreaming).toBe(false);
    });

    it('handles stop when no stream is active', () => {
      const { result } = renderHook(() => useChat(undefined));

      // Should not throw error
      act(() => {
        result.current.stopStreaming();
      });

      expect(result.current.isLoading).toBe(false);
    });
  });

  describe('Session Management', () => {
    it('tracks current session ID', () => {
      const { result } = renderHook(() => useChat('initial-session'));

      expect(result.current.currentSessionId).toBe('initial-session');
    });

    it('updates session ID after message completes', () => {
      let onCompleteCallback: ((messageId: string, sessionId: string) => void) | undefined;

      const mockStreamClient = {
        streamMessage: vi.fn((message, sessionId, onChunk, onComplete, onError) => {
          onCompleteCallback = onComplete;
        }),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat(undefined));

      expect(result.current.currentSessionId).toBeUndefined();

      act(() => {
        result.current.sendMessage('Hello!');
      });

      act(() => {
        if (onCompleteCallback) {
          onCompleteCallback('msg-1', 'new-session-id');
        }
      });

      expect(result.current.currentSessionId).toBe('new-session-id');
    });

    it('passes session ID to stream client', () => {
      const mockStreamClient = {
        streamMessage: vi.fn(),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat('existing-session'));

      act(() => {
        result.current.sendMessage('Hello!');
      });

      expect(mockStreamClient.streamMessage).toHaveBeenCalledWith(
        'Hello!',
        'existing-session',
        expect.any(Function),
        expect.any(Function),
        expect.any(Function)
      );
    });
  });

  describe('Error Handling', () => {
    it('clears error state when sending new message', () => {
      let onErrorCallback: ((error: Error) => void) | undefined;

      const mockStreamClient = {
        streamMessage: vi.fn((message, sessionId, onChunk, onComplete, onError) => {
          onErrorCallback = onError;
        }),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat(undefined));

      // Trigger an error
      act(() => {
        result.current.sendMessage('First message');
      });

      act(() => {
        if (onErrorCallback) {
          onErrorCallback(new Error('Stream failed'));
        }
      });

      expect(result.current.error).toBe('Stream failed');

      // Send another message
      act(() => {
        result.current.sendMessage('Second message');
      });

      expect(result.current.error).toBeNull();
    });
  });

  describe('Edge Cases', () => {
    it('handles rapid successive messages', () => {
      const mockStreamClient = {
        streamMessage: vi.fn(),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat(undefined));

      act(() => {
        result.current.sendMessage('Message 1');
        result.current.sendMessage('Message 2');
        result.current.sendMessage('Message 3');
      });

      // Should have 6 messages: 3 user + 3 assistant placeholders
      expect(result.current.messages).toHaveLength(6);
    });

    it('handles empty message content', () => {
      const mockStreamClient = {
        streamMessage: vi.fn(),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat(undefined));

      act(() => {
        result.current.sendMessage('');
      });

      expect(result.current.messages[0].content).toBe('');
      expect(mockStreamClient.streamMessage).toHaveBeenCalledWith(
        '',
        undefined,
        expect.any(Function),
        expect.any(Function),
        expect.any(Function)
      );
    });

    it('generates unique IDs for messages', async () => {
      const mockStreamClient = {
        streamMessage: vi.fn(),
        close: vi.fn(),
      };

      vi.mocked(ChatStreamClient).mockImplementation(() => mockStreamClient as any);

      const { result } = renderHook(() => useChat(undefined));

      act(() => {
        result.current.sendMessage('Message 1');
      });

      // Wait a bit to ensure different timestamps
      await new Promise((resolve) => setTimeout(resolve, 10));

      act(() => {
        result.current.sendMessage('Message 2');
      });

      const ids = result.current.messages.map((m) => m.id);
      const uniqueIds = new Set(ids);

      expect(uniqueIds.size).toBe(ids.length);
    });
  });
});
