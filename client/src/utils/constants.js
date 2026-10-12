// API Base URL
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// AI Models available for selection
export const AI_MODELS = [
  {
    id: 'nemotron-super',
    name: 'Nemotron Super 120B',
    provider: 'nvidia',
    description: 'Best reasoning for complex questions',
    icon: '💎',
    tier: 'premium',
  },
  {
    id: 'gemini-flash',
    name: 'Gemini Flash',
    provider: 'google',
    description: 'Fast, versatile, long context',
    icon: '⚡',
    tier: 'standard',
  },
  {
    id: 'groq-fast',
    name: 'Groq GPT-OSS 20B',
    provider: 'groq',
    description: 'Lightning fast responses',
    icon: '🚀',
    tier: 'free',
  },
];

// PDF upload constraints (smart multi-PDF limits)
export const PDF_LIMITS = {
  MAX_FILE_SIZE_MB: 15,                  // keep in step with the server's MAX_PDF_SIZE_MB
  MAX_FILE_SIZE_BYTES: 15 * 1024 * 1024,
  // Page-count based multi-PDF rules
  SMALL_PDF_MAX_PAGES: 5,
  SMALL_PDF_MAX_FILES: 5,
  MEDIUM_PDF_MAX_PAGES: 30,
  MEDIUM_PDF_MAX_FILES: 2,
  LARGE_PDF_MAX_FILES: 1,
};

// Route paths
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  SIGNUP: '/signup',
  DASHBOARD: '/dashboard',
  CHAT: '/chat/:chatId',
  PROFILE: '/profile',
  SETTINGS: '/settings',
};

/** Shareable URL for one chat. */
export const chatPath = (chatId) => `/chat/${chatId}`;

/** Routes shown as a modal on top of the chat layout. */
export const MODAL_ROUTES = [ROUTES.PROFILE, ROUTES.SETTINGS];
