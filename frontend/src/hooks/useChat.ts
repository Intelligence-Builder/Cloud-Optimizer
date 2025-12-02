import { useState, useRef, useCallback } from 'react';
import { chatApi, Message, ChatStreamClient } from '../api/chat';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

export const useChat = (sessionId: string | undefined) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const streamClientRef = useRef<ChatStreamClient | null>(null);
  const currentSessionIdRef = useRef<string | undefined>(sessionId);

  const loadMessages = useCallback(async (sid: string) => {
    try {
      setIsLoading(true);
      const session = await chatApi.getSession(sid);
      const chatMessages: ChatMessage[] = session.messages.map((msg: Message) => ({
        id: msg.message_id,
        role: msg.role,
        content: msg.content,
        timestamp: new Date(msg.created_at),
      }));
      setMessages(chatMessages);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load messages');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const sendMessage = useCallback(
    (content: string) => {
      // Add user message immediately
      const userMessage: ChatMessage = {
        id: `temp-${Date.now()}`,
        role: 'user',
        content,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);

      // Add assistant message placeholder for streaming
      const assistantMessageId = `streaming-${Date.now()}`;
      const assistantMessage: ChatMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setIsLoading(true);
      setError(null);

      // Initialize stream client
      if (!streamClientRef.current) {
        streamClientRef.current = new ChatStreamClient();
      }

      // Stream the response
      streamClientRef.current.streamMessage(
        content,
        currentSessionIdRef.current,
        // On chunk received
        (chunk: string) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, content: msg.content + chunk }
                : msg
            )
          );
        },
        // On complete
        (messageId: string, sessionId: string) => {
          currentSessionIdRef.current = sessionId;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, id: messageId, isStreaming: false }
                : msg
            )
          );
          setIsLoading(false);
        },
        // On error
        (err: Error) => {
          setError(err.message);
          setIsLoading(false);
          setMessages((prev) => prev.filter((msg) => msg.id !== assistantMessageId));
        }
      );
    },
    []
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    currentSessionIdRef.current = undefined;
  }, []);

  const stopStreaming = useCallback(() => {
    if (streamClientRef.current) {
      streamClientRef.current.close();
    }
    setIsLoading(false);
    setMessages((prev) =>
      prev.map((msg) => (msg.isStreaming ? { ...msg, isStreaming: false } : msg))
    );
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    loadMessages,
    clearMessages,
    stopStreaming,
    currentSessionId: currentSessionIdRef.current,
  };
};
