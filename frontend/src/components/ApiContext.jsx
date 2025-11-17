import React, { createContext, useContext, useMemo } from 'react';

const ApiContext = createContext({ baseUrl: '', socketUrl: '' });

export function ApiProvider({ children }) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
  const socketUrl = import.meta.env.VITE_SOCKET_URL || 'http://localhost:8000';

  const value = useMemo(() => ({ baseUrl, socketUrl }), [baseUrl, socketUrl]);
  return <ApiContext.Provider value={value}>{children}</ApiContext.Provider>;
}

export function useApiConfig() {
  return useContext(ApiContext);
}

export default ApiContext;
