import { ChatMessage } from '../../api/chat';

interface ChatMessageBubbleProps {
  message: ChatMessage;
}

export function ChatMessageBubble({ message }: ChatMessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 md:mb-5 group`}>
      <div
        className={`max-w-[85%] sm:max-w-[75%] md:max-w-[70%] lg:max-w-[65%] rounded-2xl px-5 py-4 md:px-6 md:py-5 shadow-lg hover:shadow-xl transition-all duration-300 hover-lift ${
          isUser
            ? 'bg-gradient-to-br from-blue-600 via-blue-500 to-purple-600 text-white dark:from-blue-500 dark:via-blue-400 dark:to-purple-500 rounded-br-sm hover:from-blue-700 hover:via-blue-600 hover:to-purple-700'
            : 'glass dark:glass-dark backdrop-blur-md bg-white/90 dark:bg-gray-700/90 text-gray-900 dark:text-gray-100 rounded-bl-sm border border-gray-200/60 dark:border-gray-600/60 hover:bg-white/95 dark:hover:bg-gray-700/95'
        }`}
      >
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <p className="whitespace-pre-wrap break-words text-sm md:text-base leading-relaxed">{message.content}</p>
        </div>
        {message.retrieved_chunks && message.retrieved_chunks.length > 0 && (
          <div className="mt-3 pt-3 border-t border-opacity-20 dark:border-opacity-30">
            <p className="text-xs opacity-80 font-medium">
              📚 Sources: {message.retrieved_chunks.length} document{message.retrieved_chunks.length > 1 ? 's' : ''}
            </p>
          </div>
        )}
        <div className={`mt-2 text-xs opacity-70 ${isUser ? 'text-blue-100 dark:text-blue-200' : 'text-gray-500 dark:text-gray-400'}`}>
          {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  );
}

