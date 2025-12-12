import { api } from './client';
import { Storage } from '../utils/storage';

export interface ChatSession {
  id: number;
  user_id: number;
  title: string | null;
  created_at: string;
}

export interface Citation {
  document_id: number;
  document_title: string;
  chunk_id: number;
  chunk_index: number;
  score: number;
}

export interface ChatMessage {
  id: number;
  session_id: number;
  role: 'user' | 'assistant';
  content: string;
  retrieved_chunks: Citation[];
  created_at: string;
}

export interface CreateSessionRequest {
  title?: string | null;
}

export interface SendMessageRequest {
  content: string;
}

export const chatApi = {
  createSession: async (title?: string): Promise<ChatSession> => {
    return api.post<ChatSession>('/chat/sessions', { title: title || null });
  },

  listSessions: async (): Promise<ChatSession[]> => {
    return api.get<ChatSession[]>('/chat/sessions');
  },

  getSessionMessages: async (sessionId: number): Promise<ChatMessage[]> => {
    // Backend returns messages when GET /chat/sessions/{session_id}
    return api.get<ChatMessage[]>(`/chat/sessions/${sessionId}`);
  },

  sendMessage: async (sessionId: number, content: string): Promise<ChatMessage> => {
    return api.post<ChatMessage>(`/chat/sessions/${sessionId}/message`, { content });
  },

  sendMessageStream: async (
    sessionId: number,
    content: string,
    onToken: (token: string) => void,
    onDone: (citations: Citation[], messageId: number) => void,
    onError: (error: string) => void
  ): Promise<void> => {
    const token = Storage.getToken();
    if (!token) {
      onError('Not authenticated');
      return;
    }

    const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/chat/sessions/${sessionId}/message/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ content }),
    });

    if (!response.ok) {
      onError(`Error: ${response.statusText}`);
      return;
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      onError('Failed to read response stream');
      return;
    }

    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'token') {
              onToken(data.content);
            } else if (data.type === 'done') {
              onDone(data.citations || [], data.message_id);
            } else if (data.type === 'error') {
              onError(data.content);
              return;
            }
          } catch (e) {
            // Skip invalid JSON
          }
        }
      }
    }
  },

  updateSessionTitle: async (sessionId: number, title: string): Promise<ChatSession> => {
    return api.patch<ChatSession>(`/chat/sessions/${sessionId}/title?title=${encodeURIComponent(title)}`);
  },

  deleteSession: async (sessionId: number): Promise<void> => {
    return api.delete(`/chat/sessions/${sessionId}`);
  },

  deleteAllChatHistory: async (): Promise<{ deleted_sessions: number; deleted_messages: number; message: string }> => {
    return api.delete('/chat/sessions/all');
  },

  getQuestionSuggestions: async (sessionId: number): Promise<{ suggestions: string[] }> => {
    return api.get<{ suggestions: string[] }>(`/chat/sessions/${sessionId}/suggestions`);
  },

  createShareLink: async (sessionId: number, expiresInDays?: number): Promise<{ token: string; share_url: string; expires_at: string | null; created_at: string }> => {
    const params = expiresInDays ? `?expires_in_days=${expiresInDays}` : '';
    return api.post<{ token: string; share_url: string; expires_at: string | null; created_at: string }>(`/chat/sessions/${sessionId}/share${params}`);
  },

  getSharedConversation: async (token: string): Promise<any> => {
    // This endpoint doesn't require auth, so we need to handle it specially
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}/chat/shared/${token}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    if (!response.ok) {
      throw new Error(`Failed to load shared conversation: ${response.statusText}`);
    }
    return response.json();
  },

  listShareLinks: async (sessionId: number): Promise<Array<{ token: string; share_url: string; status: string; expires_at: string | null; created_at: string; access_count: number }>> => {
    return api.get<Array<{ token: string; share_url: string; status: string; expires_at: string | null; created_at: string; access_count: number }>>(`/chat/sessions/${sessionId}/share`);
  },

  revokeShareLink: async (sessionId: number, token: string): Promise<void> => {
    return api.delete(`/chat/sessions/${sessionId}/share/${token}`);
  },
};

