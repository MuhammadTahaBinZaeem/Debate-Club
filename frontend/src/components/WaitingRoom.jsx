import React, { useEffect, useState } from 'react';

export default function WaitingRoom({ session, onCancel, pendingTopic = null }) {
  const inviteCode = session?.inviteCode || '';
  const mode = session?.metadata?.mode || 'invite';
  const isRandomMatch = mode === 'random';
  const [copied, setCopied] = useState(false);
  const [pulse, setPulse] = useState(0);

  useEffect(() => {
    if (!copied) return undefined;
    const timeout = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(timeout);
  }, [copied]);

  useEffect(() => {
    if (!isRandomMatch) return undefined;
    const interval = setInterval(() => {
      setPulse((value) => (value + 1) % 3);
    }, 700);
    return () => clearInterval(interval);
  }, [isRandomMatch]);

  const handleCopy = async () => {
    if (!inviteCode) return;
    try {
      await navigator.clipboard.writeText(inviteCode);
    } catch (error) {
      // Fallback for environments without clipboard support
      const textArea = document.createElement('textarea');
      textArea.value = inviteCode;
      textArea.setAttribute('readonly', '');
      textArea.style.position = 'absolute';
      textArea.style.left = '-9999px';
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
    } finally {
      setCopied(true);
    }
  };

  return (
    <div className="waiting-wrapper">
      <div className="waiting-card">
        <div className="waiting-header">
          <div className="waiting-icon" aria-hidden="true">
            <span role="img" aria-label="session created">
              {isRandomMatch ? '🔍' : '👥'}
            </span>
          </div>
          <h2>{isRandomMatch ? 'Finding an Opponent…' : 'Session Created!'}</h2>
          <p>
            {isRandomMatch
              ? 'Hang tight while we locate another debater who also clicked “Find Opponent”.'
              : 'Waiting for your opponent to join.'}
          </p>
        </div>

        {!isRandomMatch && (
          <div className="waiting-share">
            <div className="waiting-share-header">
              <h3>Share This Code</h3>
              <p>Send this code to your debate opponent</p>
            </div>

            <div className="waiting-code-card">
              <span className="waiting-code-label">Session Code</span>
              <div className="waiting-code-row">
                <code className="waiting-code" aria-live="polite">
                  {inviteCode || '—'}
                </code>
                <button
                  type="button"
                  className="waiting-copy"
                  onClick={handleCopy}
                  disabled={!inviteCode}
                >
                  {copied ? 'Copied!' : 'Copy Code'}
                </button>
              </div>
            </div>
          </div>
        )}

        <div className={`waiting-status ${isRandomMatch ? 'waiting-status--random' : ''}`}>
          <div className="waiting-status-icon" aria-hidden="true">
            <span role="img" aria-label="hourglass">
              {isRandomMatch ? '⏱️' : '⏳'}
            </span>
          </div>
          <div className="waiting-status-body">
            <h3>{isRandomMatch ? 'Searching for Opponent' : 'Waiting for Opponent'}</h3>
            <p>
              {isRandomMatch
                ? 'Looking for the next available debater. You will be connected automatically once a match is found.'
                : 'Share the session code above with your opponent. The debate will start automatically once they join.'}
            </p>
            {isRandomMatch ? (
              <div className="waiting-search" aria-hidden="true">
                <div className={`waiting-pulse waiting-pulse--${pulse}`}>
                  <span />
                  <span />
                  <span />
                </div>
                <p className="waiting-search-status">Searching the lobby…</p>
              </div>
            ) : (
              pendingTopic && (
                <p>
                  <strong>Custom topic selected:</strong> {pendingTopic}
                </p>
              )
            )}
          </div>
        </div>

        <button type="button" className="waiting-cancel" onClick={onCancel}>
          Cancel Session
        </button>
      </div>
    </div>
  );
}
