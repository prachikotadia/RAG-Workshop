import { useState, useRef, useEffect } from 'react';
import { chatApi, ChatMessage } from '../../api/chat';
import { useApi } from '../../hooks/useApi';
import { ChatMessageBubble } from './ChatMessageBubble';
import { ChatInputBar } from './ChatInputBar';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { Icon } from '../common/Icon';
import { ShareConversation } from './ShareConversation';

interface ChatWindowProps {
  sessionId: number | null;
  onSessionUpdate?: () => void;
}

export function ChatWindow({ sessionId, onSessionUpdate }: ChatWindowProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [lastQuery, setLastQuery] = useState<string>(''); // Store last query for highlighting
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

  const loadSuggestions = async () => {
    if (!sessionId || messages.length === 0) return;
    
    // Only load suggestions if last message is from assistant
    const lastMessage = messages[messages.length - 1];
    if (lastMessage?.role !== 'assistant') return;

    try {
      const result = await chatApi.getQuestionSuggestions(sessionId);
      if (result?.suggestions) {
        setSuggestions(result.suggestions);
      }
    } catch (err) {
      // Silently fail - suggestions are optional
      setSuggestions([]);
    }
  };

  useEffect(() => {
    if (sessionId && messages.length > 0) {
      // Load suggestions when messages change and last message is assistant
      const lastMessage = messages[messages.length - 1];
      if (lastMessage?.role === 'assistant') {
        loadSuggestions();
      } else {
        setSuggestions([]);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length, sessionId]);

  const [isStreaming, setIsStreaming] = useState(false);

  const handleSend = async (content: string) => {
    if (!sessionId || !content.trim() || sendMessageApi.loading || isStreaming) {
      return;
    }

    const trimmedContent = content.trim();
    setLastQuery(trimmedContent); // Store query for highlighting

    // Optimistic update: Add user message immediately
    const optimisticUserMessage: ChatMessage = {
      id: Date.now(),
      session_id: sessionId,
      role: 'user',
      content: trimmedContent,
      retrieved_chunks: [],
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticUserMessage]);
    scrollToBottom();

    // Try streaming first, fallback to regular if not available
    const useStreaming = true; // Can be made configurable
    
    if (useStreaming) {
        setIsStreaming(true);
        let streamingContent = '';
        const tempAssistantId = Date.now() + 1;

      // Add placeholder assistant message
      const placeholderMessage: ChatMessage = {
        id: tempAssistantId,
        session_id: sessionId,
        role: 'assistant',
        content: '',
        retrieved_chunks: [],
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, placeholderMessage]);

      try {
        await chatApi.sendMessageStream(
          sessionId,
          content.trim(),
          (token) => {
            streamingContent += token;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === tempAssistantId
                  ? { ...msg, content: streamingContent }
                  : msg
              )
            );
            scrollToBottom();
          },
          (citations, messageId) => {
            // Update with final message
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === tempAssistantId
                  ? {
                      ...msg,
                      id: messageId,
                      retrieved_chunks: citations,
                    }
                  : msg
              )
            );
            setIsStreaming(false);
            if (onSessionUpdate) {
              onSessionUpdate();
            }
            // Load question suggestions after assistant message
            loadSuggestions();
          },
          (error) => {
            // Remove placeholder on error
            setMessages((prev) => prev.filter((m) => m.id !== tempAssistantId));
            setIsStreaming(false);
            alert(`Error: ${error}`);
          }
        );
      } catch (err) {
        // Fallback to regular API
        setMessages((prev) => prev.filter((m) => m.id !== tempAssistantId));
        setIsStreaming(false);
        
        try {
          const assistantMessage = await sendMessageApi.execute(sessionId, content.trim());
          if (assistantMessage) {
            await loadMessages();
            if (onSessionUpdate) {
              onSessionUpdate();
            }
          }
        } catch (fallbackErr) {
          setMessages((prev) => prev.filter((m) => m.id !== optimisticUserMessage.id));
        }
      }
    } else {
      // Regular non-streaming path
      try {
        const assistantMessage = await sendMessageApi.execute(sessionId, content.trim());
        if (assistantMessage) {
          await loadMessages();
          if (onSessionUpdate) {
            onSessionUpdate();
          }
          // Load question suggestions after assistant message
          loadSuggestions();
        }
      } catch (err) {
        setMessages((prev) => prev.filter((m) => m.id !== optimisticUserMessage.id));
      }
    }
  };

  if (!sessionId) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-0 relative">
        <div className="text-center max-w-md px-4 animate-fade-in">
          <div className="mb-6">
            <div className="bg-blue-100 dark:bg-blue-900/30 rounded-full p-6 w-24 h-24 mx-auto flex items-center justify-center">
              <svg
                className="w-12 h-12 text-blue-500 dark:text-blue-400"
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
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden relative">
      
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
              <ChatMessageBubble 
                key={message.id} 
                message={message} 
                query={message.role === 'assistant' ? lastQuery : undefined}
              />
            ))}
            {(sendMessageApi.loading || isStreaming) && (
              <div className="flex justify-start animate-fade-in">
                <div className="bg-white dark:bg-gray-800 rounded-2xl px-4 py-3 shadow-soft border border-gray-200 dark:border-gray-700">
                  <div className="flex space-x-1.5">
                    <div
                      className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
                    />
                    <div
                      className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
                      style={{ animationDelay: '0.15s' }}
                    />
                    <div
                      className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"
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

      {/* Question Suggestions */}
      {suggestions.length > 0 && !isStreaming && (
        <div className="px-4 md:px-6 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-900/50 flex-shrink-0">
          <div className="max-w-4xl mx-auto">
            <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-2">
              <Icon name="question" size="xs" className="text-gray-400" />
              <span>Suggested questions:</span>
            </p>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSend(suggestion)}
                  className="px-3 py-1.5 text-xs bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:border-blue-300 dark:hover:border-blue-700 text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400 transition-all duration-200 hover-lift"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Share Conversation */}
      {sessionId && messages.length > 0 && (
        <div className="px-4 md:px-6 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-900/50 flex-shrink-0">
          <div className="max-w-4xl mx-auto">
            <ShareConversation sessionId={sessionId} />
          </div>
        </div>
      )}

      {/* Input area - ALWAYS VISIBLE, fixed at bottom */}
      <div className="flex-shrink-0 relative z-30 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div>
          {sendMessageApi.error && (
            <div className="px-4 md:px-6 pt-3">
              <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-sm text-red-800 dark:text-red-200">{sendMessageApi.error}</p>
              </div>
            </div>
          )}
          <ChatInputBar
            onSend={handleSend}
            disabled={(sendMessageApi.loading || isStreaming) || !sessionId}
            isLoading={sendMessageApi.loading || isStreaming}
          />
        </div>
      </div>
    </div>
  );
}
