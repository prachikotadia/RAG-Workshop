import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { ThemeToggle } from './ThemeToggle';
import { Icon } from '../common/Icon';

export function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/auth');
  };

  return (
    <nav className="glass-strong dark:glass-strong backdrop-blur-xl bg-white/90 dark:bg-gray-800/90 border-b border-gray-200/60 dark:border-gray-700/60 shadow-strong flex-shrink-0 relative z-40">
      <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8">
        <div className="flex justify-between items-center h-14 md:h-16">
          <div className="flex items-center space-x-4 md:space-x-8">
            <Link 
              to="/" 
              className="flex items-center space-x-3 hover-lift group transition-all duration-200"
            >
              <div className="relative">
                <div className="relative p-2 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 dark:from-blue-400 dark:to-indigo-500 shadow-soft group-hover:shadow-medium transition-all duration-200 group-hover:scale-105">
                  <Icon name="document" size="md" className="text-white" />
                </div>
              </div>
              <span className="text-lg md:text-xl font-semibold text-gray-900 dark:text-white transition-colors duration-200">RAG Workspace</span>
            </Link>
            <div className="hidden md:flex space-x-2">
              <Link
                to="/documents"
                className="px-4 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100/50 dark:hover:bg-gray-800/50 transition-all duration-200"
              >
                Documents
              </Link>
              <Link
                to="/chat"
                className="px-4 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100/50 dark:hover:bg-gray-800/50 transition-all duration-200"
              >
                Chat
              </Link>
              <Link
                to="/analytics"
                className="px-4 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-gray-100/50 dark:hover:bg-gray-800/50 transition-all duration-200"
              >
                Analytics
              </Link>
            </div>
          </div>
          <div className="flex items-center space-x-2 md:space-x-4">
            <ThemeToggle />
            {user && (
              <div className="flex items-center space-x-2 md:space-x-4">
                <span className="hidden sm:inline text-xs md:text-sm text-gray-700 dark:text-gray-300 truncate max-w-[120px] md:max-w-none font-semibold glass dark:glass-dark px-3 py-1.5 rounded-lg">
                  {user.email}
                </span>
                <button
                  onClick={handleLogout}
                  className="inline-flex items-center gap-2 px-3 py-1.5 md:px-4 md:py-2 text-xs md:text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-red-600 dark:hover:text-red-400 rounded-lg hover:bg-gray-100/50 dark:hover:bg-gray-800/50 transition-all duration-200"
                >
                  <Icon name="arrow-right" size="sm" className="sm:hidden" />
                  <span className="hidden sm:inline">Logout</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
