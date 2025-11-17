import React, { useEffect, useMemo, useRef, useState } from 'react';

export default function CoinToss({ session, onComplete, playerName }) {
  const [phase, setPhase] = useState('waiting');
  const hasCompletedRef = useRef(false);
  const hasStartedRef = useRef(false);

  const result = session?.metadata?.coinToss || null;
  const completed = Boolean(session?.metadata?.coinTossCompleted);

  const normalizedPlayerName = useMemo(
    () => (playerName || '').trim().toLowerCase(),
    [playerName]
  );

  const playerSide = useMemo(() => {
    if (!result || !normalizedPlayerName) return null;
    const pro = (result.pro || '').trim().toLowerCase();
    const con = (result.con || '').trim().toLowerCase();
    if (pro && pro === normalizedPlayerName) return 'Pro';
    if (con && con === normalizedPlayerName) return 'Con';
    return null;
  }, [result, normalizedPlayerName]);

  useEffect(() => {
    setPhase('waiting');
    hasCompletedRef.current = false;
    hasStartedRef.current = false;
  }, [session?.sessionId]);

  useEffect(() => {
    if (!result) return undefined;
    if (completed) {
      setPhase('revealed');
      return undefined;
    }
    if (hasStartedRef.current) return undefined;
    hasStartedRef.current = true;
    setPhase('flipping');
    const timer = setTimeout(() => {
      setPhase('revealed');
    }, 2500);
    return () => clearTimeout(timer);
  }, [result, completed]);

  useEffect(() => {
    if (phase !== 'revealed' || !result || hasCompletedRef.current) {
      return;
    }
    const { pro, con } = result;
    const lines = [
      'Coin toss result!',
      `Pro: ${pro || 'TBD'}`,
      `Con: ${con || 'TBD'}`,
    ];
    if (playerSide) {
      lines.push(`You will argue as the ${playerSide.toUpperCase()} side.`);
    }
    // Notify the players of their assigned roles with a simple alert.
    if (typeof window !== 'undefined' && typeof window.alert === 'function') {
      window.alert(lines.join('\n'));
    }
    hasCompletedRef.current = true;
    onComplete?.();
  }, [phase, result, onComplete, playerSide]);

  return (
    <div className="coin-toss-wrapper">
      <div className="coin-toss-card">
        <h2>Coin Toss</h2>
        <p className="coin-toss-subtitle">
          Determining which side each debater will take for this topic.
        </p>
        <div
          className={`coin-toss-coin ${
            phase === 'flipping' ? 'flipping' : phase === 'revealed' ? 'revealed' : ''
          }`}
          aria-live="polite"
        >
          {phase === 'revealed' ? '⚖️' : '🪙'}
        </div>
        <div className="coin-toss-status" aria-live="polite">
          {phase === 'flipping' && <p>The coin is in the air...</p>}
          {phase !== 'flipping' && !result && <p>Waiting for both debaters...</p>}
          {phase === 'revealed' && result && (
            <>
              <p className="coin-toss-highlight">
                {playerSide
                  ? `You will argue as the ${playerSide.toUpperCase()} side.`
                  : 'Here are the assignments for this round.'}
              </p>
              <div className="coin-toss-result">
                <div
                  className={`coin-toss-role pro ${
                    playerSide === 'Pro' ? 'me' : ''
                  }`}
                >
                  <span className="coin-toss-role-label">Pro</span>
                  <strong>{result.pro || 'TBD'}</strong>
                </div>
                <div
                  className={`coin-toss-role con ${
                    playerSide === 'Con' ? 'me' : ''
                  }`}
                >
                  <span className="coin-toss-role-label">Con</span>
                  <strong>{result.con || 'TBD'}</strong>
                </div>
              </div>
            </>
          )}
          {phase !== 'revealed' && result && <p>Preparing the results...</p>}
        </div>
      </div>
    </div>
  );
}
