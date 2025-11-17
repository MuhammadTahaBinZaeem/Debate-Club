import React, { useCallback, useEffect, useMemo, useState } from 'react';
import Lobby from './components/Lobby.jsx';
import TopicSelection from './components/TopicSelection.jsx';
import DebateRoom from './components/DebateRoom.jsx';
import Results from './components/Results.jsx';
import { ApiProvider, useApiConfig } from './components/ApiContext.jsx';
import { useSession } from './hooks/useSession.js';
import { useDebate } from './hooks/useDebate.js';
import { downloadTranscript } from './api/export.js';

function deriveRole(session, playerName) {
  if (!session || !session.participants) return null;
  const entries = Object.entries(session.participants);
  const lower = (playerName || '').toLowerCase();
  for (const [role, participant] of entries) {
    if ((participant.name || '').toLowerCase() === lower) {
      return role;
    }
  }
  if (entries.length === 1) {
    return entries[0][0];
  }
  return null;
}

function AppContent() {
  const {
    session,
    setSession,
    loading,
    error,
    createInvite,
    joinRandom,
    joinInvite,
    loadTopics,
    finalize,
  } = useSession();
  const [playerName, setPlayerName] = useState('');
  const [playerRole, setPlayerRole] = useState(null);
  const [topics, setTopics] = useState([]);
  const [view, setView] = useState('lobby');
  const { baseUrl } = useApiConfig();

  const handleSessionUpdate = useCallback(
    (payload) => {
      setSession(payload);
    },
    [setSession]
  );

  const debate = useDebate(session, playerRole, handleSessionUpdate);

  useEffect(() => {
    if (!session || !playerName) return;
    const derived = deriveRole(session, playerName);
    if (derived && derived !== playerRole) {
      setPlayerRole(derived);
    }
  }, [session?.participants, playerName]);

  const sessionId = session?.sessionId;

  const fetchTopics = useCallback(async () => {
    if (!sessionId) return;
    const response = await loadTopics(sessionId);
    setTopics(response.topics);
    setSession((prev) => (prev ? { ...prev, topicOptions: response.topics } : prev));
  }, [sessionId, loadTopics, setSession]);

  useEffect(() => {
    if (!session) {
      setView('lobby');
      return;
    }
    switch (session.status) {
      case 'lobby':
        setView('waiting');
        break;
      case 'veto':
        setView('topics');
        break;
      case 'debating':
        setView('debate');
        break;
      case 'finished':
        setView('results');
        break;
      default:
        setView('lobby');
    }
  }, [session?.status]);

  useEffect(() => {
    if (view === 'topics' && session && session.topicOptions?.length) {
      setTopics(session.topicOptions);
    } else if (view === 'topics' && session && (!session.topicOptions || session.topicOptions.length === 0)) {
      fetchTopics();
    }
  }, [view, session?.topicOptions, fetchTopics]);

  useEffect(() => {
    if (debate.status === 'finished' && session) {
      finalize(session.sessionId);
    }
  }, [debate.status, session?.sessionId]);

  const handleCreateInvite = async (name) => {
    setPlayerName(name);
    const next = await createInvite(name);
    setPlayerRole('pro');
    setTopics([]);
    setView(next.status === 'veto' ? 'topics' : 'waiting');
  };

  const handleJoinRandom = async (name) => {
    setPlayerName(name);
    const next = await joinRandom(name);
    setPlayerRole(deriveRole(next, name) || 'pro');
    if (next.topicOptions?.length) setTopics(next.topicOptions);
  };

  const handleJoinInvite = async (code, name) => {
    setPlayerName(name);
    const next = await joinInvite(code, name);
    setPlayerRole(deriveRole(next, name) || 'con');
    if (next.topicOptions?.length) setTopics(next.topicOptions);
  };

  const handleCustomTopic = async (topic) => {
    if (!topic.trim()) return;
    debate.submitTopic(topic.trim());
  };

  const handleRestart = () => {
    setSession(null);
    setPlayerName('');
    setPlayerRole(null);
    setTopics([]);
    setView('lobby');
  };

  const rendered = useMemo(() => {
    if (view === 'lobby') {
      return (
        <Lobby
          onCreateInvite={handleCreateInvite}
          onJoinRandom={handleJoinRandom}
          onJoinInvite={handleJoinInvite}
          loading={loading}
          error={error}
          session={session}
        />
      );
    }
    if (view === 'waiting') {
      return (
        <div className="container">
          <div className="card stack">
            <h2 className="section-title">Waiting for opponent…</h2>
            {session?.inviteCode && (
              <p>
                Share invite code <strong>{session.inviteCode}</strong>
              </p>
            )}
            <p>We will notify you once both participants are ready.</p>
            <button className="secondary" onClick={handleRestart}>
              Leave lobby
            </button>
          </div>
        </div>
      );
    }
    if (view === 'topics') {
      return (
        <TopicSelection
          topics={topics}
          session={session}
          loading={loading}
          onRefresh={fetchTopics}
          onVeto={debate.veto}
          onCustomTopic={handleCustomTopic}
          canUseCustom={session?.metadata?.mode === 'invite'}
        />
      );
    }
    if (view === 'debate') {
      return (
        <DebateRoom
          session={session}
          role={playerRole}
          debate={debate}
          onExit={() => setView('results')}
        />
      );
    }
    if (view === 'results') {
      return (
        <Results
          session={session}
          onDownload={() => downloadTranscript(baseUrl, session.sessionId)}
          onRestart={handleRestart}
        />
      );
    }
    return null;
  }, [view, session, topics, loading, error, debate, playerRole, fetchTopics, baseUrl, handleRestart]);

  return rendered;
}

export default function App() {
  return (
    <ApiProvider>
      <AppContent />
    </ApiProvider>
  );
}
