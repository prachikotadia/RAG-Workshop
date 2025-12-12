import { useState, FormEvent } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { ApiError } from '../../api/client';

interface SignupFormProps {
  onSwitchToLogin: () => void;
}

export function SignupForm({ onSwitchToLogin }: SignupFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [confirmPasswordError, setConfirmPasswordError] = useState<string | null>(null);
  const { signup, loading, error: authError } = useAuth();

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
    if (value.length < 8) {
      setPasswordError('Password must be at least 8 characters long');
      return false;
    }
    if (!/(?=.*[a-z])/.test(value)) {
      setPasswordError('Password must contain at least one lowercase letter');
      return false;
    }
    if (!/(?=.*[A-Z])/.test(value)) {
      setPasswordError('Password must contain at least one uppercase letter');
      return false;
    }
    if (!/(?=.*\d)/.test(value)) {
      setPasswordError('Password must contain at least one number');
      return false;
    }
    setPasswordError(null);
    return true;
  };

  // Confirm password validation
  const validateConfirmPassword = (value: string): boolean => {
    if (!value) {
      setConfirmPasswordError('Please confirm your password');
      return false;
    }
    if (value !== password) {
      setConfirmPasswordError('Passwords do not match');
      return false;
    }
    setConfirmPasswordError(null);
    return true;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setEmailError(null);
    setPasswordError(null);
    setConfirmPasswordError(null);

    // Validate all inputs
    const isEmailValid = validateEmail(email);
    const isPasswordValid = validatePassword(password);
    const isConfirmPasswordValid = validateConfirmPassword(confirmPassword);

    if (!isEmailValid || !isPasswordValid || !isConfirmPasswordValid) {
      return;
    }

    try {
      await signup(email.trim(), password);
    } catch (err) {
      // Extract actual error message from API response
      const apiError = err as ApiError;
      let errorMessage = 'Signup failed. Please try again.';
      
      if (apiError.detail) {
        if (typeof apiError.detail === 'string') {
          errorMessage = apiError.detail;
        } else if (typeof apiError.detail === 'object') {
          errorMessage = JSON.stringify(apiError.detail);
        }
      }
      
      // Show helpful error messages
      if (apiError.status === 0) {
        errorMessage = 'Cannot connect to server. Please make sure the backend is running on port 8000.';
      } else if (apiError.status === 400) {
        errorMessage = apiError.detail as string || 'Invalid input. Please check your information.';
      } else if (apiError.status === 409) {
        errorMessage = 'An account with this email already exists. Please login instead.';
      }
      
      setError(errorMessage);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 animate-fade-in">
      <div>
        <label htmlFor="signup-email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Email
        </label>
        <input
          id="signup-email"
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
        <label htmlFor="signup-password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Password
        </label>
        <input
          id="signup-password"
          type="password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            if (passwordError) validatePassword(e.target.value);
            // Re-validate confirm password if it's been entered
            if (confirmPassword) validateConfirmPassword(confirmPassword);
          }}
          onBlur={() => validatePassword(password)}
          required
          minLength={8}
          className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 transition-all duration-200 bg-white dark:bg-gray-800 dark:text-white ${
            passwordError
              ? 'border-red-500 focus:ring-red-500/20 focus:border-red-500'
              : 'border-gray-300 dark:border-gray-600 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-blue-400'
          }`}
          placeholder="••••••••"
          autoComplete="new-password"
        />
        {passwordError ? (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{passwordError}</p>
        ) : (
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 font-medium">
            At least 8 characters with uppercase, lowercase, and number
          </p>
        )}
      </div>

      <div>
        <label htmlFor="signup-confirm-password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Confirm Password
        </label>
        <input
          id="signup-confirm-password"
          type="password"
          value={confirmPassword}
          onChange={(e) => {
            setConfirmPassword(e.target.value);
            if (confirmPasswordError) validateConfirmPassword(e.target.value);
          }}
          onBlur={() => validateConfirmPassword(confirmPassword)}
          required
          minLength={8}
          className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 transition-all duration-200 bg-white dark:bg-gray-800 dark:text-white ${
            confirmPasswordError
              ? 'border-red-500 focus:ring-red-500/20 focus:border-red-500'
              : 'border-gray-300 dark:border-gray-600 focus:ring-blue-500/20 focus:border-blue-500 dark:focus:border-blue-400'
          }`}
          placeholder="••••••••"
          autoComplete="new-password"
        />
        {confirmPasswordError && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{confirmPasswordError}</p>
        )}
      </div>

      {(error || authError) && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-200">{error || authError}</p>
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 px-6 bg-blue-500 hover:bg-blue-600 dark:bg-blue-400 dark:hover:bg-blue-500 text-white font-semibold rounded-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-soft hover:shadow-medium hover-lift"
      >
        {loading ? 'Signing up...' : 'Sign up'}
      </button>

      <p className="text-sm text-center text-gray-600 dark:text-gray-400 font-medium">
        Already have an account?{' '}
        <button
          type="button"
          onClick={onSwitchToLogin}
          className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-bold hover-underline transition-all duration-300 hover-lift"
        >
          Login
        </button>
      </p>
    </form>
  );
}

