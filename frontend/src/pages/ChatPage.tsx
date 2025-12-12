import { useState, useEffect } from 'react';
import { chatApi } from '../api/chat';
import { useApi } from '../hooks/useApi';
import { ChatSessionList } from '../components/chat/ChatSessionList';
import { ChatWindow } from '../components/chat/ChatWindow';

export function ChatPage() {
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const sessionsApi = useApi(chatApi.listSessions);
  const createSessionApi = useApi(chatApi.createSession);
  const deleteSessionApi = useApi(chatApi.deleteSession);
  const deleteAllApi = useApi(chatApi.deleteAllChatHistory);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      await sessionsApi.execute();
    } catch (err) {
      // Error handled by useApi
    }
  };

  const handleCreateNew = async () => {
    try {
      const newSession = await createSessionApi.execute(undefined);
      if (newSession) {
        await loadSessions();
        setSelectedSessionId(newSession.id);
      }
    } catch (err) {
      // Error handled by useApi
    }
  };

  const handleDeleteSession = async (sessionId: number) => {
    try {
      await deleteSessionApi.execute(sessionId);
      // If deleted session was selected, clear selection
      if (selectedSessionId === sessionId) {
        setSelectedSessionId(null);
      }
      // Refresh sessions list
      await loadSessions();
    } catch (err) {
      // Error handled by useApi
    }
  };

  const handleDeleteAll = async () => {
    try {
      await deleteAllApi.execute();
      setSelectedSessionId(null);
      await loadSessions();
    } catch (err) {
      console.error('Error deleting all chat history:', err);
    }
  };

  const sessions = sessionsApi.data || [];

  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="h-full flex flex-col overflow-hidden relative">
      {/* Mobile header */}
      <div className="md:hidden bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-4 py-3 flex items-center justify-between flex-shrink-0 z-30">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Chat</h1>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2.5 rounded-xl glass dark:glass-dark hover-lift hover-zoom transition-all duration-300"
          aria-label="Toggle sidebar"
        >
          <svg className="w-6 h-6 text-gray-700 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {sidebarOpen ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            )}
          </svg>
        </button>
      </div>

      {/* Main chat area - FIXED LAYOUT */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Sidebar - responsive */}
        <div className={`
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          md:translate-x-0
          fixed md:static
          inset-y-0 left-0 z-50 md:z-auto
          w-64 flex-shrink-0
          transition-transform duration-300 ease-in-out
          md:transition-none
          h-full md:h-full
        `}>
          <ChatSessionList
            sessions={sessions}
            selectedSessionId={selectedSessionId}
            onSelectSession={(id) => {
              setSelectedSessionId(id);
              setSidebarOpen(false);
            }}
            onCreateNew={handleCreateNew}
            onDeleteSession={handleDeleteSession}
            onDeleteAll={handleDeleteAll}
            loading={sessionsApi.loading}
          />
        </div>

        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-md z-40 md:hidden animate-fade-in"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Chat window - CRITICAL: flex-1 with proper constraints */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden h-full">
          <ChatWindow sessionId={selectedSessionId} onSessionUpdate={loadSessions} />
        </div>
      </div>
    </div>
  );
}
