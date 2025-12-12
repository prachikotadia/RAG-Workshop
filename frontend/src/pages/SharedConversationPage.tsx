import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { chatApi } from '../api/chat';
import { ChatMessageBubble } from '../components/chat/ChatMessageBubble';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { Icon } from '../components/common/Icon';

export function SharedConversationPage() {
  const { token } = useParams<{ token: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [conversation, setConversation] = useState<any>(null);

  useEffect(() => {
    const loadConversation = async () => {
      if (!token) {
        setError('Invalid share token');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const data = await chatApi.getSharedConversation(token);
        setConversation(data);
      } catch (err: any) {
        setError(err?.detail || 'Failed to load shared conversation');
      } finally {
        setLoading(false);
      }
    };

    loadConversation();
  }, [token]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="text-center">
          <LoadingSpinner size="lg" className="mb-4" />
          <div className="text-gray-500 dark:text-gray-400">Loading shared conversation...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="text-center bg-white dark:bg-gray-800 rounded-xl p-8 border border-gray-200 dark:border-gray-700 max-w-md">
          <Icon name="error" size="xl" className="text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Error</h2>
          <p className="text-gray-600 dark:text-gray-400">{error}</p>
        </div>
      </div>
    );
  }

  if (!conversation) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 mb-6 border border-gray-200 dark:border-gray-700 shadow-soft">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {conversation.session.title || 'Shared Conversation'}
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Shared conversation • {conversation.access_count} view{conversation.access_count !== 1 ? 's' : ''}
              </p>
            </div>
            <div className="flex items-center gap-2 px-3 py-1 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Icon name="check" size="sm" className="text-blue-500 dark:text-blue-400" />
              <span className="text-sm font-medium text-blue-700 dark:text-blue-300">Read-Only</span>
            </div>
          </div>
          {conversation.expires_at && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Expires: {new Date(conversation.expires_at).toLocaleString()}
            </p>
          )}
        </div>

        {/* Messages */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-soft">
          <div className="space-y-4">
            {conversation.messages.map((message: any) => (
              <ChatMessageBubble key={message.id} message={message} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
