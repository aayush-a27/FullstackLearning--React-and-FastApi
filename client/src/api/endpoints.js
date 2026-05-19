// ===== API ENDPOINTS =====

export const AUTH = {
  LOGIN: '/auth/login',
  REGISTER: '/auth/register',
  LOGOUT: '/auth/logout',
  REFRESH: '/auth/refresh',
};

export const USERS = {
  ME: '/users/me',
  ONBOARDING: '/users/me/onboarding',
  UPDATE_PROFILE: '/users/me',
};

export const CHATS = {
  LIST: '/chats',
  CREATE: '/chats',
  GET: (id) => `/chats/${id}`,
  DELETE: (id) => `/chats/${id}`,
  UPDATE: (id) => `/chats/${id}`,
};

export const MESSAGES = {
  LIST: (chatId) => `/chats/${chatId}/messages`,
  SEND: (chatId) => `/chats/${chatId}/messages`,
};

export const PDFS = {
  UPLOAD: '/pdfs/upload',
  LIST: '/pdfs',
  GET: (id) => `/pdfs/${id}`,
  DELETE: (id) => `/pdfs/${id}`,
  ATTACH: (chatId) => `/chats/${chatId}/pdfs`,
  VIEW: (id) => `/pdfs/${id}/view`,
};

export const MODELS = {
  LIST: '/models',
  HEALTH: '/models/health',
};
