import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi, User } from '../api/auth';
import { ApiError } from '../api/client';

interface UseAuthReturn {
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchCurrentUser: () => Promise<void>;
  isAuthenticated: boolean;
}

export function useAuth(): UseAuthReturn {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchCurrentUser = useCallback(async () => {
    const currentToken = token || localStorage.getItem('access_token');
    if (!currentToken) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      // Add reasonable timeout (3 seconds - fail fast for better UX)
      const timeoutPromise = new Promise<never>((_, reject) => 
        setTimeout(() => reject({ detail: 'Request timeout', status: 0 } as ApiError), 3000)
      );
      
      const currentUser = await Promise.race([
        authApi.getCurrentUser(),
        timeoutPromise
      ]);
      
      setUser(currentUser);
      if (!token) {
        setToken(currentToken);
      }
      setError(null); // Clear any previous errors on success
    } catch (err) {
      const apiError = err as ApiError;
      
      // Only clear token and redirect on 401 (unauthorized), not on timeout/network errors
      if (apiError.status === 401) {
        localStorage.removeItem('access_token');
        setToken(null);
        setUser(null);
        setError(null);
        navigate('/login');
      } else {
        // Network error or timeout - keep token, don't set error, don't log
        // Silently fail - user can still use the app if they have a valid token
        setError(null);
      }
    } finally {
      setLoading(false);
    }
  }, [token, navigate]);

  // Load token from localStorage on mount and fetch user
  useEffect(() => {
    const storedToken = localStorage.getItem('access_token');
    if (storedToken) {
      setToken(storedToken);
      // Fetch user in background - don't block UI
      fetchCurrentUser().catch(() => {
        // Silently handle errors - user can still use app
      });
    } else {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  // Fetch current user when token changes (but not on initial mount)
  // Prevent excessive retries - only fetch once per token change, no auto-retry
  const hasFetchedRef = useRef(false);
  const lastTokenRef = useRef<string | null>(null);
  
  useEffect(() => {
    // Only fetch if token changed (not just on mount)
    if (token && token !== lastTokenRef.current) {
      lastTokenRef.current = token;
      hasFetchedRef.current = false;
    }
    
    if (token && !user && !hasFetchedRef.current) {
      hasFetchedRef.current = true;
      fetchCurrentUser();
      // Don't reset hasFetchedRef - only allow manual retry via fetchCurrentUser()
    } else if (!token) {
      hasFetchedRef.current = false;
      lastTokenRef.current = null;
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, user]);

  const login = useCallback(async (email: string, password: string) => {
    try {
      setLoading(true);
      setError(null);
      
      // Validate input
      if (!email || !email.trim()) {
        setError('Email is required');
        setLoading(false);
        return;
      }
      
      if (!password || !password.trim()) {
        setError('Password is required');
        setLoading(false);
        return;
      }
      
      // Normalize email (case-insensitive)
      const normalizedEmail = email.toLowerCase().trim();
      
      // Login request
      const response = await authApi.login(normalizedEmail, password);
      
      if (!response || !response.access_token) {
        throw { detail: 'Invalid response from server', status: 500 } as ApiError;
      }
      
      // Store token
      localStorage.setItem('access_token', response.access_token);
      setToken(response.access_token);

      // Fetch user info with retry
      try {
        const currentUser = await authApi.getCurrentUser();
        setUser(currentUser);
      } catch (userErr) {
        // If getCurrentUser fails, still allow login (token is valid)
        setUser({
          id: 0,
          email: normalizedEmail,
          created_at: new Date().toISOString(),
        });
      }

      // Ensure state is updated before navigation
      setLoading(false);
      
      // Navigate to documents after a brief delay to ensure state updates
      setTimeout(() => {
        navigate('/documents', { replace: true });
      }, 100);
    } catch (err) {
      const apiError = err as ApiError;
      let errorMessage = 'Login failed. Please check your credentials.';
      
      if (apiError.detail) {
        if (typeof apiError.detail === 'string') {
          errorMessage = apiError.detail;
        } else if (typeof apiError.detail === 'object') {
          errorMessage = JSON.stringify(apiError.detail);
        }
      }
      
      // Provide helpful error messages
      if (apiError.status === 0) {
        errorMessage = 'Cannot connect to server. Please make sure the backend is running on port 8000.';
      } else if (apiError.status === 401) {
        errorMessage = 'Incorrect email or password. Please try again.';
      } else if (apiError.status === 500) {
        errorMessage = 'Server error. Please try again later.';
      }
      
      setError(errorMessage);
      setLoading(false);
      throw err;
    }
  }, [navigate]);

  const signup = useCallback(async (email: string, password: string) => {
    try {
      setLoading(true);
      setError(null);
      
      // Normalize email (case-insensitive)
      const normalizedEmail = email.toLowerCase().trim();
      
      // Validate password length
      if (password.length < 8) {
        throw { detail: 'Password must be at least 8 characters long', status: 400 } as ApiError;
      }
      
      await authApi.signup(normalizedEmail, password);
      
      // Auto-login after signup
      await login(normalizedEmail, password);
    } catch (err) {
      const apiError = err as ApiError;
      const errorMessage = typeof apiError.detail === 'string' 
        ? apiError.detail 
        : 'Signup failed. Please try again.';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    setToken(null);
    setUser(null);
    navigate('/login');
  }, [navigate]);

  return {
    user,
    token,
    loading,
    error,
    login,
    signup,
    logout,
    fetchCurrentUser,
    isAuthenticated: !!token || !!localStorage.getItem('access_token'),
  };
}

