import { api } from './client';

export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export const authApi = {
  login: async (email: string, password: string): Promise<TokenResponse> => {
    return api.post<TokenResponse>('/auth/login', { email, password });
  },

  signup: async (email: string, password: string): Promise<User> => {
    return api.post<User>('/auth/signup', { email, password });
  },

  getCurrentUser: async (): Promise<User> => {
    return api.get<User>('/auth/me');
  },
};

