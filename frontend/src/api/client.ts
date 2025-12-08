/**
 * API client for communicating with the FastAPI backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export interface ApiError {
  detail: string | { [key: string]: any };
  status?: number;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
  }

  private getAuthToken(): string | null {
    return localStorage.getItem('access_token');
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const token = this.getAuthToken();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const config: RequestInit = {
      ...options,
      headers: headers as HeadersInit,
      // CRITICAL: Always include credentials and CORS mode for CORS to work properly
      credentials: 'include' as RequestCredentials,
      mode: 'cors' as RequestMode,
    };

    try {
      const response = await fetch(url, config);

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
    } catch (error) {
      // Handle network errors (including CORS errors)
      if (error instanceof TypeError) {
        const isCorsError = error.message === 'Failed to fetch' || 
                           error.message.includes('CORS') ||
                           error.message.includes('network');
        
        if (isCorsError) {
          console.error('Network/CORS error:', {
            url,
            baseUrl: this.baseUrl,
            endpoint,
            error: error.message,
          });
          throw {
            detail: `Network error: Could not connect to the server at ${this.baseUrl}. This may be a CORS issue. Make sure the backend is running on port 8000 and CORS is properly configured.`,
            status: 0,
          } as ApiError;
        }
      }
      console.error('API request error:', {
        url,
        error,
        endpoint,
      });
      throw error;
    }
  }

  async get<T>(endpoint: string, options?: RequestInit): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  async post<T>(endpoint: string, data?: any, options?: RequestInit): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data?: any, options?: RequestInit): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string, options?: RequestInit): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }

  async patch<T>(endpoint: string, data?: any, options?: RequestInit): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async postFormData<T>(endpoint: string, formData: FormData): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const token = this.getAuthToken();

    const headers: Record<string, string> = {};

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Create AbortController for timeout (45 seconds for fast processing)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000); // 45 seconds (backend max is 30s, but allow buffer)

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
          window.location.href = '/login';
        }

        throw error;
      }

      return await response.json();
    } catch (error: any) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw {
          detail: 'Request timeout after 45 seconds. The document may still be processing. Please refresh the page to check status.',
          status: 0,
        } as ApiError;
      }
      throw error;
    }
  }
}

export const api = new ApiClient(API_BASE_URL);

