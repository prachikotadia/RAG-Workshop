import { api } from './client';

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

  updateSessionTitle: async (sessionId: number, title: string): Promise<ChatSession> => {
    return api.patch<ChatSession>(`/chat/sessions/${sessionId}/title?title=${encodeURIComponent(title)}`);
  },

  deleteSession: async (sessionId: number): Promise<void> => {
    return api.delete(`/chat/sessions/${sessionId}`);
  },

  deleteAllChatHistory: async (): Promise<{ deleted_sessions: number; deleted_messages: number; message: string }> => {
    return api.delete('/chat/sessions/all');
  },
};

