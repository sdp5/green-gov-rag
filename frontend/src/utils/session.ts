/**
 * Session management utilities for user-specific query history.
 *
 * Generates and persists a unique session ID in localStorage to track
 * queries per browser/user without requiring authentication.
 */

const SESSION_KEY = 'greengovrag_session_id';

/**
 * Get or create a session ID for the current browser.
 *
 * @returns {string} UUID session ID
 */
export const getOrCreateSessionId = (): string => {
  // Check if session ID already exists
  let sessionId = localStorage.getItem(SESSION_KEY);

  if (!sessionId) {
    // Generate new UUID v4
    sessionId = crypto.randomUUID();
    localStorage.setItem(SESSION_KEY, sessionId);
    console.log('[Session] Created new session ID:', sessionId);
  }

  return sessionId;
};

/**
 * Clear the current session ID (useful for testing or logout).
 */
export const clearSessionId = (): void => {
  localStorage.removeItem(SESSION_KEY);
  console.log('[Session] Cleared session ID');
};

/**
 * Get current session ID without creating a new one.
 *
 * @returns {string | null} Session ID or null if not exists
 */
export const getSessionId = (): string | null => {
  return localStorage.getItem(SESSION_KEY);
};