import { Link, useLocation } from 'react-router-dom';
import { Icon } from '../common/Icon';

interface SidebarProps {
  items: Array<{
    path: string;
    label: string;
    icon?: 'document' | 'chat' | 'analytics' | 'home' | 'settings';
  }>;
}

export function Sidebar({ items }: SidebarProps) {
  const location = useLocation();

  return (
    <aside className="hidden md:block w-64 glass-strong dark:glass-strong backdrop-blur-xl bg-white/85 dark:bg-gray-900/85 border-r border-gray-200/60 dark:border-gray-700/60 flex-shrink-0 overflow-y-auto relative z-30 shadow-strong">
      <nav className="p-4 space-y-3">
        <ul className="space-y-3">
          {items.map((item) => {
            const isActive = location.pathname === item.path || 
              (item.path !== '/' && location.pathname.startsWith(item.path));
            
            return (
              <li key={item.path} className="transform-3d">
                <Link
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                    isActive
                      ? 'bg-gradient-to-r from-blue-500 to-indigo-600 dark:from-blue-400 dark:to-indigo-500 text-white shadow-soft'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100/50 dark:hover:bg-gray-800/50'
                  }`}
                >
                  {item.icon && (
                    <Icon 
                      name={item.icon} 
                      size="sm" 
                      className={isActive ? 'text-white' : 'text-gray-600 dark:text-gray-400'} 
                    />
                  )}
                  <span className="font-medium text-sm md:text-base">{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}

