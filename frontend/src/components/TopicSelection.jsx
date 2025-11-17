import React, { useState } from 'react';

export default function TopicSelection({
  topics = [],
  session,
  onRefresh,
  onVeto,
  onCustomTopic,
  loading,
  canUseCustom,
}) {
  const [customTopic, setCustomTopic] = useState('');

  return (
    <div className="container">
      <div className="card stack">
        <h2 className="section-title">Pick Tonight&apos;s Topic</h2>
        <p>Each side can veto one suggestion. The remaining topic will be debated.</p>
        <div className="topic-grid">
          {topics.map((topic) => (
            <div key={topic} className="topic-card">
              <p>{topic}</p>
              <button className="secondary" onClick={() => onVeto?.(topic)} disabled={loading}>
                Veto
              </button>
            </div>
          ))}
        </div>
        <button className="secondary" onClick={() => onRefresh?.()} disabled={loading}>
          Refresh Suggestions
        </button>

        {canUseCustom && (
          <div className="stack">
            <label htmlFor="custom-topic">Prefer a custom topic?</label>
            <textarea
              id="custom-topic"
              rows={3}
              placeholder="Type a topic both debaters agreed on"
              value={customTopic}
              onChange={(event) => setCustomTopic(event.target.value)}
            />
            <button
              className="primary"
              onClick={() => onCustomTopic?.(customTopic)}
              disabled={!customTopic.trim()}
            >
              Use Custom Topic
            </button>
          </div>
        )}

        <div className="card" style={{ background: '#f1f5f9' }}>
          <h4>Status</h4>
          <p>Current selection: {session.chosenTopic || 'pending'}</p>
        </div>
      </div>
    </div>
  );
}
