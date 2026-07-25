export const COOKIE_NAME = 'cookie_preferences';
export const STORAGE_KEY = 'mamla_cookie_preferences';
export const COOKIE_VERSION = '1.0';
export const DEFAULT_PREFERENCES = {
  necessary: true,
  analytics: false,
  marketing: false,
  personalization: false,
};

function parseCookie(name) {
  if (typeof document === 'undefined') return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return parts.pop().split(';').shift();
  }
  return null;
}

export function getStoredConsent() {
  try {
    if (typeof window === 'undefined') return null;
    const raw = window.localStorage.getItem(STORAGE_KEY) || parseCookie(COOKIE_NAME);
    if (!raw) return null;
    const parsed = JSON.parse(decodeURIComponent(raw));
    if (!parsed || typeof parsed !== 'object') return null;
    return parsed;
  } catch (error) {
    console.error('Failed to read stored cookie consent:', error);
    return null;
  }
}

export function saveConsentToLocal(preferences) {
  const payload = {
    version: COOKIE_VERSION,
    preferences,
  };
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  } catch (error) {
    console.warn('Unable to save cookie consent to localStorage', error);
  }
  try {
    const encoded = encodeURIComponent(JSON.stringify(payload));
    document.cookie = `${COOKIE_NAME}=${encoded}; Path=/; Max-Age=${60 * 60 * 24 * 365}; SameSite=Lax`;
  } catch (error) {
    console.warn('Unable to save cookie consent to cookie', error);
  }
}
