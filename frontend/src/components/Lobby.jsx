import React, { useState } from 'react';

export default function Lobby({
  onCreateInvite,
  onJoinRandom,
  onJoinInvite,
  loading,
  error,
  session,
}) {
  const [name, setName] = useState('');
  const [inviteCode, setInviteCode] = useState('');

  const handle = async (action) => {
    if (loading) return;
    await action();
  };

  return (
    <div className="container">
      <div className="card stack">
        <header className="stack">
          <h1 className="section-title">Letsee Debate Lobby</h1>
          <p>Start a random match, create an invite code, or join an opponent directly.</p>
        </header>

        <div className="stack">
          <label htmlFor="name">Display Name</label>
          <input
            id="name"
            placeholder="Choose how others will see you"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </div>

        {error && <div className="alert">{error}</div>}

        <div className="row">
          <button className="primary" onClick={() => handle(() => onJoinRandom(name || 'Player'))}>
            {loading ? 'Joining…' : 'Join Random Match'}
          </button>
          <button className="secondary" onClick={() => handle(() => onCreateInvite(name || 'Host'))}>
            {loading ? 'Creating…' : 'Create Invite'}
          </button>
        </div>

        <div className="stack">
          <label htmlFor="code">Have an invite code?</label>
          <div className="row">
            <input
              id="code"
              placeholder="ABC123"
              value={inviteCode}
              onChange={(event) => setInviteCode(event.target.value.toUpperCase())}
            />
            <button
              className="primary"
              onClick={() => handle(() => onJoinInvite(inviteCode.trim(), name || 'Guest'))}
              disabled={!inviteCode || loading}
            >
              Join
            </button>
          </div>
        </div>

        {session && session.inviteCode && (
          <div className="card" style={{ background: '#eff6ff' }}>
            <h3>Invite Code</h3>
            <p>Share this code with your opponent:</p>
            <strong style={{ fontSize: '1.5rem' }}>{session.inviteCode}</strong>
          </div>
        )}
      </div>
    </div>
  );
}
