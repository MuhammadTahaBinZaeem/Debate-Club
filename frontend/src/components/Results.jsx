import React from 'react';

export default function Results({ session, onDownload, onRestart }) {
  const result = session?.result;
  if (!result) {
    return (
      <div className="container">
        <div className="card">
          <p>Waiting for AI judge…</p>
        </div>
      </div>
    );
  }

  const perArgument = result.perArgument || [];
  const review = result.review || {};
  const participants = session?.participants || {};
  const overallHighlights = review.overallHighlights || [];
  const overallImprovements = review.overallImprovements || [];
  const hasOverallLists = overallHighlights.length > 0 || overallImprovements.length > 0;
  const hasReview =
    !!review.overall ||
    hasOverallLists ||
    (review.pro &&
      (review.pro.strengths?.length || review.pro.improvements?.length || review.pro.summary)) ||
    (review.con &&
      (review.con.strengths?.length || review.con.improvements?.length || review.con.summary));

  return (
    <div className="container">
      <div className="card stack">
        <h2 className="section-title">Results</h2>
        <p>Winner: <strong>{result.winner.toUpperCase()}</strong></p>
        <p>{result.rationale}</p>

        <div className="card" style={{ background: '#eff6ff' }}>
          <h3>Scores</h3>
          <ul>
            {Object.entries(result.overall || {}).map(([role, score]) => (
              <li key={role}>
                {role.toUpperCase()}: {score}
              </li>
            ))}
          </ul>
        </div>

        <div className="stack">
          <h3>Argument feedback</h3>
          {perArgument.map((entry) => {
            const turnNumber =
              typeof entry.turn === 'number'
                ? entry.turn + 1
                : entry.turn ?? '—';
            return (
              <div key={`${entry.turn}-${entry.role}`} className="card" style={{ background: '#f8fafc' }}>
                <strong>
                  Turn {turnNumber} - {entry.role?.toUpperCase?.() || entry.role}
                </strong>
                <p>Score: {entry.score}</p>
                {entry.rating && <p>Rating: {entry.rating}</p>}
                <p>{entry.feedback}</p>
              </div>
            );
          })}
        </div>

        {hasReview && (
          <div className="stack">
            <h3>Debate review</h3>
            {['pro', 'con'].map((roleKey) => {
              const roleReview = review[roleKey] || {};
              const participant = participants[roleKey] || {};
              const label = roleKey === 'pro' ? 'Proponent' : 'Opponent';
              const strengths = roleReview.strengths || [];
              const improvements = roleReview.improvements || [];
              const summary = roleReview.summary;
              if (!strengths.length && !improvements.length && !summary) {
                return null;
              }
              return (
                <div key={roleKey} className="card" style={{ background: '#fff7ed' }}>
                  <strong>
                    {label} ({participant.name || 'Participant'})
                  </strong>
                  {summary && <p style={{ fontStyle: 'italic' }}>{summary}</p>}
                  {strengths.length > 0 && (
                    <div>
                      <p><strong>What went well</strong></p>
                      <ul>
                        {strengths.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {improvements.length > 0 && (
                    <div>
                      <p><strong>Opportunities to improve</strong></p>
                      <ul>
                        {improvements.map((item, idx) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
            {hasOverallLists && (
              <div className="card" style={{ background: '#f0fdf4' }}>
                <strong>Overall highlights</strong>
                {overallHighlights.length > 0 && (
                  <ul>
                    {overallHighlights.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                )}
                {overallImprovements.length > 0 && (
                  <div>
                    <p><strong>Overall growth areas</strong></p>
                    <ul>
                      {overallImprovements.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
            {review.overall && (
              <div className="card" style={{ background: '#eef2ff' }}>
                <strong>Overall assessment</strong>
                <p>{review.overall}</p>
              </div>
            )}
          </div>
        )}

        <div className="row">
          <button className="primary" onClick={onDownload}>
            Download PDF
          </button>
          <button className="secondary" onClick={onRestart}>
            Return to lobby
          </button>
        </div>
      </div>
    </div>
  );
}
