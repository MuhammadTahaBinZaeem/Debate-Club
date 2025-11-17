async function request(baseUrl, path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.error || 'Request failed');
  }
  return response.json();
}

export function createInviteSession(baseUrl, name) {
  return request(baseUrl, '/sessions/create', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

export function joinRandomSession(baseUrl, name) {
  return request(baseUrl, '/sessions/join/random', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

export function joinInviteSession(baseUrl, code, name) {
  return request(baseUrl, '/sessions/join/invite', {
    method: 'POST',
    body: JSON.stringify({ code, name }),
  });
}

export function fetchSession(baseUrl, sessionId) {
  return request(baseUrl, `/sessions/${sessionId}`);
}

export function fetchTopics(baseUrl, sessionId) {
  return request(baseUrl, `/topics/${sessionId}`);
}

export function chooseTopic(baseUrl, sessionId, topic, custom = false) {
  return request(baseUrl, `/sessions/${sessionId}/topic`, {
    method: 'POST',
    body: JSON.stringify({ topic, custom }),
  });
}

export function finalizeSession(baseUrl, sessionId) {
  return request(baseUrl, `/sessions/${sessionId}/finish`, {
    method: 'POST',
  });
}
