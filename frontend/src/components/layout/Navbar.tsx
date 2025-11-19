import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { ThemeToggle } from './ThemeToggle';

export function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/auth');
  };

  return (
    <nav className="glass dark:glass-dark backdrop-blur-md bg-white/95 dark:bg-gray-800/95 border-b border-gray-200/50 dark:border-gray-700/50 shadow-lg flex-shrink-0">
      <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8">
        <div className="flex justify-between items-center h-14 md:h-16">
          <div className="flex items-center space-x-4 md:space-x-8">
            <Link to="/" className="flex items-center space-x-2 hover-lift transition-transform duration-200">
              <div className="p-1.5 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 dark:from-blue-400 dark:to-purple-500">
                <svg className="w-5 h-5 md:w-6 md:h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <span className="text-lg md:text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400 bg-clip-text text-transparent">RAG Workspace</span>
            </Link>
            <div className="hidden md:flex space-x-2">
              <Link
                to="/documents"
                className="px-4 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100/80 dark:hover:bg-gray-700/80 transition-all duration-200 hover-lift"
              >
                Documents
              </Link>
              <Link
                to="/chat"
                className="px-4 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100/80 dark:hover:bg-gray-700/80 transition-all duration-200 hover-lift"
              >
                Chat
              </Link>
            </div>
          </div>
          <div className="flex items-center space-x-2 md:space-x-4">
            <ThemeToggle />
            {user && (
              <div className="flex items-center space-x-2 md:space-x-4">
                <span className="hidden sm:inline text-xs md:text-sm text-gray-700 dark:text-gray-300 truncate max-w-[120px] md:max-w-none font-medium">
                  {user.email}
                </span>
                <button
                  onClick={handleLogout}
                  className="px-3 py-1.5 md:px-4 md:py-2 text-xs md:text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50/80 dark:hover:bg-red-900/20 rounded-lg transition-all duration-200 hover-lift"
                >
                  <span className="hidden sm:inline">Logout</span>
                  <svg className="sm:hidden w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
