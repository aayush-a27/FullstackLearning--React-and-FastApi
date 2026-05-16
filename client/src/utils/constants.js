// API Base URL
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// AI Models available for selection
export const AI_MODELS = [
  {
    id: 'gpt-4o',
    name: 'GPT-4o',
    provider: 'openai',
    description: 'Most capable OpenAI model',
    icon: '🧠',
    tier: 'premium',
  },
  {
    id: 'gpt-4o-mini',
    name: 'GPT-4o Mini',
    provider: 'openai',
    description: 'Fast and affordable',
    icon: '⚡',
    tier: 'standard',
  },
  {
    id: 'gemini-pro',
    name: 'Gemini Pro',
    provider: 'google',
    description: 'Google DeepMind model',
    icon: '💎',
    tier: 'premium',
  },
  {
    id: 'claude-sonnet',
    name: 'Claude Sonnet',
    provider: 'anthropic',
    description: 'Anthropic balanced model',
    icon: '🎯',
    tier: 'premium',
  },
  {
    id: 'llama-local',
    name: 'Llama (Local)',
    provider: 'ollama',
    description: 'Run locally via Ollama',
    icon: '🦙',
    tier: 'free',
  },
];

// Smart Switch complexity thresholds
export const COMPLEXITY = {
  SIMPLE: 'simple',       // Quick factual lookups → use mini/fast model
  MODERATE: 'moderate',   // Analysis, summaries → use standard model
  COMPLEX: 'complex',     // Deep reasoning, comparisons → use premium model
};

// PDF upload constraints (smart multi-PDF limits)
export const PDF_LIMITS = {
  MAX_FILE_SIZE_MB: 50,
  MAX_FILE_SIZE_BYTES: 50 * 1024 * 1024,
  // Page-count based multi-PDF rules
  SMALL_PDF_MAX_PAGES: 5,
  SMALL_PDF_MAX_FILES: 5,
  MEDIUM_PDF_MAX_PAGES: 30,
  MEDIUM_PDF_MAX_FILES: 2,
  LARGE_PDF_MAX_FILES: 1,
};

// Onboarding options
export const LANGUAGES = [
  'English', 'Hindi', 'Spanish', 'French', 'German',
  'Chinese', 'Japanese', 'Korean', 'Arabic', 'Portuguese',
];

export const PURPOSES = [
  { id: 'student_research', label: 'Student Research', icon: '🎓' },
  { id: 'deep_research', label: 'Deep Research', icon: '🔬' },
  { id: 'content_writing', label: 'Content Writing', icon: '✍️' },
  { id: 'legal_review', label: 'Legal Review', icon: '⚖️' },
  { id: 'business_analysis', label: 'Business Analysis', icon: '📊' },
  { id: 'personal_reading', label: 'Personal Reading', icon: '📚' },
];

// Route paths
export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  SIGNUP: '/signup',
  ONBOARDING: '/onboarding',
  DASHBOARD: '/dashboard',
  PROFILE: '/profile',
  SETTINGS: '/settings',
};
