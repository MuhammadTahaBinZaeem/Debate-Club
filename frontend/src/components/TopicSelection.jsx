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
  const vetoedTopics = new Set(
    Object.values(session?.participants || {})
      .map((participant) => participant?.vetoedTopic)
      .filter(Boolean)
  );
  const refreshLimit = session?.topicRefreshLimit ?? 0;
  const refreshesUsed = session?.topicRefreshes ?? 0;
  const refreshRemaining =
    refreshLimit > 0 ? Math.max(refreshLimit - refreshesUsed, 0) : null;
  const refreshDisabled =
    loading || (refreshLimit > 0 && refreshRemaining === 0);
  const refreshTitle =
    refreshLimit > 0 && refreshRemaining === 0
      ? 'You can only refresh topics once per debate session.'
      : undefined;

  return (
    <div className="container">
      <div className="card stack">
        <h2 className="section-title">Pick Tonight&apos;s Topic</h2>
        <p>Each side can veto one suggestion. The remaining topic will be debated.</p>
        <div className="topic-grid">
          {topics.map((topic) => {
            const isVetoed = vetoedTopics.has(topic);
            return (
              <div key={topic} className="topic-card">
                <p>{topic}</p>
                <button
                  className={`secondary${isVetoed ? ' vetoed' : ''}`}
                  onClick={() => onVeto?.(topic)}
                  disabled={loading || isVetoed}
                  aria-pressed={isVetoed}
                >
                  {isVetoed ? 'Vetoed' : 'Veto'}
                </button>
              </div>
            );
          })}
        </div>
        <button
          className="secondary"
          onClick={() => onRefresh?.()}
          disabled={refreshDisabled}
          title={refreshTitle}
        >
          {refreshDisabled && refreshLimit > 0 && refreshRemaining === 0
            ? 'Refresh Unavailable'
            : 'Refresh Suggestions'}
        </button>
        {refreshLimit > 0 && (
          <p style={{ fontSize: '0.9rem', color: '#475569' }}>
            {refreshRemaining !== null && refreshRemaining > 0
              ? `You can refresh ${refreshRemaining} more time${
                  refreshRemaining === 1 ? '' : 's'
                } this session.`
              : 'Topic suggestions have already been refreshed once this session.'}
          </p>
        )}

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
