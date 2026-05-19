// API Base URL
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// AI Models available for selection
export const AI_MODELS = [
  {
    id: 'gemini-pro',
    name: 'Gemini 2.5 Pro',
    provider: 'google',
    description: 'Best reasoning and long context',
    icon: '💎',
    tier: 'premium',
  },
  {
    id: 'gemini-flash',
    name: 'Gemini 2.5 Flash',
    provider: 'google',
    description: 'Fast and versatile',
    icon: '⚡',
    tier: 'standard',
  },
  {
    id: 'groq-llama3',
    name: 'Groq Llama-3',
    provider: 'groq',
    description: 'Lightning fast responses',
    icon: '🚀',
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
