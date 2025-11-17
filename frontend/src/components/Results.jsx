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
          {perArgument.map((entry) => (
            <div key={entry.turn} className="card" style={{ background: '#f8fafc' }}>
              <strong>
                Turn {entry.turn + 1} - {entry.role.toUpperCase()}
              </strong>
              <p>Score: {entry.score}</p>
              <p>{entry.feedback}</p>
            </div>
          ))}
        </div>

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
