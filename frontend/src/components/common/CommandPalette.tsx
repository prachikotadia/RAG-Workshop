import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Icon } from './Icon';

interface Command {
  id: string;
  label: string;
  description?: string;
  icon?: React.ReactNode;
  action: () => void;
  category: string;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  const commands: Command[] = [
    {
      id: 'new-chat',
      label: 'New Chat',
      description: 'Start a new conversation',
      icon: <Icon name="chat" size="md" className="text-blue-500 dark:text-blue-400" />,
      category: 'Chat',
      action: () => {
        navigate('/chat');
        onClose();
      },
    },
    {
      id: 'documents',
      label: 'Go to Documents',
      description: 'View all documents',
      icon: <Icon name="document" size="md" className="text-indigo-500 dark:text-indigo-400" />,
      category: 'Navigation',
      action: () => {
        navigate('/documents');
        onClose();
      },
    },
    {
      id: 'analytics',
      label: 'Go to Analytics',
      description: 'View analytics dashboard',
      icon: <Icon name="analytics" size="md" className="text-purple-500 dark:text-purple-400" />,
      category: 'Navigation',
      action: () => {
        navigate('/analytics');
        onClose();
      },
    },
    {
      id: 'chat',
      label: 'Go to Chat',
      description: 'Open chat assistant',
      icon: <Icon name="chat" size="md" className="text-blue-500 dark:text-blue-400" />,
      category: 'Navigation',
      action: () => {
        navigate('/chat');
        onClose();
      },
    },
  ];

  const filteredCommands = commands.filter(
    (cmd) =>
      cmd.label.toLowerCase().includes(search.toLowerCase()) ||
      cmd.description?.toLowerCase().includes(search.toLowerCase())
  );

  // Group by category
  const groupedCommands = filteredCommands.reduce((acc, cmd) => {
    if (!acc[cmd.category]) {
      acc[cmd.category] = [];
    }
    acc[cmd.category].push(cmd);
    return acc;
  }, {} as Record<string, Command[]>);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
      setSearch('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Handle keyboard shortcuts when palette is open
  useEffect(() => {
    if (!isOpen) return;
    
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, filteredCommands.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredCommands[selectedIndex]) {
          filteredCommands[selectedIndex].action();
        }
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, filteredCommands, selectedIndex, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh] bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl mx-4 bg-white dark:bg-gray-800 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-700 animate-fade-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Icon name="search" size="sm" className="text-gray-400 dark:text-gray-500" />
            </div>
            <input
              ref={inputRef}
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setSelectedIndex(0);
              }}
              placeholder="Type a command or search..."
              className="w-full pl-10 pr-4 py-3 bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500"
            />
          </div>
        </div>
        <div className="max-h-96 overflow-y-auto">
          {Object.entries(groupedCommands).map(([category, cmds]) => (
            <div key={category} className="py-2">
              <div className="px-4 py-1 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                {category}
              </div>
              {cmds.map((cmd) => {
                const globalIndex = filteredCommands.indexOf(cmd);
                const isSelected = globalIndex === selectedIndex;
                return (
                  <button
                    key={cmd.id}
                    onClick={cmd.action}
                    className={`w-full px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-all duration-200 ${
                      isSelected ? 'bg-blue-50 dark:bg-blue-900/20 border-l-2 border-blue-500' : ''
                    }`}
                    onMouseEnter={() => setSelectedIndex(globalIndex)}
                  >
                    <div className="flex items-center gap-3">
                      {cmd.icon && <div className="flex-shrink-0">{cmd.icon}</div>}
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-900 dark:text-white">{cmd.label}</div>
                        {cmd.description && (
                          <div className="text-sm text-gray-500 dark:text-gray-400 truncate">{cmd.description}</div>
                        )}
                      </div>
                      {isSelected && (
                        <div className="text-xs text-gray-400 dark:text-gray-500 flex-shrink-0">Enter to select</div>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          ))}
          {filteredCommands.length === 0 && (
            <div className="px-4 py-12 text-center">
              <Icon name="search" size="lg" className="text-gray-300 dark:text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-gray-400 font-medium">No commands found</p>
              <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">Try a different search term</p>
            </div>
          )}
        </div>
        <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
          <div className="flex items-center justify-between">
            <div>
              <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded">↑</kbd>{' '}
              <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded">↓</kbd> Navigate{' '}
              <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded">Enter</kbd> Select{' '}
              <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded">Esc</kbd> Close
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

