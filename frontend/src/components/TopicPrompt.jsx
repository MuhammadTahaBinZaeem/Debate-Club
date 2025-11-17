import React, { useState } from 'react';

export default function TopicPrompt({ onUseCustom, onPickRandom, initialTopic = '' }) {
  const [topic, setTopic] = useState(initialTopic);
  const trimmed = topic.trim();

  return (
    <div className="container">
      <div className="card stack">
        <header className="stack" style={{ gap: '0.5rem' }}>
          <h2 className="section-title">Choose Your Debate Topic</h2>
          <p>
            Set the tone for the debate by entering a custom prompt or let the system suggest random
            topics for both sides to veto.
          </p>
        </header>

        <div className="stack">
          <label htmlFor="custom-topic">Enter a custom topic (optional)</label>
          <textarea
            id="custom-topic"
            rows={4}
            placeholder="Type the statement you want to debate"
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
          />
          <button
            type="button"
            className="primary"
            onClick={() => onUseCustom?.(trimmed)}
            disabled={!trimmed}
          >
            Use This Topic
          </button>
        </div>

        <div className="card" style={{ background: '#f8fafc' }}>
          <h3>Prefer suggestions?</h3>
          <p>Pick a random set of prompts and decide together with the veto system.</p>
          <button type="button" className="secondary" onClick={() => onPickRandom?.()}>
            Use Random Suggestions
          </button>
        </div>
      </div>
    </div>
  );
}
