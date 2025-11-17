import { io } from 'socket.io-client';

export function createDebateSocket(socketUrl, sessionId, role, handlers = {}) {
  const socket = io(socketUrl, {
    transports: ['websocket'],
    autoConnect: true,
  });

  socket.on('connect', () => {
    socket.emit('join_session', { sessionId, role });
  });

  const eventMap = {
    'session:update': 'onSessionUpdate',
    'topic:vetoed': 'onTopicVetoed',
    'topic:selected': 'onTopicSelected',
    'debate:started': 'onDebateStarted',
    'message:new': 'onMessage',
    'timer:turn': 'onTurnTimer',
    'timer:total': 'onTotalTimer',
    'timer:turnExpired': 'onTurnExpired',
    'timer:totalExpired': 'onTotalExpired',
    'debate:finished': 'onDebateFinished',
    'session:error': 'onError',
  };

  Object.entries(eventMap).forEach(([event, handlerName]) => {
    const handler = handlers[handlerName];
    if (handler) {
      socket.on(event, handler);
    }
  });

  return socket;
}

export function vetoTopic(socket, topic) {
  socket.emit('veto_topic', { topic });
}

export function submitCustomTopic(socket, topic) {
  socket.emit('set_custom_topic', { topic });
}

export function sendDebateMessage(socket, message) {
  socket.emit('send_message', { message });
}

export function endDebate(socket) {
  socket.emit('end_debate');
}

export function completeCoinToss(socket) {
  socket.emit('coin_toss_complete');
}
