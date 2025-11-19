import { Link, useLocation } from 'react-router-dom';

interface SidebarProps {
  items: Array<{
    path: string;
    label: string;
    icon?: string;
  }>;
}

export function Sidebar({ items }: SidebarProps) {
  const location = useLocation();

  return (
    <aside className="hidden md:block w-64 glass dark:glass-dark backdrop-blur-md bg-white/90 dark:bg-gray-900/90 border-r border-gray-200/50 dark:border-gray-700/50 flex-shrink-0 overflow-y-auto">
      <nav className="p-4">
        <ul className="space-y-2">
          {items.map((item) => {
            const isActive = location.pathname === item.path || 
              (item.path !== '/' && location.pathname.startsWith(item.path));
            
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`block px-4 py-3 rounded-xl transition-all duration-200 hover-lift ${
                    isActive
                      ? 'bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-500 dark:to-purple-500 text-white shadow-lg'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100/80 dark:hover:bg-gray-800/80 border border-transparent hover:border-gray-200/50 dark:hover:border-gray-700/50'
                  }`}
                >
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}

