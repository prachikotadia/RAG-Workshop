import { Outlet, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useAuth } from './hooks/useAuth';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { LoadingSpinner } from './components/common/LoadingSpinner';
import { api } from './api/client';

const sidebarItems = [
  { path: '/documents', label: 'Documents' },
  { path: '/chat', label: 'Chat Assistant' },
];

export function App() {
  const { loading } = useAuth();
  const location = useLocation();
  const [backendStatus, setBackendStatus] = useState<'checking' | 'connected' | 'error'>('checking');
  const [backendError, setBackendError] = useState<string>('');

  // Check backend connectivity on mount (non-blocking, with timeout)
  useEffect(() => {
    const checkBackend = async () => {
      try {
        // Use AbortController for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000); // 2 second timeout
        
        const response = await api.get<{ status: string }>('/health');
        clearTimeout(timeoutId);
        
        if (response.status === 'ok') {
          setBackendStatus('connected');
          setBackendError('');
        } else {
          setBackendStatus('error');
          setBackendError('Backend returned unexpected response');
        }
      } catch (error: any) {
        setBackendStatus('error');
        setBackendError(error?.detail || 'Could not connect to backend');
        // Don't log to console in production - just set status
      }
    };
    // Don't block - check in background
    checkBackend();
  }, []);

  // Show loading state only briefly - don't block UI for too long
  // If we have a token, show UI immediately and load user in background
  const hasToken = !!localStorage.getItem('access_token');
  if (loading && !hasToken) {
    // Only show loading if we don't have a token (first visit)
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900">
        <div className="text-center">
          <LoadingSpinner size="lg" className="mb-4" />
          <div className="text-gray-500 dark:text-gray-400 mb-2">Loading...</div>
        </div>
      </div>
    );
  }

  // Show backend status banner if error
  const showBackendBanner = backendStatus === 'error' && location.pathname !== '/login';

  // Show auth page without layout
  if (location.pathname === '/login') {
    return <Outlet />;
  }

  // Show main app with layout and protection
  return (
    <ProtectedRoute>
      <div className="h-screen flex flex-col bg-gradient-to-br from-slate-50 via-blue-50/20 to-indigo-50/20 dark:from-slate-900 dark:via-indigo-950/30 dark:to-slate-900 overflow-hidden">
        {showBackendBanner && (
          <div className="bg-gradient-to-r from-red-500 to-red-600 text-white px-4 py-2 text-center text-sm flex-shrink-0 shadow-md">
            <strong>Backend:</strong> ❌ {backendError} - Make sure backend is running on http://127.0.0.1:8000
          </div>
        )}
        {!showBackendBanner && backendStatus === 'connected' && (
          <div className="bg-gradient-to-r from-green-500 to-emerald-600 text-white px-4 py-2 text-center text-sm flex-shrink-0 shadow-md">
            <strong>Backend:</strong> ✅ Connected
          </div>
        )}
        <Navbar />
        <div className="flex-1 flex overflow-hidden min-h-0">
          <Sidebar items={sidebarItems} />
          <main className="flex-1 overflow-hidden min-w-0 h-full">
            <Outlet />
          </main>
        </div>
      </div>
    </ProtectedRoute>
  );
}

