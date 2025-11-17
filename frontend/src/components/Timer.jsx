import React, { useEffect, useMemo, useState } from 'react';

export default function Timer({ seconds, label }) {
  const [remaining, setRemaining] = useState(Math.max(seconds || 0, 0));

  useEffect(() => {
    setRemaining(Math.max(seconds || 0, 0));
  }, [seconds]);

  useEffect(() => {
    if (remaining <= 0) return undefined;
    const interval = setInterval(() => {
      setRemaining((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [remaining]);

  const formatted = useMemo(() => {
    const minutes = Math.floor(remaining / 60);
    const secs = remaining % 60;
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  }, [remaining]);

  return (
    <div className="timer">
      <span role="img" aria-label="timer">
        ⏱️
      </span>
      <span>{label}: {formatted}</span>
    </div>
  );
}
