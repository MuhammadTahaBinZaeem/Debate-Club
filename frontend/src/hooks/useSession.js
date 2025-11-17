import { useCallback, useState } from 'react';
import {
  createInviteSession,
  joinInviteSession,
  joinRandomSession,
  fetchSession,
  fetchTopics,
  chooseTopic,
  finalizeSession,
} from '../api/session.js';
import { useApiConfig } from '../components/ApiContext.jsx';

export function useSession() {
  const { baseUrl } = useApiConfig();
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const wrap = useCallback(
    async (fn) => {
      setLoading(true);
      setError(null);
      try {
        const next = await fn();
        setSession(next);
        return next;
      } catch (err) {
        setError(err.message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [baseUrl]
  );

  const createInvite = useCallback(
    (name) => wrap(() => createInviteSession(baseUrl, name)),
    [wrap, baseUrl]
  );

  const joinRandom = useCallback(
    (name) => wrap(() => joinRandomSession(baseUrl, name)),
    [wrap, baseUrl]
  );

  const joinInvite = useCallback(
    (code, name) => wrap(() => joinInviteSession(baseUrl, code, name)),
    [wrap, baseUrl]
  );

  const refresh = useCallback(
    (sessionId) => wrap(() => fetchSession(baseUrl, sessionId)),
    [wrap, baseUrl]
  );

  const loadTopics = useCallback(
    async (sessionId, refresh = false) => {
      setError(null);
      try {
        return await fetchTopics(baseUrl, sessionId, refresh);
      } catch (err) {
        setError(err.message);
        throw err;
      }
    },
    [baseUrl]
  );

  const selectTopic = useCallback(
    (sessionId, topic, custom = false) => wrap(() => chooseTopic(baseUrl, sessionId, topic, custom)),
    [wrap, baseUrl]
  );

  const finalize = useCallback(
    (sessionId) => wrap(() => finalizeSession(baseUrl, sessionId)),
    [wrap, baseUrl]
  );

  return {
    session,
    setSession,
    loading,
    error,
    createInvite,
    joinRandom,
    joinInvite,
    refresh,
    loadTopics,
    selectTopic,
    finalize,
  };
}
