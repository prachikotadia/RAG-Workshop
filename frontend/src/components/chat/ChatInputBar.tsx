import { useState, FormEvent, KeyboardEvent } from 'react';

interface ChatInputBarProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  isLoading?: boolean;
}

export function ChatInputBar({
  onSend,
  disabled = false,
  placeholder: defaultPlaceholder = 'Ask a question about your documents...',
  isLoading = false,
}: ChatInputBarProps) {
  const [inputValue, setInputValue] = useState('');
  const placeholder = disabled ? "Select a chat session to start typing..." : defaultPlaceholder;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !disabled && !isLoading) {
      onSend(inputValue.trim());
      setInputValue('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="p-4 md:p-5 pb-4 md:pb-6" style={{ paddingBottom: 'max(1rem, env(safe-area-inset-bottom))' }}>
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
        <div className="flex items-end gap-3 md:gap-4">
          <div className="flex-1 relative group">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              rows={1}
              className="w-full px-5 py-4 md:px-6 md:py-5 pr-16 md:pr-20 border-2 border-gray-300/80 dark:border-gray-600/80 rounded-2xl focus:outline-none focus:ring-4 focus:ring-blue-500/40 focus:border-blue-500 dark:focus:border-blue-400 dark:bg-gray-700/90 dark:text-white dark:placeholder-gray-400/80 resize-none transition-all duration-300 text-base md:text-lg shadow-xl hover:shadow-2xl hover:border-blue-400/80 dark:hover:border-blue-500/80 focus:shadow-2xl bg-white/95 dark:bg-gray-800/95 backdrop-blur-sm hover-lift font-medium placeholder:text-gray-400 dark:placeholder:text-gray-500"
              disabled={disabled || isLoading}
              style={{ 
                minHeight: '56px', 
                maxHeight: '200px',
                lineHeight: '1.6'
              }}
            />
            {inputValue.length > 0 && (
              <div className="absolute right-5 md:right-6 bottom-4 md:bottom-5 text-xs text-gray-500 dark:text-gray-400 font-semibold bg-white/90 dark:bg-gray-800/90 px-2 py-1 rounded-md shadow-sm border border-gray-200/50 dark:border-gray-700/50">
                {inputValue.length}
              </div>
            )}
          </div>
          <button
            type="submit"
            disabled={!inputValue.trim() || disabled || isLoading}
            className="px-5 py-4 md:px-7 md:py-5 bg-gradient-to-r from-blue-600 via-blue-500 to-purple-600 hover:from-blue-700 hover:via-blue-600 hover:to-purple-700 active:from-blue-800 active:to-purple-800 dark:from-blue-500 dark:via-blue-400 dark:to-purple-500 dark:hover:from-blue-600 dark:hover:via-blue-500 dark:hover:to-purple-600 dark:active:from-blue-700 dark:active:to-purple-700 text-white font-semibold rounded-2xl transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed shadow-xl hover:shadow-2xl hover:shadow-blue-500/60 disabled:shadow-md flex items-center justify-center space-x-2 text-base md:text-lg flex-shrink-0 min-w-[70px] md:min-w-[90px] hover-lift hover-glow transform hover:scale-105 active:scale-95 disabled:transform-none"
          >
            {isLoading ? (
              <>
                <svg className="animate-spin h-4 w-4 md:h-5 md:w-5" fill="none" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                <span className="hidden sm:inline">Sending...</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4 md:w-5 md:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                  />
                </svg>
                <span className="hidden sm:inline">Send</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

