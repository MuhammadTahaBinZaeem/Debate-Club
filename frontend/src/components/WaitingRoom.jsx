import React, { useEffect, useState } from 'react';

export default function WaitingRoom({ session, onCancel, pendingTopic = null }) {
  const inviteCode = session?.inviteCode || '';
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!copied) return undefined;
    const timeout = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(timeout);
  }, [copied]);

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
              👥
            </span>
          </div>
          <h2>Session Created!</h2>
          <p>Waiting for your opponent to join.</p>
        </div>

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

        <div className="waiting-status">
          <div className="waiting-status-icon" aria-hidden="true">
            <span role="img" aria-label="hourglass">
              ⏳
            </span>
          </div>
          <div className="waiting-status-body">
            <h3>Waiting for Opponent</h3>
            <p>
              Share the session code above with your opponent. The debate will start automatically once they
              join.
            </p>
            {pendingTopic && (
              <p>
                <strong>Custom topic selected:</strong> {pendingTopic}
              </p>
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
