/**
 * Cross-tab session isolation via localStorage fingerprint.
 *
 * Each login stores a unique `auth_session_id` (the backend session UUID)
 * in localStorage. A `StorageEvent` listener detects when another tab
 * changes or clears this key, triggering forced re-authentication.
 */

const SESSION_KEY = "auth_session_id";

let currentSessionId: string | null = null;

/** Store the session fingerprint in memory and localStorage. */
export function setSessionFingerprint(sessionId: string): void {
  currentSessionId = sessionId;
  localStorage.setItem(SESSION_KEY, sessionId);
}

/** Initialize the in-memory fingerprint from localStorage on app boot. */
export function initSessionFingerprint(): void {
  currentSessionId = localStorage.getItem(SESSION_KEY);
}

/** Clear both in-memory and stored fingerprint. */
export function clearSessionFingerprint(): void {
  currentSessionId = null;
  localStorage.removeItem(SESSION_KEY);
}

/**
 * Start listening for cross-tab session changes.
 * Returns a cleanup function to remove the listener.
 *
 * The `storage` event only fires in OTHER tabs (not the one that wrote),
 * which is exactly the behavior we need.
 */
export function startSessionGuard(onSessionChanged: () => void): () => void {
  function handleStorageChange(event: StorageEvent): void {
    if (event.key !== SESSION_KEY) return;

    // Session cleared from another tab (logout)
    if (event.newValue === null) {
      onSessionChanged();
      return;
    }

    // Session changed to a different value (new login from another tab)
    if (currentSessionId && event.newValue !== currentSessionId) {
      onSessionChanged();
    }
  }

  window.addEventListener("storage", handleStorageChange);
  return () => window.removeEventListener("storage", handleStorageChange);
}
