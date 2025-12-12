/**
 * LocalStorage utilities with error handling and type safety
 */

const STORAGE_PREFIX = 'rag_workspace_';

export class Storage {
  private static getKey(key: string): string {
    return `${STORAGE_PREFIX}${key}`;
  }

  static setItem(key: string, value: string): boolean {
    try {
      localStorage.setItem(this.getKey(key), value);
      return true;
    } catch (error) {
      console.error(`Failed to set localStorage item ${key}:`, error);
      return false;
    }
  }

  static getItem(key: string): string | null {
    try {
      return localStorage.getItem(this.getKey(key));
    } catch (error) {
      console.error(`Failed to get localStorage item ${key}:`, error);
      return null;
    }
  }

  static removeItem(key: string): boolean {
    try {
      localStorage.removeItem(this.getKey(key));
      return true;
    } catch (error) {
      console.error(`Failed to remove localStorage item ${key}:`, error);
      return false;
    }
  }

  static clear(): boolean {
    try {
      const keys = Object.keys(localStorage);
      keys.forEach((key) => {
        if (key.startsWith(STORAGE_PREFIX)) {
          localStorage.removeItem(key);
        }
      });
      return true;
    } catch (error) {
      console.error('Failed to clear localStorage:', error);
      return false;
    }
  }

  // Token-specific methods
  static setToken(token: string): boolean {
    return this.setItem('access_token', token);
  }

  static getToken(): string | null {
    return this.getItem('access_token');
  }

  static removeToken(): boolean {
    return this.removeItem('access_token');
  }

  // Session persistence
  static setSessionData(data: { user?: any; timestamp?: number }): boolean {
    try {
      const sessionData = {
        ...data,
        timestamp: Date.now(),
      };
      return this.setItem('session_data', JSON.stringify(sessionData));
    } catch (error) {
      console.error('Failed to set session data:', error);
      return false;
    }
  }

  static getSessionData(): { user?: any; timestamp?: number } | null {
    try {
      const data = this.getItem('session_data');
      if (!data) return null;
      const parsed = JSON.parse(data);
      // Check if session is still valid (24 hours)
      if (parsed.timestamp && Date.now() - parsed.timestamp > 24 * 60 * 60 * 1000) {
        this.removeItem('session_data');
        return null;
      }
      return parsed;
    } catch (error) {
      console.error('Failed to get session data:', error);
      return null;
    }
  }

  static clearSession(): boolean {
    return this.removeItem('session_data');
  }
}
