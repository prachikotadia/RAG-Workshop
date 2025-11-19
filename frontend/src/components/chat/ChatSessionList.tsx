import { ChatSession } from '../../api/chat';
import { SidebarChatHistory } from './SidebarChatHistory';

interface ChatSessionListProps {
  sessions: ChatSession[];
  selectedSessionId: number | null;
  onSelectSession: (sessionId: number) => void;
  onCreateNew: () => void;
  onDeleteSession?: (sessionId: number) => void;
  onDeleteAll?: () => void;
  loading?: boolean;
}

export function ChatSessionList(props: ChatSessionListProps) {
  return <SidebarChatHistory {...props} />;
}
