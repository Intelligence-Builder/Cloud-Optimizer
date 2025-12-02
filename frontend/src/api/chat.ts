import apiClient from './client';

export interface Message {
  message_id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ChatSession {
  session_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

export interface SendMessageRequest {
  session_id?: string;
  message: string;
}

export interface SendMessageResponse {
  message_id: string;
  session_id: string;
  response: string;
}

export const chatApi = {
  getSessions: async (): Promise<ChatSession[]> => {
    const response = await apiClient.get('/chat/sessions');
    return response.data;
  },

  getSession: async (sessionId: string): Promise<ChatSession> => {
    const response = await apiClient.get(`/chat/sessions/${sessionId}`);
    return response.data;
  },

  createSession: async (): Promise<ChatSession> => {
    const response = await apiClient.post('/chat/sessions');
    return response.data;
  },

  sendMessage: async (data: SendMessageRequest): Promise<SendMessageResponse> => {
    const response = await apiClient.post('/chat/message', data);
    return response.data;
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/chat/sessions/${sessionId}`);
  },
};

// SSE streaming for chat messages
export class ChatStreamClient {
  private eventSource: EventSource | null = null;

  constructor() {
    // Token is retrieved from localStorage when needed
  }

  streamMessage(
    message: string,
    sessionId: string | undefined,
    onChunk: (chunk: string) => void,
    onComplete: (messageId: string, sessionId: string) => void,
    onError: (error: Error) => void
  ): void {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api/v1';
    const params = new URLSearchParams();
    params.append('message', message);
    if (sessionId) {
      params.append('session_id', sessionId);
    }

    const url = `${baseUrl}/chat/stream?${params.toString()}`;

    this.eventSource = new EventSource(url);

    this.eventSource.addEventListener('message', (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'chunk') {
          onChunk(data.content);
        } else if (data.type === 'done') {
          onComplete(data.message_id, data.session_id);
          this.close();
        } else if (data.type === 'error') {
          onError(new Error(data.error));
          this.close();
        }
      } catch (err) {
        onError(err instanceof Error ? err : new Error('Failed to parse stream data'));
        this.close();
      }
    });

    this.eventSource.addEventListener('error', () => {
      onError(new Error('Stream connection error'));
      this.close();
    });
  }

  close(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
