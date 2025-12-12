import { useEffect } from 'react';

export interface KeyboardShortcut {
  key: string;
  ctrl?: boolean;
  meta?: boolean; // Cmd on Mac
  shift?: boolean;
  alt?: boolean;
  action: () => void;
  description: string;
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]) {
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Skip if event.key is undefined
      if (!event.key) return;
      
      for (const shortcut of shortcuts) {
        if (!shortcut.key) continue;
        
        const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase();
        const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey;
        const altMatch = shortcut.alt ? event.altKey : !event.altKey;

        // Skip if modifier keys don't match
        if (shortcut.ctrl && !event.ctrlKey && !event.metaKey) continue;
        if (shortcut.meta && !event.metaKey && !event.ctrlKey) continue;
        if (shortcut.shift && !event.shiftKey) continue;
        if (shortcut.alt && !event.altKey) continue;

        // Check if it's a match (allow Cmd on Mac to work as Ctrl)
        const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
        const modifierMatch = isMac
          ? (shortcut.meta ? (event.metaKey || event.ctrlKey) : !event.metaKey && !event.ctrlKey)
          : (shortcut.ctrl ? event.ctrlKey : !event.ctrlKey) && (shortcut.meta ? false : !event.metaKey);

        if (keyMatch && modifierMatch && shiftMatch && altMatch) {
          event.preventDefault();
          shortcut.action();
          break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts]);
}

// Common keyboard shortcuts
export const COMMON_SHORTCUTS = {
  NEW_CHAT: { key: 'n', meta: true, description: 'New chat' },
  NEW_DOCUMENT: { key: 'n', meta: true, shift: true, description: 'New document' },
  SEARCH: { key: 'k', meta: true, description: 'Search / Command palette' },
  FOCUS_CHAT: { key: 'l', meta: true, description: 'Focus chat input' },
  ESCAPE: { key: 'Escape', description: 'Close modal / Cancel' },
  SAVE: { key: 's', meta: true, description: 'Save' },
  DELETE: { key: 'Delete', description: 'Delete selected' },
  ARROW_UP: { key: 'ArrowUp', description: 'Navigate up' },
  ARROW_DOWN: { key: 'ArrowDown', description: 'Navigate down' },
};

