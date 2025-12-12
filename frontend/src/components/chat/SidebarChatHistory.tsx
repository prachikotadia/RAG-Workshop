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
    <div className="h-full flex flex-col glass-strong dark:glass-strong backdrop-blur-xl bg-white/95 dark:bg-gray-800/95 border-r border-gray-200/60 dark:border-gray-700/60">
      <div className="p-4 md:p-5 border-b border-gray-200/60 dark:border-gray-700/60">
        <button
          onClick={onCreateNew}
          className="w-full px-4 py-3 bg-blue-500 hover:bg-blue-600 dark:bg-blue-400 dark:hover:bg-blue-500 text-white font-semibold rounded-xl transition-all duration-200 flex items-center justify-center space-x-2 text-sm md:text-base shadow-soft hover:shadow-medium hover-lift"
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
            <div className="glass dark:glass-dark px-6 py-4 rounded-2xl shadow-soft">
            <LoadingSpinner />
            </div>
          </div>
        ) : sessions.length === 0 ? (
          <div className="p-6 text-center">
            <div className="glass-strong dark:glass-strong backdrop-blur-sm rounded-2xl p-6">
              <p className="text-gray-600 dark:text-gray-400 text-sm font-semibold">
            No chat sessions yet. Create one to get started!
              </p>
            </div>
          </div>
        ) : (
          <div className="p-2 space-y-2">
            {sessions.map((session, index) => (
              <div
                key={session.id}
                className={`group relative w-full px-4 py-3 rounded-xl transition-all duration-200 hover-lift animate-fade-in ${
                  selectedSessionId === session.id
                    ? 'bg-blue-500 dark:bg-blue-400 text-white shadow-soft'
                    : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                <button
                  onClick={() => onSelectSession(session.id)}
                  className="w-full text-left"
                >
                  <div className="flex items-center space-x-3">
                    <div className={`p-1.5 rounded-lg flex-shrink-0 ${
                      selectedSessionId === session.id
                        ? 'bg-white/20'
                        : 'bg-blue-100/50 dark:bg-blue-900/30'
                    }`}>
                    <svg
                        className="w-4 h-4"
                      fill="none"
                        stroke={selectedSessionId === session.id ? "currentColor" : "currentColor"}
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                      />
                    </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <span className={`truncate block text-xs md:text-sm font-bold ${
                      selectedSessionId === session.id
                          ? 'text-white'
                        : 'text-gray-700 dark:text-gray-300'
                    }`}>
                      {session.title || 'New Chat'}
                    </span>
                      <div className={`text-xs mt-1 font-medium ${
                        selectedSessionId === session.id
                          ? 'text-blue-100'
                          : 'text-gray-500 dark:text-gray-400'
                      }`}>
                        {new Date(session.created_at).toLocaleDateString()}
                      </div>
                  </div>
                  </div>
                </button>
                {onDeleteSession && (
                  <button
                    onClick={(e) => handleDelete(e, session.id)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-all duration-300 p-1.5 rounded-lg hover:bg-red-500/20 dark:hover:bg-red-500/30 text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 hover-zoom"
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
        <div className="p-3 md:p-4 border-t border-gray-200/60 dark:border-gray-700/60">
          <button
            onClick={handleDeleteAllClick}
            className="w-full px-4 py-3 bg-red-500 hover:bg-red-600 dark:bg-red-600 dark:hover:bg-red-700 text-white font-semibold rounded-xl transition-all duration-200 flex items-center justify-center space-x-2 text-sm md:text-base shadow-soft hover:shadow-medium hover-lift"
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

