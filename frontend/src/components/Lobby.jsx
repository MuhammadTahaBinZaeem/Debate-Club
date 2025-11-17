import React, { useState } from 'react';

export default function Lobby({
  onCreateInvite,
  onJoinRandom,
  onJoinInvite,
  loading,
  error,
  session,
}) {
  const [inviteCode, setInviteCode] = useState('');

  const handle = async (action) => {
    if (loading) return;
    await action();
  };

  return (
    <div className="landing">
      <section className="hero">
        <h1 className="hero-title">Debate Platform</h1>
        <p className="hero-subtitle">
          Engage in real-time anonymous debates with intelligent judging and turn-based gameplay
        </p>
      </section>

      {error && <div className="alert">{error}</div>}

      <section className="action-grid">
        <div className="action-card">
          <div className="action-icon" aria-hidden="true">
            <span>🎯</span>
          </div>
          <div className="action-body">
            <h2>Create Session</h2>
            <p>Start a new debate session with custom settings.</p>
          </div>
          <button className="card-button" onClick={() => handle(() => onCreateInvite('Host'))}>
            {loading ? 'Creating…' : 'Create New Session'}
          </button>
        </div>

        <div className="action-card">
          <div className="action-icon" aria-hidden="true">
            <span>🔐</span>
          </div>
          <div className="action-body">
            <h2>Join by Code</h2>
            <p>Enter a session code to participate directly.</p>
          </div>
          <div className="input-group">
            <label htmlFor="session-code">Session Code</label>
            <input
              id="session-code"
              placeholder="12-character code"
              value={inviteCode}
              onChange={(event) => setInviteCode(event.target.value.toUpperCase())}
            />
          </div>
          <button
            className="card-button"
            onClick={() => handle(() => onJoinInvite(inviteCode.trim(), 'Guest'))}
            disabled={!inviteCode || loading}
          >
            {loading ? 'Joining…' : 'Join Session'}
          </button>
          {session && session.inviteCode && (
            <div className="invite-pill">
              <span>Share this code:</span>
              <strong>{session.inviteCode}</strong>
            </div>
          )}
        </div>

        <div className="action-card">
          <div className="action-icon" aria-hidden="true">
            <span>🤝</span>
          </div>
          <div className="action-body">
            <h2>Random Match</h2>
            <p>Get paired with an available opponent.</p>
          </div>
          <button className="card-button" onClick={() => handle(() => onJoinRandom('Player'))}>
            {loading ? 'Matching…' : 'Find Opponent'}
          </button>
        </div>
      </section>

      <section className="how-it-works">
        <h2>How It Works</h2>
        <div className="steps">
          <div className="step">
            <div className="step-icon" aria-hidden="true">
              <span>🆕</span>
            </div>
            <h3>Create/Join</h3>
            <p>Start a new debate or join via invite code.</p>
          </div>
          <div className="step">
            <div className="step-icon" aria-hidden="true">
              <span>🗂️</span>
            </div>
            <h3>Select Topic</h3>
            <p>Choose from curated prompts or submit your own.</p>
          </div>
          <div className="step">
            <div className="step-icon" aria-hidden="true">
              <span>🔄</span>
            </div>
            <h3>Debate Turns</h3>
            <p>Alternate timed turns with structured arguments.</p>
          </div>
          <div className="step">
            <div className="step-icon" aria-hidden="true">
              <span>⚖️</span>
            </div>
            <h3>Get Judgement</h3>
            <p>Receive AI-assisted scoring with instant feedback.</p>
          </div>
        </div>

        <div className="feature-grid">
          <div className="feature-card">
            <h3>Real-time Timers</h3>
            <p>Serve turn-based structure with automatic reminders and precision scoring.</p>
          </div>
          <div className="feature-card">
            <h3>Anonymous Sessions</h3>
            <p>Engage with masked identities to keep debates focused on ideas and reasoning.</p>
          </div>
          <div className="feature-card">
            <h3>AI Judging</h3>
            <p>Receive algorithmic analysis with multi-criteria scoring and reasoning breakdowns.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
