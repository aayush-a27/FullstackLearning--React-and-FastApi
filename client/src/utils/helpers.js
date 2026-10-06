import { PDF_LIMITS } from './constants';

/**
 * Calculate how many more PDFs can be added to a chat based on existing PDFs' page counts.
 * Rules:
 *   - All PDFs ≤5 pages → allow up to 5 total
 *   - Any PDF 6-30 pages → allow up to 2 total
 *   - Any PDF >30 pages → only 1 PDF allowed
 */
export function getMaxPdfsAllowed(existingPdfs = []) {
  if (existingPdfs.length === 0) return PDF_LIMITS.SMALL_PDF_MAX_FILES;

  const maxPages = Math.max(...existingPdfs.map((p) => p.page_count || 0));

  if (maxPages > PDF_LIMITS.MEDIUM_PDF_MAX_PAGES) return PDF_LIMITS.LARGE_PDF_MAX_FILES;
  if (maxPages > PDF_LIMITS.SMALL_PDF_MAX_PAGES) return PDF_LIMITS.MEDIUM_PDF_MAX_FILES;
  return PDF_LIMITS.SMALL_PDF_MAX_FILES;
}

/**
 * Check if a new PDF can be added to the existing set.
 */
export function canAddPdf(existingPdfs, newPdfPageCount) {
  const allPdfs = [...existingPdfs, { page_count: newPdfPageCount }];
  const maxAllowed = getMaxPdfsAllowed(allPdfs);
  return allPdfs.length <= maxAllowed;
}

/**
 * Format file size from bytes to human-readable string.
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 B';
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
}

/**
 * Truncate text with ellipsis.
 */
export function truncate(text, maxLength = 50) {
  if (!text || text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

/**
 * Format a date to relative time (e.g., "2 hours ago").
 */
export function timeAgo(date) {
  const now = new Date();
  const past = new Date(date);
  const diffMs = now - past;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return past.toLocaleDateString();
}

/**
 * Generate initials from a name (e.g., "John Doe" → "JD").
 */
export function getInitials(name) {
  if (!name) return '?';
  return name
    .split(' ')
    .map((word) => word[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

/**
 * Turn an axios error into a short, user-friendly message.
 * Backend `detail` strings for 4xx/503 are written for end users; anything
 * else (500s, validation arrays, network failures) gets a generic message.
 */
export function getFriendlyError(err, fallback = 'Something went wrong. Please try again.') {
  if (err?.code === 'ECONNABORTED') {
    return 'This is taking longer than expected. Please try again.';
  }
  if (!err?.response) {
    return "Can't reach the server. Check your connection and try again.";
  }
  const { status, data } = err.response;
  const detail = typeof data?.detail === 'string' ? data.detail : null;
  if (detail && (status < 500 || status === 503)) {
    return detail;
  }
  return fallback;
}
