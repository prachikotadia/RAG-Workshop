import { useState, useRef, useEffect } from 'react';
import { chatApi, ChatMessage } from '../../api/chat';
import { useApi } from '../../hooks/useApi';
import { ChatMessageBubble } from './ChatMessageBubble';
import { ChatInputBar } from './ChatInputBar';
import { LoadingSpinner } from '../common/LoadingSpinner';

interface ChatWindowProps {
  sessionId: number | null;
  onSessionUpdate?: () => void;
}

export function ChatWindow({ sessionId, onSessionUpdate }: ChatWindowProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesApi = useApi(chatApi.getSessionMessages);
  const sendMessageApi = useApi(chatApi.sendMessage);

  useEffect(() => {
    if (sessionId) {
      loadMessages();
    } else {
      setMessages([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadMessages = async () => {
    if (!sessionId) return;

    try {
      const loadedMessages = await messagesApi.execute(sessionId);
      if (loadedMessages) {
        setMessages(loadedMessages);
      }
    } catch (err) {
      // Error handled by useApi
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async (content: string) => {
    if (!sessionId || !content.trim() || sendMessageApi.loading) {
      return;
    }

    // Optimistic update: Add user message immediately
    const optimisticUserMessage: ChatMessage = {
      id: Date.now(),
      session_id: sessionId,
      role: 'user',
      content: content.trim(),
      retrieved_chunks: [],
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticUserMessage]);
    scrollToBottom();

    try {
      const assistantMessage = await sendMessageApi.execute(sessionId, content.trim());
      if (assistantMessage) {
        // Reload all messages to get the complete conversation with proper IDs
        await loadMessages();
        // Trigger session list refresh to update title
        if (onSessionUpdate) {
          onSessionUpdate();
        }
      }
    } catch (err) {
      // Remove optimistic message on error
      setMessages((prev) => prev.filter((m) => m.id !== optimisticUserMessage.id));
    }
  };

  if (!sessionId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gradient-to-br from-gray-50 via-blue-50/30 to-purple-50/30 dark:from-gray-900 dark:via-blue-900/20 dark:to-purple-900/20 min-h-0 relative">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-white/50 dark:to-gray-800/50 pointer-events-none" />
        <div className="text-center max-w-md px-4 relative z-10">
          <div className="mb-6 hover-lift">
            <div className="glass dark:glass-dark backdrop-blur-sm bg-white/60 dark:bg-gray-800/60 rounded-full p-6 w-24 h-24 mx-auto flex items-center justify-center border border-gray-200/50 dark:border-gray-700/50 shadow-lg">
              <svg
                className="w-12 h-12 mx-auto text-blue-500 dark:text-blue-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
            </div>
          </div>
          <p className="text-gray-700 dark:text-gray-300 text-xl font-semibold mb-2">
            Welcome to RAG Workspace
          </p>
          <p className="text-gray-500 dark:text-gray-400 text-sm md:text-base">
            Select a chat session or create a new one to start chatting with your documents
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden relative bg-gradient-to-br from-slate-50 via-blue-50/20 to-indigo-50/20 dark:from-slate-900 dark:via-indigo-950/30 dark:to-slate-900">
      {/* Gradient overlay for depth */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-white/40 dark:to-slate-900/40 pointer-events-none z-0" />
      
      {/* Messages area - scrollable, takes available space */}
      <div className="flex-1 overflow-y-auto overscroll-contain p-4 md:p-6 space-y-4 relative z-10 min-h-0" style={{ paddingBottom: '1rem' }}>
        {messagesApi.loading && messages.length === 0 ? (
          <div className="flex justify-center items-center h-full min-h-[200px]">
            <div className="text-center">
              <LoadingSpinner size="lg" className="mb-4" />
              <div className="text-gray-500 dark:text-gray-400">Loading messages...</div>
            </div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex justify-center items-center h-full min-h-[200px]">
            <div className="text-center max-w-md px-4">
              <div className="mb-4">
                <svg
                  className="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
              </div>
              <p className="text-gray-500 dark:text-gray-400 text-base md:text-lg font-medium mb-1">
                No messages yet
              </p>
              <p className="text-gray-400 dark:text-gray-500 text-sm">
                Start a conversation by asking a question below
              </p>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto w-full">
            {messages.map((message) => (
              <ChatMessageBubble key={message.id} message={message} />
            ))}
            {sendMessageApi.loading && (
              <div className="flex justify-start animate-fade-in">
                <div className="glass dark:glass-dark backdrop-blur-sm bg-white/80 dark:bg-gray-700/80 rounded-2xl px-4 py-3 shadow-lg border border-gray-200/50 dark:border-gray-600/50">
                  <div className="flex space-x-1.5">
                    <div
                      className="w-2 h-2 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full animate-bounce"
                    />
                    <div
                      className="w-2 h-2 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full animate-bounce"
                      style={{ animationDelay: '0.15s' }}
                    />
                    <div
                      className="w-2 h-2 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full animate-bounce"
                      style={{ animationDelay: '0.3s' }}
                    />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} className="h-1" />
          </div>
        )}
      </div>

      {/* Input area - ALWAYS VISIBLE, fixed at bottom */}
      <div className="flex-shrink-0 relative z-30 border-t border-gray-200/30 dark:border-gray-700/30 shadow-[0_-4px_20px_rgba(0,0,0,0.1)] dark:shadow-[0_-4px_20px_rgba(0,0,0,0.3)]">
        <div className="glass dark:glass-dark backdrop-blur-xl bg-white/95 dark:bg-gray-800/95">
          {sendMessageApi.error && (
            <div className="px-4 md:px-6 pt-3">
              <div className="p-3 bg-red-50/90 dark:bg-red-900/30 border border-red-200/50 dark:border-red-800/50 rounded-lg backdrop-blur-sm">
                <p className="text-sm text-red-800 dark:text-red-200 font-medium">{sendMessageApi.error}</p>
              </div>
            </div>
          )}
          <ChatInputBar
            onSend={handleSend}
            disabled={sendMessageApi.loading || !sessionId}
            isLoading={sendMessageApi.loading}
          />
        </div>
      </div>
    </div>
  );
}
