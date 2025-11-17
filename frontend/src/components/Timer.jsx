import React, { useEffect, useState } from 'react';

export default function Timer({ seconds, label }) {
  const [remaining, setRemaining] = useState(seconds || 0);

  useEffect(() => {
    setRemaining(seconds || 0);
  }, [seconds]);

  useEffect(() => {
    if (remaining <= 0) return;
    const interval = setInterval(() => {
      setRemaining((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [remaining]);

  return (
    <div className="timer">
      <span role="img" aria-label="timer">
        ⏱️
      </span>
      <span>{label}: {remaining}s</span>
    </div>
  );
}
