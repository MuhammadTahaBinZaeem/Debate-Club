import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Lobby from './components/Lobby.jsx';
import TopicSelection from './components/TopicSelection.jsx';
import DebateRoom from './components/DebateRoom.jsx';
import Results from './components/Results.jsx';
import WaitingRoom from './components/WaitingRoom.jsx';
import TopicPrompt from './components/TopicPrompt.jsx';
import LoadingScreen from './components/LoadingScreen.jsx';
import { ApiProvider, useApiConfig } from './components/ApiContext.jsx';
import { useSession } from './hooks/useSession.js';
import { useDebate } from './hooks/useDebate.js';
import { downloadTranscript } from './api/export.js';

function deriveRole(session, playerName) {
  if (!session || !session.participants) return null;
  const entries = Object.entries(session.participants);
  const lower = (playerName || '').toLowerCase();
  const matches = entries.filter(([, participant]) => (participant.name || '').toLowerCase() === lower);
  if (matches.length === 1) {
    return matches[0][0];
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
  const [showTopicPrompt, setShowTopicPrompt] = useState(false);
  const [pendingCustomTopic, setPendingCustomTopic] = useState(null);
  const [roleToast, setRoleToast] = useState(null);
  const [roleModal, setRoleModal] = useState(null);
  const roleToastTimerRef = useRef(null);
  const lastRoleAssignmentRef = useRef(null);
  const coinTossCompletionRef = useRef(false);
  const { baseUrl } = useApiConfig();
  const pendingTopicRef = useRef(pendingCustomTopic);

  useEffect(() => {
    pendingTopicRef.current = pendingCustomTopic;
  }, [pendingCustomTopic]);

  const handleSessionUpdate = useCallback(
    (payload) => {
      setSession(payload);
    },
    [setSession]
  );

  const debate = useDebate(session, playerRole, handleSessionUpdate);
  const submitDebateTopic = debate.submitTopic;

  useEffect(() => {
    if (!session || !playerName) return;
    const derived = deriveRole(session, playerName);
    if (derived && derived !== playerRole) {
      setPlayerRole(derived);
    }
  }, [session?.participants, playerName]);

  const sessionId = session?.sessionId;

  const fetchTopics = useCallback(
    async (refresh = false) => {
      if (!sessionId) return;
      try {
        const response = await loadTopics(sessionId, refresh);
        setTopics(response.topics);
        setSession((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            topicOptions: response.topics,
            topicRefreshes:
              response.refreshesUsed ?? prev.topicRefreshes ?? 0,
            topicRefreshLimit:
              response.refreshLimit ?? prev.topicRefreshLimit ?? 1,
          };
        });
      } catch (err) {
        console.error('Failed to load topics', err);
      }
    },
    [sessionId, loadTopics, setSession]
  );

  useEffect(() => {
    if (!session) {
      setView('lobby');
      setShowTopicPrompt(false);
      setPendingCustomTopic(null);
      setRoleToast(null);
      setRoleModal(null);
      lastRoleAssignmentRef.current = null;
      coinTossCompletionRef.current = false;
      return;
    }
    switch (session.status) {
      case 'lobby':
        setView(showTopicPrompt ? 'topicPrompt' : 'waiting');
        break;
      case 'veto':
        setView(pendingTopicRef.current ? 'waiting' : 'topics');
        break;
      case 'coin_toss':
        setView('waiting');
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
  }, [session?.status, showTopicPrompt]);

  useEffect(() => {
    const assignments = session?.metadata?.coinToss;
    if (!assignments || !playerName) return;

    const normalizedPlayer = playerName.trim().toLowerCase();
    const normalizedPro = (assignments.pro || '').trim().toLowerCase();
    const normalizedCon = (assignments.con || '').trim().toLowerCase();

    let assignedRole = null;
    if (normalizedPlayer && normalizedPlayer === normalizedPro) {
      assignedRole = 'pro';
    } else if (normalizedPlayer && normalizedPlayer === normalizedCon) {
      assignedRole = 'con';
    }

    if (!assignedRole || lastRoleAssignmentRef.current === assignedRole) {
      return;
    }

    lastRoleAssignmentRef.current = assignedRole;
    setPlayerRole(assignedRole);

    const readable = assignedRole === 'pro' ? 'Player 1 (PRO)' : 'Player 2 (CON)';
    const message = `You will argue as ${readable}.`;
    announceRoleAssignment(message);
    setRoleModal({
      title: assignedRole === 'pro' ? 'You are Player 1' : 'You are Player 2',
      message,
    });
  }, [session?.metadata?.coinToss, session?.sessionId, playerName, announceRoleAssignment]);

  const completeCoinToss = debate?.completeCoinToss;

  useEffect(() => {
    if (session?.status !== 'coin_toss') {
      coinTossCompletionRef.current = false;
      return;
    }
    if (!session?.metadata?.coinToss || !completeCoinToss || coinTossCompletionRef.current) {
      return;
    }
    completeCoinToss();
    coinTossCompletionRef.current = true;
  }, [session?.status, session?.metadata?.coinToss, completeCoinToss]);

  useEffect(() => {
    return () => {
      if (roleToastTimerRef.current) {
        clearTimeout(roleToastTimerRef.current);
      }
    };
  }, []);

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
    setPendingCustomTopic(null);
    setShowTopicPrompt(true);
    setView('topicPrompt');
  };

  const handleJoinRandom = async (name) => {
    setPlayerName(name);
    const next = await joinRandom(name);
    const participants = next?.participants || {};
    const participantRoles = Object.keys(participants);
    let assignedRole = null;

    if (participantRoles.length === 1) {
      assignedRole = participantRoles[0];
    } else if (participantRoles.includes('pro') && participantRoles.includes('con')) {
      assignedRole = 'con';
    } else if (participantRoles.length > 0) {
      [assignedRole] = participantRoles;
    }

    const normalizedRole = assignedRole || deriveRole(next, name) || 'pro';
    setPlayerRole(normalizedRole);
    const assignedParticipant = participants[normalizedRole];
    if (assignedParticipant?.name) {
      setPlayerName(assignedParticipant.name);
    }
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

  const handlePromptRandom = useCallback(() => {
    setPendingCustomTopic(null);
    setShowTopicPrompt(false);
    setView('waiting');
  }, []);

  const handlePromptCustom = useCallback((topic) => {
    if (!topic) return;
    setPendingCustomTopic(topic);
    setShowTopicPrompt(false);
    setView('waiting');
  }, []);

  useEffect(() => {
    if (
      !session ||
      session.status !== 'veto' ||
      !pendingCustomTopic ||
      playerRole !== 'pro'
    ) {
      return;
    }
    const participantCount = Object.keys(session.participants || {}).length;
    if (participantCount < 2) return;
    submitDebateTopic(pendingCustomTopic);
    setPendingCustomTopic(null);
  }, [session?.status, session?.participants, pendingCustomTopic, playerRole, submitDebateTopic]);

  const handleRestart = () => {
    setSession(null);
    setPlayerName('');
    setPlayerRole(null);
    setTopics([]);
    setPendingCustomTopic(null);
    setShowTopicPrompt(false);
    if (roleToastTimerRef.current) {
      clearTimeout(roleToastTimerRef.current);
    }
    setRoleToast(null);
    setRoleModal(null);
    lastRoleAssignmentRef.current = null;
    coinTossCompletionRef.current = false;
    setView('lobby');
  };

  const announceRoleAssignment = useCallback((message) => {
    if (!message) return;
    setRoleToast(message);
    if (roleToastTimerRef.current) {
      clearTimeout(roleToastTimerRef.current);
    }
    roleToastTimerRef.current = setTimeout(() => setRoleToast(null), 3200);
  }, []);

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
        <WaitingRoom
          session={session}
          onCancel={handleRestart}
          pendingTopic={playerRole === 'pro' ? pendingCustomTopic : null}
        />
      );
    }
    if (view === 'topicPrompt') {
      return (
        <TopicPrompt
          onUseCustom={handlePromptCustom}
          onPickRandom={handlePromptRandom}
          initialTopic={pendingCustomTopic || ''}
        />
      );
    }
    if (view === 'topics') {
      return (
        <TopicSelection
          topics={topics}
          session={session}
          loading={loading}
          onRefresh={() => fetchTopics(true)}
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
  }, [
    view,
    session,
    topics,
    loading,
    error,
    debate,
    playerRole,
    fetchTopics,
    baseUrl,
    handleRestart,
    handleCreateInvite,
    handleJoinRandom,
    handleJoinInvite,
    handlePromptCustom,
    handlePromptRandom,
    announceRoleAssignment,
    pendingCustomTopic,
  ]);

  return (
    <>
      {rendered}
      {roleModal && (
        <div className="role-modal" role="dialog" aria-modal="true" aria-live="assertive">
          <div className="role-modal__card">
            <p className="role-modal__eyebrow">Assignment ready</p>
            <h3>{roleModal.title}</h3>
            <p>{roleModal.message}</p>
            <button type="button" className="primary" onClick={() => setRoleModal(null)}>
              Let&apos;s debate
            </button>
          </div>
        </div>
      )}
      {roleToast && (
        <div className="role-toast" role="status" aria-live="polite">
          {roleToast}
        </div>
      )}
    </>
  );
}

function AppWithIntro() {
  const [showLoader, setShowLoader] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setShowLoader(false), 2400);
    return () => clearTimeout(timer);
  }, []);

  return (
    <>
      <LoadingScreen visible={showLoader} />
      <div className={`app-shell ${showLoader ? '' : 'app-shell--ready'}`}>
        <AppContent />
      </div>
    </>
  );
}

export default function App() {
  return (
    <ApiProvider>
      <AppWithIntro />
    </ApiProvider>
  );
}
