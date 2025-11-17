import React from 'react';
import DebateClubLogo from './DebateClubLogo.jsx';

export default function LoadingScreen({ visible }) {
  return (
    <div className={`loading-screen ${visible ? 'loading-screen--visible' : 'loading-screen--hidden'}`} role="status">
      <div className="loading-screen__content">
        <DebateClubLogo animate />
        <div className="loading-title">
          <span>Debate Club</span>
          <small>Where arguments take the spotlight</small>
        </div>
        <div className="loading-wave" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </div>
      <p className="loading-tagline">Setting the stage for spirited discourse…</p>
    </div>
  );
}
