import { useState } from 'react';
import { ChatSession } from '../../api/chat';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ConfirmModal } from '../common/ConfirmModal';

interface SidebarChatHistoryProps {
  sessions: ChatSession[];
  selectedSessionId: number | null;
  onSelectSession: (sessionId: number) => void;
  onCreateNew: () => void;
  onDeleteSession?: (sessionId: number) => void;
  onDeleteAll?: () => void;
  loading?: boolean;
}

export function SidebarChatHistory({
  sessions,
  selectedSessionId,
  onSelectSession,
  onCreateNew,
  onDeleteSession,
  onDeleteAll,
  loading = false,
}: SidebarChatHistoryProps) {
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteAllModalOpen, setDeleteAllModalOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<number | null>(null);

  const handleDelete = (e: React.MouseEvent, sessionId: number) => {
    e.stopPropagation();
    setSessionToDelete(sessionId);
    setDeleteModalOpen(true);
  };

  const handleConfirmDelete = () => {
    if (sessionToDelete !== null) {
      onDeleteSession?.(sessionToDelete);
      setSessionToDelete(null);
    }
  };

  const handleDeleteAllClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDeleteAllModalOpen(true);
  };

  const handleConfirmDeleteAll = () => {
    onDeleteAll?.();
  };

  return (
    <>
      <ConfirmModal
        isOpen={deleteModalOpen}
        onClose={() => {
          setDeleteModalOpen(false);
          setSessionToDelete(null);
        }}
        onConfirm={handleConfirmDelete}
        title="Delete Chat Session"
        message="Are you sure you want to delete this chat session? This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
      />
      <ConfirmModal
        isOpen={deleteAllModalOpen}
        onClose={() => setDeleteAllModalOpen(false)}
        onConfirm={handleConfirmDeleteAll}
        title="Delete All Chat History"
        message="Are you sure you want to delete all chat history? This will permanently delete all sessions and messages. This action cannot be undone."
        confirmText="Delete All"
        cancelText="Cancel"
        variant="danger"
      />
    <div className="h-full flex flex-col glass dark:glass-dark backdrop-blur-md bg-white/95 dark:bg-gray-800/95 border-r border-gray-200/50 dark:border-gray-700/50">
      <div className="p-4 md:p-5 border-b border-gray-200/50 dark:border-gray-700/50">
        <button
          onClick={onCreateNew}
          className="w-full px-4 py-3 md:px-5 md:py-3.5 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 dark:from-blue-500 dark:to-purple-500 dark:hover:from-blue-600 dark:hover:to-purple-600 text-white font-semibold rounded-xl transition-all duration-300 flex items-center justify-center space-x-2 text-sm md:text-base shadow-lg hover:shadow-xl hover-lift hover-glow transform hover:scale-[1.02] active:scale-[0.98]"
        >
          <svg className="w-4 h-4 md:w-5 md:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          <span>New Chat</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading && sessions.length === 0 ? (
          <div className="flex justify-center items-center py-8">
            <LoadingSpinner />
          </div>
        ) : sessions.length === 0 ? (
          <div className="p-4 text-center text-gray-500 dark:text-gray-400 text-sm">
            No chat sessions yet. Create one to get started!
          </div>
        ) : (
          <div className="p-2 space-y-1">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`group relative w-full px-3 py-3 md:px-4 md:py-3 rounded-xl transition-all duration-200 ${
                  selectedSessionId === session.id
                    ? 'bg-gradient-to-r from-blue-100 to-purple-100 dark:from-blue-900/40 dark:to-purple-900/40 border border-blue-200/50 dark:border-blue-700/50 shadow-md'
                    : 'hover:bg-gray-100/80 dark:hover:bg-gray-700/80 border border-transparent hover:border-gray-200/50 dark:hover:border-gray-600/50'
                }`}
              >
                <button
                  onClick={() => onSelectSession(session.id)}
                  className="w-full text-left"
                >
                  <div className="flex items-center space-x-2">
                    <svg
                      className="w-4 h-4 flex-shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                      />
                    </svg>
                    <span className={`truncate text-xs md:text-sm font-medium flex-1 ${
                      selectedSessionId === session.id
                        ? 'text-blue-900 dark:text-blue-100'
                        : 'text-gray-700 dark:text-gray-300'
                    }`}>
                      {session.title || 'New Chat'}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {new Date(session.created_at).toLocaleDateString()}
                  </div>
                </button>
                {onDeleteSession && (
                  <button
                    onClick={(e) => handleDelete(e, session.id)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity p-1 text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                    title="Delete chat session"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      
      {sessions.length > 0 && onDeleteAll && (
        <div className="p-3 md:p-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={handleDeleteAllClick}
            className="w-full px-4 py-3 md:px-5 md:py-3.5 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 dark:from-red-500 dark:to-red-600 dark:hover:from-red-600 dark:hover:to-red-700 text-white font-semibold rounded-xl transition-all duration-300 flex items-center justify-center space-x-2 text-sm md:text-base shadow-lg hover:shadow-xl hover-lift transform hover:scale-[1.02] active:scale-[0.98]"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
            <span>Delete All History</span>
          </button>
        </div>
      )}
    </div>
    </>
  );
}

