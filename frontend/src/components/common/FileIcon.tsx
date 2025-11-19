interface FileIconProps {
  type: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

const fileTypeIcons: Record<string, { icon: string; color: string }> = {
  pdf: {
    icon: 'M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z',
    color: 'text-red-600 dark:text-red-400',
  },
  image: {
    icon: 'M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z',
    color: 'text-green-600 dark:text-green-400',
  },
  text: {
    icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    color: 'text-blue-600 dark:text-blue-400',
  },
  default: {
    icon: 'M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z',
    color: 'text-gray-600 dark:text-gray-400',
  },
};

const sizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
};

export function FileIcon({ type, className = '', size = 'md' }: FileIconProps) {
  const normalizedType = type.toLowerCase();
  let iconConfig = fileTypeIcons.default;

  if (normalizedType === 'pdf' || normalizedType.endsWith('.pdf')) {
    iconConfig = fileTypeIcons.pdf;
  } else if (
    ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'heic', 'heif', 'tiff', 'tif', 'svg', 'ico'].some(
      (ext) => normalizedType.includes(ext)
    )
  ) {
    iconConfig = fileTypeIcons.image;
  } else if (['txt', 'md', 'markdown', 'text'].some((ext) => normalizedType.includes(ext))) {
    iconConfig = fileTypeIcons.text;
  }

  return (
    <svg
      className={`${sizeClasses[size]} ${iconConfig.color} ${className}`}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={iconConfig.icon} />
    </svg>
  );
}

