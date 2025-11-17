import React, { useMemo, useState } from 'react';
import Timer from './Timer.jsx';

export default function DebateRoom({ session, role, debate = {}, onExit }) {
  const {
    messages = [],
    turnSeconds = null,
    totalSeconds = null,
    errors = [],
    status = 'idle',
    sendMessage = () => {},
    finish = () => {},
  } = debate;
  const [draft, setDraft] = useState('');

  const isMyTurn = useMemo(() => session?.currentTurn === role, [session?.currentTurn, role]);

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
            <p>Role: <strong>{role.toUpperCase()}</strong></p>
          </div>
          <div className="row" style={{ gap: '0.75rem' }}>
            {totalSeconds !== null && <Timer label="Debate" seconds={totalSeconds} />}
            {turnSeconds !== null && <Timer label="Turn" seconds={turnSeconds} />}
          </div>
        </header>

        {errors.map((error, index) => (
          <div key={index} className="alert">
            {error}
          </div>
        ))}

        <section className="transcript card" style={{ background: '#f8fafc' }}>
          {messages.map((message) => (
            <div key={message.turn} className="message">
              <strong>
                Turn {message.turn + 1}: {message.role.toUpperCase()} - {message.speaker}
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
