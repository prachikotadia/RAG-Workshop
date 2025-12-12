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
    // Login should fail fast - no retries, 10 second timeout
    return api.post<TokenResponse>('/auth/login', { email, password }, {}, false, 10000);
  },

  signup: async (email: string, password: string): Promise<User> => {
    // Signup should also fail fast - no retries, 10 second timeout
    return api.post<User>('/auth/signup', { email, password }, {}, false, 10000);
  },

  getCurrentUser: async (): Promise<User> => {
    return api.get<User>('/auth/me');
  },
};

