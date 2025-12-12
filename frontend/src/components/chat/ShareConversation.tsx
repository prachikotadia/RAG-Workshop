import { useState } from 'react';
import { chatApi } from '../../api/chat';
import { Icon } from '../common/Icon';

interface ShareConversationProps {
  sessionId: number;
}

export function ShareConversation({ sessionId }: ShareConversationProps) {
  const [shareLink, setShareLink] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expiresInDays, setExpiresInDays] = useState<number | undefined>(undefined);

  const handleCreateShare = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await chatApi.createShareLink(sessionId, expiresInDays);
      const fullUrl = `${window.location.origin}/shared/${result.token}`;
      setShareLink(fullUrl);
    } catch (err: any) {
      setError(err?.detail || 'Failed to create share link');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyLink = () => {
    if (shareLink) {
      navigator.clipboard.writeText(shareLink);
      // Show toast or notification
      alert('Link copied to clipboard!');
    }
  };

  return (
    <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-2 mb-4">
        <Icon name="arrow-right" size="sm" className="text-blue-500 dark:text-blue-400" />
        <h3 className="font-semibold text-gray-900 dark:text-white">Share Conversation</h3>
      </div>

      {!shareLink ? (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Expires in (days, optional)
            </label>
            <input
              type="number"
              value={expiresInDays || ''}
              onChange={(e) => setExpiresInDays(e.target.value ? parseInt(e.target.value) : undefined)}
              placeholder="Never expires"
              min="1"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
            />
          </div>

          <button
            onClick={handleCreateShare}
            disabled={loading}
            className="w-full px-4 py-2 bg-blue-500 hover:bg-blue-600 dark:bg-blue-400 dark:hover:bg-blue-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
          >
            {loading ? 'Creating...' : 'Create Share Link'}
          </button>

          {error && (
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Share Link:</p>
            <p className="text-sm font-mono text-gray-900 dark:text-white break-all">{shareLink}</p>
          </div>

          <button
            onClick={handleCopyLink}
            className="w-full px-4 py-2 bg-green-500 hover:bg-green-600 dark:bg-green-400 dark:hover:bg-green-500 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
          >
            <Icon name="check" size="sm" />
            Copy Link
          </button>

          <button
            onClick={() => setShareLink(null)}
            className="w-full px-4 py-2 bg-gray-500 hover:bg-gray-600 dark:bg-gray-400 dark:hover:bg-gray-500 text-white rounded-lg font-medium transition-colors"
          >
            Create New Link
          </button>
        </div>
      )}
    </div>
  );
}
