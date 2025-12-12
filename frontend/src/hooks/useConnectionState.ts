import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../api/client';

export interface ConnectionState {
  isConnected: boolean;
  isChecking: boolean;
  lastChecked: Date | null;
  error: string | null;
}

export function useConnectionState(checkInterval: number = 30000) {
  const [state, setState] = useState<ConnectionState>({
    isConnected: false,
    isChecking: false,
    lastChecked: null,
    error: null,
  });

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isMountedRef = useRef(true);

  const checkConnection = useCallback(async () => {
    if (!isMountedRef.current) return;

    setState((prev) => ({ ...prev, isChecking: true, error: null }));

    try {
      // Use the API client's get method with retry disabled for health checks (silent mode)
      const response = await api.get<{ status: string }>('/health', undefined, false, 5000, true);

      if (response && response.status === 'ok') {
        setState({
          isConnected: true,
          isChecking: false,
          lastChecked: new Date(),
          error: null,
        });
      } else {
        setState({
          isConnected: false,
          isChecking: false,
          lastChecked: new Date(),
          error: 'Backend returned unexpected response',
        });
      }
    } catch (error: any) {
      if (!isMountedRef.current) return;

      const errorMessage = error?.detail || error?.message || 'Cannot connect to backend';
      setState({
        isConnected: false,
        isChecking: false,
        lastChecked: new Date(),
        error: typeof errorMessage === 'string' ? errorMessage : String(errorMessage),
      });
    }
  }, []);

  // Check connection on mount and periodically
  useEffect(() => {
    isMountedRef.current = true;
    checkConnection();

    intervalRef.current = setInterval(() => {
      if (isMountedRef.current) {
        checkConnection();
      }
    }, checkInterval);

    return () => {
      isMountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [checkConnection, checkInterval]);

  return {
    ...state,
    checkConnection,
  };
}
