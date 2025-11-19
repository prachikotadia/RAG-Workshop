interface HeroSectionProps {
  title: string;
  subtitle: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export function HeroSection({
  title,
  subtitle,
  actionLabel,
  onAction,
  icon,
}: HeroSectionProps) {
  return (
    <div className="bg-gradient-to-br from-blue-50/80 via-indigo-50/60 to-purple-50/80 dark:from-indigo-950/50 dark:via-slate-900 dark:to-slate-900 border-b border-gray-200/50 dark:border-gray-700/50 flex-shrink-0 glass dark:glass-dark backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 md:py-10">
        <div className="text-center">
          {icon && (
            <div className="flex justify-center mb-4 md:mb-5">
              <div className="p-3 md:p-4 glass dark:glass-dark backdrop-blur-md bg-white/80 dark:bg-gray-800/80 rounded-full shadow-xl border border-gray-200/50 dark:border-gray-700/50">
                {icon}
              </div>
            </div>
          )}
          <h1 className="text-2xl md:text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 dark:from-blue-400 dark:to-purple-400 bg-clip-text text-transparent mb-2 md:mb-3">
            {title}
          </h1>
          <p className="text-base md:text-lg text-gray-600 dark:text-gray-300 mb-6 md:mb-8 max-w-2xl mx-auto px-4">
            {subtitle}
          </p>
          {actionLabel && onAction && (
            <button
              onClick={onAction}
              className="inline-flex items-center px-6 py-3 md:px-8 md:py-3.5 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 dark:from-blue-500 dark:to-purple-500 dark:hover:from-blue-600 dark:hover:to-purple-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 text-sm md:text-base hover-lift hover-glow transform hover:scale-105 active:scale-95"
            >
              {actionLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

