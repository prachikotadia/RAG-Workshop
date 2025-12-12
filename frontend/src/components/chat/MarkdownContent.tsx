import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownContentProps {
  content: string;
  isUser?: boolean;
}

export function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <div className="markdown-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Headings with beautiful colors
          h1: ({ node, ...props }) => (
            <h1 className="text-2xl font-bold mb-4 mt-4 first:mt-0 text-blue-600 dark:text-blue-400" {...props} />
          ),
          h2: ({ node, ...props }) => (
            <h2 className="text-xl font-bold mb-3 mt-4 first:mt-0 text-purple-600 dark:text-purple-400" {...props} />
          ),
          h3: ({ node, ...props }) => (
            <h3 className="text-lg font-bold mb-2 mt-3 first:mt-0 text-indigo-600 dark:text-indigo-400" {...props} />
          ),
          h4: ({ node, ...props }) => (
            <h4 className="text-base font-bold mb-2 mt-3 first:mt-0 text-violet-600 dark:text-violet-400" {...props} />
          ),
          // Paragraphs with nice spacing and typography
          p: ({ node, ...props }) => (
            <p className="mb-3 last:mb-0 leading-relaxed text-gray-800 dark:text-gray-200" {...props} />
          ),
          // Bold text - beautiful and prominent, no asterisks visible
          strong: ({ node, ...props }) => (
            <strong className="font-bold text-gray-900 dark:text-gray-100" {...props} />
          ),
          // Italic text
          em: ({ node, ...props }) => (
            <em className="italic text-gray-700 dark:text-gray-300" {...props} />
          ),
          // Lists with beautiful styling and spacing
          ul: ({ node, ...props }) => (
            <ul className="mb-4 space-y-2.5 ml-4 list-disc" {...props} />
          ),
          ol: ({ node, ...props }) => (
            <ol className="mb-4 space-y-2.5 ml-4 list-decimal" {...props} />
          ),
          li: ({ node, ...props }) => (
            <li className="leading-relaxed text-gray-800 dark:text-gray-200 pl-1 marker:text-blue-500 dark:marker:text-blue-400" {...props} />
          ),
          // Code blocks with beautiful backgrounds
          code: ({ node, inline, ...props }: any) => {
            if (inline) {
              return (
                <code
                  className="px-1.5 py-0.5 rounded-md bg-gray-200 dark:bg-gray-800 text-pink-600 dark:text-pink-400 text-sm font-mono font-semibold"
                  {...props}
                />
              );
            }
            return (
              <code
                className="block p-4 rounded-lg bg-gray-100 dark:bg-gray-800 text-sm font-mono overflow-x-auto mb-4 border border-gray-200 dark:border-gray-700"
                {...props}
              />
            );
          },
          // Links with beautiful colors and hover effects
          a: ({ node, ...props }: any) => (
            <a
              className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline decoration-2 underline-offset-2 hover:decoration-blue-400 transition-colors"
              target="_blank"
              rel="noopener noreferrer"
              {...props}
            />
          ),
          // Blockquotes with beautiful styling
          blockquote: ({ node, ...props }) => (
            <blockquote
              className="border-l-4 border-blue-500 dark:border-blue-400 pl-4 py-3 my-4 bg-blue-50 dark:bg-blue-900/20 italic rounded-r-lg"
              {...props}
            />
          ),
          // Horizontal rules
          hr: ({ node, ...props }) => (
            <hr className="my-6 border-0 border-t-2 border-gray-300 dark:border-gray-600" {...props} />
        ),
        // Tables with beautiful styling
        table: ({ node, ...props }) => (
          <div className="overflow-x-auto my-4 rounded-lg border border-gray-300 dark:border-gray-600">
            <table className="min-w-full border-collapse" {...props} />
          </div>
        ),
        thead: ({ node, ...props }) => (
          <thead className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-gray-800 dark:to-gray-700" {...props} />
        ),
        th: ({ node, ...props }) => (
          <th className="border border-gray-300 dark:border-gray-600 px-4 py-3 text-left font-bold text-gray-900 dark:text-gray-100" {...props} />
        ),
        td: ({ node, ...props }) => (
          <td className="border border-gray-300 dark:border-gray-600 px-4 py-2 text-gray-700 dark:text-gray-300" {...props} />
        ),
      }}
    >
      {content}
    </ReactMarkdown>
    </div>
  );
}

