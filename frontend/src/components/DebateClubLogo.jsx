import React, { useMemo } from 'react';
import debateClubEmblem from '../assets/debate-club-logo.svg';

export default function DebateClubLogo({ className = '', animate = false }) {
  const classes = useMemo(
    () => ['debate-logo', animate ? 'debate-logo--animate' : '', className].filter(Boolean).join(' '),
    [animate, className]
  );

  return (
    <div className={classes} role="img" aria-label="Debate Club logo">
      <img src={debateClubEmblem} alt="Debate Club shield" className="debate-logo__image" loading="lazy" />
      <span className="sr-only">Debate Club</span>
    </div>
  );
}
