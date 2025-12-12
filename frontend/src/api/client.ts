// API client for backend communication

import { retry, RetryOptions } from '../utils/retry';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export interface ApiError {
  detail: string | { [key: string]: any };
  status?: number;
}

class ApiClient {
  public baseUrl: string; // Made public for useConnectionState
  private retryOptions: RetryOptions;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.retryOptions = {
      maxRetries: 3,
      initialDelay: 1000,
      maxDelay: 10000,
      backoffMultiplier: 2,
      retryable: (error: any) => {
        // Retry on network errors or 5xx server errors
        if (error?.status === 0 || (error?.status >= 500 && error?.status < 600)) {
          return true;
        }
        // Retry on rate limit (429)
        if (error?.status === 429) {
          return true;
        }
        return false;
      },
    };
  }

  private getAuthToken(): string | null {
    // Try to get from localStorage first (for backward compatibility)
    return localStorage.getItem('access_token') || null;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    useRetry: boolean = true,
    timeout: number = 30000,
    silent: boolean = false
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const makeRequest = async (): Promise<T> => {
      const token = this.getAuthToken();

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(options.headers as Record<string, string> || {}),
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // Add timeout using AbortController
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);
      
      // Merge with existing signal if present
      if (options.signal) {
        options.signal.addEventListener('abort', () => controller.abort());
      }

      const config: RequestInit = {
        ...options,
        headers: headers as HeadersInit,
        credentials: 'include' as RequestCredentials,
        mode: 'cors' as RequestMode,
        signal: controller.signal,
      };

      let response: Response;
      try {
        response = await fetch(url, config);
        clearTimeout(timeoutId);
      } catch (error: any) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
          throw {
            detail: `Request timeout after ${timeout / 1000} seconds. Please check your connection and try again.`,
            status: 0,
          } as ApiError;
        }
        // Re-throw network errors to be caught by outer handler
        if (error instanceof TypeError || error.message === 'Failed to fetch') {
          throw error;
        }
        throw error;
      }

      // Handle empty responses (e.g., 204 No Content)
      if (response.status === 204) {
        return null as T;
      }

      const contentType = response.headers.get('content-type');
      const isJson = contentType && contentType.includes('application/json');

      if (!response.ok) {
        let errorDetail: string | object = 'An error occurred';
        
        if (isJson) {
          try {
            const errorData = await response.json();
            errorDetail = errorData.detail || errorData.message || errorData;
          } catch {
            errorDetail = `HTTP ${response.status}: ${response.statusText}`;
          }
        } else {
          errorDetail = await response.text() || `HTTP ${response.status}: ${response.statusText}`;
        }

        const error: ApiError = {
          detail: errorDetail,
          status: response.status,
        };

        // Handle 401 Unauthorized - clear token (but don't redirect during login/signup)
        // Only redirect if we're not on the login page
        if (response.status === 401) {
          localStorage.removeItem('access_token');
          // Clear session data
          try {
            const sessionData = localStorage.getItem('rag_workspace_session_data');
            if (sessionData) {
              localStorage.removeItem('rag_workspace_session_data');
            }
          } catch (e) {
            // Ignore errors
          }
          // Only redirect if not already on login page
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
        }

        throw error;
      }

      if (isJson) {
        return await response.json();
      }

      return (await response.text()) as T;
    };

    try {
      // Use retry logic for network errors and server errors
      if (useRetry) {
        return await retry(makeRequest, this.retryOptions);
      } else {
        return await makeRequest();
      }
    } catch (error) {
      // Handle network errors (including CORS errors)
      if (error instanceof TypeError || error instanceof Error) {
        const errorMsg = error.message || String(error);
        const isNetworkError = errorMsg === 'Failed to fetch' || 
                             errorMsg.includes('CORS') ||
                             errorMsg.includes('network') ||
                             errorMsg.includes('NetworkError') ||
                             errorMsg.includes('Network request failed') ||
                             errorMsg.includes('ERR_INTERNET_DISCONNECTED') ||
                             errorMsg.includes('ERR_CONNECTION_REFUSED');
        
        if (isNetworkError) {
          if (!silent) {
            console.error('Network/CORS error:', {
              url,
              baseUrl: this.baseUrl,
              endpoint,
              error: errorMsg,
            });
          }
          // More helpful error message
          let errorMessage = `Network error: Could not connect to the server at ${this.baseUrl}.`;
          errorMessage += ` Make sure the backend is running on port 8000.`;
          errorMessage += ` Run: bash ensure_backend_running.sh`;
          
          throw {
            detail: errorMessage,
            status: 0,
          } as ApiError;
        }
      }
      
      // Ensure error.detail is always a string
      if (error && typeof error === 'object' && 'detail' in error) {
        if (typeof error.detail !== 'string') {
          error.detail = typeof error.detail === 'object' 
            ? JSON.stringify(error.detail) 
            : String(error.detail);
        }
      }
      // Only log errors if not silent (silent mode for health checks, etc.)
      if (!silent) {
        console.error('API request error:', {
          url,
          error,
          endpoint,
        });
      }
      throw error;
    }
  }

  async get<T>(endpoint: string, options?: RequestInit, useRetry: boolean = true, timeout: number = 30000, silent: boolean = false): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' }, useRetry, timeout, silent);
  }

  async post<T>(endpoint: string, data?: any, options?: RequestInit, useRetry: boolean = true, timeout: number = 30000): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }, useRetry, timeout);
  }

  async put<T>(endpoint: string, data?: any, options?: RequestInit, useRetry: boolean = true): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }, useRetry);
  }

  async delete<T>(endpoint: string, options?: RequestInit, useRetry: boolean = true): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' }, useRetry);
  }

  async patch<T>(endpoint: string, data?: any, options?: RequestInit, useRetry: boolean = true): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    }, useRetry);
  }

  async postFormData<T>(endpoint: string, formData: FormData): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const token = this.getAuthToken();

    const headers: Record<string, string> = {};

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Create AbortController for timeout (70 seconds to allow full processing)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 70000); // 70 seconds (backend max is 60s, allow buffer)

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: headers as HeadersInit,
        body: formData,
        credentials: 'include', // Required for CORS with credentials
        mode: 'cors', // Explicitly enable CORS
        signal: controller.signal, // Add abort signal for timeout
      });
      
      clearTimeout(timeoutId);

      if (!response.ok) {
        let errorDetail: string | object = 'An error occurred';
        
        try {
          const errorData = await response.json();
          errorDetail = errorData.detail || errorData.message || errorData;
        } catch {
          errorDetail = `HTTP ${response.status}: ${response.statusText}`;
        }

        const error: ApiError = {
          detail: errorDetail,
          status: response.status,
        };

        if (response.status === 401) {
          localStorage.removeItem('access_token');
          // Clear session data
          try {
            localStorage.removeItem('rag_workspace_session_data');
          } catch (e) {
            // Ignore errors
          }
          window.location.href = '/login';
        }

        throw error;
      }

      return await response.json();
    } catch (error: any) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw {
          detail: 'Upload timeout after 70 seconds. The document may still be processing in the background. Please refresh the page to check status.',
          status: 0,
        } as ApiError;
      }
      throw error;
    }
  }
}

export const api = new ApiClient(API_BASE_URL);

