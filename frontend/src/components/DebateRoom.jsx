import React, { useMemo, useState } from 'react';
import Timer from './Timer.jsx';

export default function DebateRoom({ session, role, debate = {}, onExit }) {
  const {
    messages = [],
    turnSeconds = null,
    totalSeconds = null,
    errors = [],
    warnings = [],
    status = 'idle',
    sendMessage = () => {},
    finish = () => {},
  } = debate;
  const [draft, setDraft] = useState('');

  const playerLabels = useMemo(() => {
    return {
      pro: session?.participants?.pro?.name?.trim() || 'Player 1',
      con: session?.participants?.con?.name?.trim() || 'Player 2',
    };
  }, [session?.participants]);

  const isMyTurn = useMemo(() => {
    if (!role) return false;
    return session?.currentTurn === role;
  }, [session?.currentTurn, role]);

  const yourAssignmentLabel = role
    ? `${playerLabels[role]} · ${role.toUpperCase()}`
    : 'Awaiting assignment';

  const speakerLabel = (message) => {
    const base = playerLabels[message.role] || message.speaker || 'Participant';
    const roleLabel = message.role ? message.role.toUpperCase() : '';
    return roleLabel ? `${base} · ${roleLabel}` : base;
  };

  const handleSend = (event) => {
    event.preventDefault();
    if (!draft.trim()) return;
    sendMessage(draft.trim());
    setDraft('');
  };

  return (
    <div className="container">
      <div className="card stack">
        <header className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 className="section-title">Debating: {session?.chosenTopic}</h2>
            <div className="role-pill" data-role={role || 'pending'}>
              <span className="role-pill__eyebrow">You are</span>
              <strong className="role-pill__value">{yourAssignmentLabel}</strong>
            </div>
          </div>
          <div className="row" style={{ gap: '0.75rem' }}>
            {totalSeconds !== null && <Timer label="Debate" seconds={totalSeconds} />}
            {turnSeconds !== null && <Timer label="Turn" seconds={turnSeconds} />}
          </div>
        </header>

        <div className="debate-players">
          {['pro', 'con'].map((debateRole) => (
            <div
              key={debateRole}
              className={`role-card ${debateRole === role ? 'active' : ''}`}
              data-role={debateRole}
            >
              <span className="role-card__label">{debateRole === 'pro' ? 'Player 1' : 'Player 2'}</span>
              <strong className="role-card__name">{playerLabels[debateRole]}</strong>
              <small className="role-card__role">{debateRole.toUpperCase()}</small>
            </div>
          ))}
        </div>

        {warnings.map((warning, index) => (
          <div key={`warning-${index}`} className="alert warning">
            <strong>
              Warning {warning.count}/{warning.maxWarnings}
            </strong>
            <p>{warning.message || 'Your last message was censored by the moderator.'}</p>
            {warning.censoredMessage && (
              <small style={{ display: 'block' }}>
                Sent message: {warning.censoredMessage}
              </small>
            )}
          </div>
        ))}

        {errors.map((error, index) => (
          <div key={index} className="alert">
            {error}
          </div>
        ))}

        <section className="transcript card" style={{ background: '#f8fafc' }}>
          {messages.map((message) => (
            <div key={message.turn} className="message">
              <strong>
                Turn {message.turn + 1}: {speakerLabel(message)}
              </strong>
              <p>{message.content}</p>
            </div>
          ))}
          {messages.length === 0 && <p>No arguments yet. Break the ice!</p>}
        </section>

        <form className="stack" onSubmit={handleSend}>
          <label htmlFor="argument">Your argument</label>
          <textarea
            id="argument"
            rows={4}
            placeholder={isMyTurn ? 'Craft your next point…' : 'Waiting for your opponent…'}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            disabled={!isMyTurn}
          />
          <div className="row">
            <button className="primary" type="submit" disabled={!isMyTurn || !draft.trim()}>
              Send argument
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => {
                finish();
                onExit?.();
              }}
            >
              End debate
            </button>
          </div>
        </form>

        {status === 'finished' && (
          <button className="primary" onClick={onExit}>
            View results
          </button>
        )}
      </div>
    </div>
  );
}
