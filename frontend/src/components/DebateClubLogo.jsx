import React, { useMemo } from 'react';

export default function DebateClubLogo({ className = '', animate = false }) {
  const classes = useMemo(
    () => ['debate-logo', animate ? 'debate-logo--animate' : '', className].filter(Boolean).join(' '),
    [animate, className]
  );

  return (
    <div className={classes}>
      <svg viewBox="0 0 160 160" role="img" aria-label="Debate Club logo" focusable="false">
        <defs>
          <linearGradient id="debateGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#60a5fa" />
            <stop offset="45%" stopColor="#6366f1" />
            <stop offset="100%" stopColor="#a855f7" />
          </linearGradient>
          <linearGradient id="debateGradientSecondary" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#fbbf24" />
            <stop offset="100%" stopColor="#ef4444" />
          </linearGradient>
        </defs>
        <circle cx="80" cy="80" r="70" fill="url(#debateGradient)" opacity="0.18" />
        <path
          d="M48 52c0-12.15 9.85-22 22-22h26c12.15 0 22 9.85 22 22v24c0 12.15-9.85 22-22 22h-4.6l-13.35 11.24c-2.06 1.73-5.05.27-5.05-2.39V98H70c-12.15 0-22-9.85-22-22V52z"
          fill="white"
          opacity="0.95"
        />
        <path
          d="M68 70c0-9.94 8.06-18 18-18h16c9.94 0 18 8.06 18 18v18c0 9.94-8.06 18-18 18h-2.5l-7.94 7.18c-1.73 1.57-4.56.32-4.56-1.95V106H86c-9.94 0-18-8.06-18-18V70z"
          fill="url(#debateGradientSecondary)"
        />
        <circle cx="90" cy="84" r="6" fill="white" opacity="0.95" />
        <circle cx="114" cy="84" r="6" fill="white" opacity="0.95" />
        <path d="M96 104c5.6 6 15.4 6 21 0" stroke="white" strokeWidth="5" strokeLinecap="round" fill="none" />
      </svg>
      <div className="debate-logo__text">
        <span>Debate</span>
        <span>Club</span>
      </div>
    </div>
  );
}
