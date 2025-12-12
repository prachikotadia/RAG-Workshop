import { Outlet, useLocation } from 'react-router-dom';
import { useState } from 'react';
import { useAuth } from './hooks/useAuth';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { LoadingSpinner } from './components/common/LoadingSpinner';
import { CommandPalette } from './components/common/CommandPalette';
import { Icon } from './components/common/Icon';
import { useKeyboardShortcuts, COMMON_SHORTCUTS } from './hooks/useKeyboardShortcuts';
import { useConnectionState } from './hooks/useConnectionState';

const sidebarItems = [
  { path: '/documents', label: 'Documents', icon: 'document' as const },
  { path: '/chat', label: 'Chat Assistant', icon: 'chat' as const },
  { path: '/analytics', label: 'Analytics', icon: 'analytics' as const },
];

export function App() {
  const { loading } = useAuth();
  const location = useLocation();
  const { isConnected, isChecking, error: connectionError } = useConnectionState(30000); // Check every 30 seconds
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  // Derive backend status from connection state
  const backendStatus = isChecking ? 'checking' : (isConnected ? 'connected' : 'error');
  const backendError = connectionError || '';

  // Global keyboard shortcuts
  useKeyboardShortcuts([
    {
      ...COMMON_SHORTCUTS.SEARCH,
      action: () => setCommandPaletteOpen(true),
    },
  ]);

  // Show loading state only briefly - don't block UI for too long
  // If we have a token, show UI immediately and load user in background
  const hasToken = !!localStorage.getItem('access_token'); // Direct check for immediate evaluation
  if (loading && !hasToken) {
    // Only show loading if we don't have a token (first visit)
    return (
      <>
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
          <div className="text-center">
            <LoadingSpinner size="lg" className="mb-4" />
            <div className="text-gray-500 dark:text-gray-400">Loading...</div>
          </div>
        </div>
        <CommandPalette isOpen={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} />
      </>
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
      <div className="h-screen flex flex-col overflow-hidden relative">
        {/* Minimal gradient background */}
        <div className="fixed inset-0 bg-gradient-to-br from-gray-50 to-white dark:from-gray-900 dark:to-gray-950 -z-10" />
        <div className="fixed inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(59,130,246,0.03),transparent_70%)] dark:bg-[radial-gradient(circle_at_50%_50%,rgba(96,165,250,0.05),transparent_70%)] -z-10" />
        
        {/* Backend status banners with glass effect */}
        {showBackendBanner && (
          <div className="glass-strong dark:glass-strong backdrop-blur-xl bg-red-500/90 dark:bg-red-600/90 text-white px-4 py-3 text-center text-sm flex-shrink-0 shadow-strong border-b border-red-400/50 dark:border-red-700/50 animate-slide-down z-50">
            <div className="flex items-center justify-center gap-2">
              <Icon name="x" size="sm" className="text-white flex-shrink-0" />
              <div>
                <strong>Backend:</strong> {String(backendError || 'Connection failed')} - Make sure backend is running on http://127.0.0.1:8000
              </div>
            </div>
          </div>
        )}
        {!showBackendBanner && backendStatus === 'connected' && (
          <div className="glass-strong dark:glass-strong backdrop-blur-xl bg-green-500/90 dark:bg-emerald-600/90 text-white px-4 py-3 text-center text-sm flex-shrink-0 shadow-strong border-b border-green-400/50 dark:border-emerald-500/50 animate-slide-down z-50">
            <div className="flex items-center justify-center gap-2">
              <Icon name="check" size="sm" className="text-white flex-shrink-0" />
              <div>
                <strong>Backend:</strong> Connected
              </div>
            </div>
          </div>
        )}
        
        <Navbar />
        <div className="flex-1 flex overflow-hidden min-h-0 relative">
          <Sidebar items={sidebarItems} />
          <main className="flex-1 overflow-hidden min-w-0 h-full relative">
            <Outlet />
          </main>
        </div>
      </div>
    </ProtectedRoute>
  );
}

