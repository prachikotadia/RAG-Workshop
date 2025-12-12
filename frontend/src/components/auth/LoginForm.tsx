import { useState, FormEvent, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { ApiError, api } from '../../api/client';

interface LoginFormProps {
  onSwitchToSignup: () => void;
}

export function LoginForm({ onSwitchToSignup }: LoginFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);
  const { login, loading, error: authError } = useAuth();

  // Check backend connection on mount and periodically
  useEffect(() => {
    const checkBackend = async () => {
      try {
        await api.get('/health', undefined, false, 2000, true);
        setBackendConnected(true);
      } catch {
        setBackendConnected(false);
      }
    };
    
    checkBackend();
    // Re-check every 10 seconds to detect when backend comes back online
    const interval = setInterval(checkBackend, 10000);
    return () => clearInterval(interval);
  }, []);

  // Email validation
  const validateEmail = (value: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!value.trim()) {
      setEmailError('Email is required');
      return false;
    }
    if (!emailRegex.test(value)) {
      setEmailError('Please enter a valid email address');
      return false;
    }
    setEmailError(null);
    return true;
  };

  // Password validation
  const validatePassword = (value: string): boolean => {
    if (!value) {
      setPasswordError('Password is required');
      return false;
    }
    if (value.length < 6) {
      setPasswordError('Password must be at least 6 characters');
      return false;
    }
    setPasswordError(null);
    return true;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setEmailError(null);
    setPasswordError(null);

    // Validate inputs
    const isEmailValid = validateEmail(email);
    const isPasswordValid = validatePassword(password);

    if (!isEmailValid || !isPasswordValid) {
      return;
    }

    // Check backend connection first (quick check, 3 second timeout, silent mode)
    try {
      await api.get('/health', undefined, false, 3000, true);
    } catch (healthErr) {
      const healthError = healthErr as ApiError;
      if (healthError.status === 0) {
        if (typeof healthError.detail === 'string' && healthError.detail.includes('timeout')) {
          setError('Backend server is not responding. The monitor will auto-restart it. Please wait a moment and try again, or run: bash ensure_backend_running.sh');
        } else {
          setError('Cannot connect to backend server. Run: bash ensure_backend_running.sh');
        }
      } else {
        setError('Backend server is not responding properly. Run: bash check_backend.sh to diagnose');
      }
      return;
    }

    try {
      await login(email.trim(), password);
      // If login succeeds, navigation happens in useAuth hook
    } catch (err) {
      // Extract actual error message from API response
      const apiError = err as ApiError;
      let errorMessage = 'Login failed. Please check your credentials.';
      
      if (apiError.detail) {
        if (typeof apiError.detail === 'string') {
          errorMessage = apiError.detail;
        } else if (typeof apiError.detail === 'object') {
          errorMessage = JSON.stringify(apiError.detail);
        }
      }
      
      // Show helpful error messages
      if (apiError.status === 0) {
        if (typeof apiError.detail === 'string' && apiError.detail.includes('timeout')) {
          errorMessage = apiError.detail;
        } else {
          errorMessage = 'Cannot connect to server. Please make sure the backend is running on port 8000.';
        }
      } else if (apiError.status === 401) {
        errorMessage = 'Incorrect email or password. Please try again.';
      } else if (apiError.status === 500) {
        errorMessage = 'Server error. Please try again later.';
      }
      
      setError(errorMessage);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 animate-fade-in">
      <div>
        <label htmlFor="login-email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Email
        </label>
        <input
          id="login-email"
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (emailError) validateEmail(e.target.value);
          }}
          onBlur={() => validateEmail(email)}
          required
          className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 transition-all duration-200 bg-white dark:bg-gray-800 dark:text-white ${
            emailError
              ? 'border-red-500 focus:ring-red-500/20 focus:border-red-500'
              : 'border-gray-300 dark:border-gray-600 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-blue-400'
          }`}
          placeholder="you@example.com"
          autoComplete="email"
        />
        {emailError && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{emailError}</p>
        )}
      </div>

      <div>
        <label htmlFor="login-password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Password
        </label>
        <input
          id="login-password"
          type="password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            if (passwordError) validatePassword(e.target.value);
          }}
          onBlur={() => validatePassword(password)}
          required
          className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 transition-all duration-200 bg-white dark:bg-gray-800 dark:text-white ${
            passwordError
              ? 'border-red-500 focus:ring-red-500/20 focus:border-red-500'
              : 'border-gray-300 dark:border-gray-600 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-blue-400'
          }`}
          placeholder="••••••••"
          autoComplete="current-password"
        />
        {passwordError && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{passwordError}</p>
        )}
      </div>

      {backendConnected === false && (
        <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg mb-4">
          <p className="text-sm text-yellow-800 dark:text-yellow-200 font-medium">
            ⚠️ Backend server is not connected. Please start the backend server:
          </p>
          <p className="text-xs text-yellow-700 dark:text-yellow-300 mt-1 font-mono">
            bash ensure_backend_running.sh
          </p>
          <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-2">
            Or run: <code className="bg-yellow-100 dark:bg-yellow-900 px-1 rounded">bash check_backend.sh</code> to check and fix automatically
          </p>
        </div>
      )}

      {(error || authError) && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-200">{error || authError}</p>
        </div>
      )}

      <button
        type="submit"
        disabled={loading || backendConnected === false}
        className="w-full py-3 px-6 bg-blue-500 hover:bg-blue-600 dark:bg-blue-400 dark:hover:bg-blue-500 text-white font-semibold rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-soft hover:shadow-medium hover-lift"
      >
        {loading ? 'Logging in...' : backendConnected === false ? 'Backend Not Connected' : 'Login'}
      </button>

      <p className="text-sm text-center text-gray-600 dark:text-gray-400 font-medium">
        Don't have an account?{' '}
        <button
          type="button"
          onClick={onSwitchToSignup}
          className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-bold hover-underline transition-all duration-300 hover-lift"
        >
          Sign up
        </button>
      </p>
    </form>
  );
}

