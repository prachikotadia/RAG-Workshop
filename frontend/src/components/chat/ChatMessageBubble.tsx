import { ChatMessage } from '../../api/chat';
import { MarkdownContent } from './MarkdownContent';
import { CitationList } from './CitationList';

interface ChatMessageBubbleProps {
  message: ChatMessage;
  query?: string; // Query string for citation highlighting
}

export function ChatMessageBubble({ message, query }: ChatMessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 md:mb-5 group animate-fade-in`}>
      <div
        className={`max-w-[85%] sm:max-w-[75%] md:max-w-[70%] lg:max-w-[65%] rounded-2xl px-5 py-4 md:px-6 md:py-5 transition-all duration-200 hover-lift ${
          isUser
            ? 'bg-blue-500 dark:bg-blue-400 text-white rounded-br-sm shadow-soft'
            : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-bl-sm border border-gray-200 dark:border-gray-700 shadow-soft'
        }`}
      >
        <div className="relative z-10 prose prose-sm dark:prose-invert max-w-none text-sm md:text-base">
          {isUser ? (
            <p className="whitespace-pre-wrap break-words leading-relaxed font-medium">{message.content}</p>
          ) : (
            <MarkdownContent content={message.content} isUser={isUser} />
          )}
        </div>
        {message.retrieved_chunks && message.retrieved_chunks.length > 0 && (
          <div className="mt-3 pt-3 border-t border-white/20 dark:border-gray-600/30">
            <CitationList citations={message.retrieved_chunks} query={query} />
          </div>
        )}
        <div className={`mt-2 text-xs opacity-80 font-medium relative z-10 ${isUser ? 'text-blue-100 dark:text-blue-200' : 'text-gray-500 dark:text-gray-400'}`}>
          {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  );
}

