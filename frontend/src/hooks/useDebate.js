import { useCallback, useEffect, useRef, useState } from 'react';
import {
  completeCoinToss as emitCoinTossComplete,
  createDebateSocket,
  endDebate,
  sendDebateMessage,
  submitCustomTopic,
  vetoTopic,
} from '../api/debate.js';
import { useApiConfig } from '../components/ApiContext.jsx';

export function useDebate(session, role, onSessionUpdate) {
  const { socketUrl } = useApiConfig();
  const socketRef = useRef(null);
  const [messages, setMessages] = useState(session?.transcript || []);
  const [turnSeconds, setTurnSeconds] = useState(null);
  const [totalSeconds, setTotalSeconds] = useState(null);
  const [errors, setErrors] = useState([]);
  const [warnings, setWarnings] = useState([]);
  const [status, setStatus] = useState('idle');

  useEffect(() => {
    setMessages(session?.transcript || []);
    setWarnings([]);
  }, [session?.sessionId]);

  useEffect(() => {
    if (!session || session.status !== 'debating') {
      setTotalSeconds(null);
    }
  }, [session?.sessionId, session?.status]);

  useEffect(() => {
    if (session?.transcript) {
      setMessages(session.transcript);
    }
  }, [session?.transcript]);

  useEffect(() => {
    if (!session || !role) return;
    const socket = createDebateSocket(socketUrl, session.sessionId, role, {
      onSessionUpdate: (payload) => {
        onSessionUpdate?.(payload);
      },
      onTopicSelected: () => {
        setStatus('coin_toss');
      },
      onDebateStarted: (payload) => {
        onSessionUpdate?.(payload);
        setStatus('debating');
      },
      onMessage: (payload) => {
        setMessages((prev) => [...prev, payload]);
      },
      onTurnTimer: ({ seconds }) => {
        setTurnSeconds(seconds);
      },
      onTotalTimer: ({ seconds }) => {
        setTotalSeconds(seconds);
      },
      onTurnExpired: () => {
        setErrors((prev) => [...prev, 'Turn timer expired']);
        setTurnSeconds(0);
      },
      onTotalExpired: () => {
        setErrors((prev) => [...prev, 'Overall debate timer expired']);
        setTotalSeconds(0);
      },
      onDebateFinished: (payload) => {
        onSessionUpdate?.(payload);
        setStatus('finished');
      },
      onError: ({ message }) => {
        if (message) setErrors((prev) => [...prev, message]);
      },
      onModerationWarning: (payload) => {
        setWarnings((prev) => [...prev, payload]);
      },
    });
    socketRef.current = socket;
    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [session?.sessionId, role, socketUrl, onSessionUpdate]);

  const sendMessage = useCallback((message) => {
    if (!socketRef.current) return;
    sendDebateMessage(socketRef.current, message);
  }, []);

  const veto = useCallback((topic) => {
    if (!socketRef.current) return;
    vetoTopic(socketRef.current, topic);
  }, []);

  const submitTopic = useCallback((topic) => {
    if (!socketRef.current) return;
    submitCustomTopic(socketRef.current, topic);
  }, []);

  const finish = useCallback(() => {
    if (!socketRef.current) return;
    endDebate(socketRef.current);
  }, []);

  const completeCoinToss = useCallback(() => {
    if (!socketRef.current) return;
    emitCoinTossComplete(socketRef.current);
  }, []);

  return {
    messages,
    turnSeconds,
    totalSeconds,
    errors,
    warnings,
    status,
    sendMessage,
    veto,
    submitTopic,
    finish,
    completeCoinToss,
  };
}
