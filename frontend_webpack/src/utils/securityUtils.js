/**
 * Security Utilities
 */

// ⚠️ Browser-safe key (no process.env)
const SECURITY_KEY =
  document
    .querySelector('meta[name="security-key"]')
    ?.getAttribute('content') ||
  'dev-key-change-me';

/**
 * Obfuscates sensitive data before storing
 */
export const obfuscateData = (data) => {
  if (!data) return '';
  try {
    return btoa(encodeURIComponent(JSON.stringify(data)))
      .split('')
      .map(char =>
        String.fromCharCode(char.charCodeAt(0) ^ SECURITY_KEY.charCodeAt(0))
      )
      .join('');
  } catch {
    return '';
  }
};

/**
 * Deobfuscates stored data
 */
export const deobfuscateData = (obfuscated) => {
  if (!obfuscated) return null;
  try {
    const deobfuscated = obfuscated
      .split('')
      .map(char =>
        String.fromCharCode(char.charCodeAt(0) ^ SECURITY_KEY.charCodeAt(0))
      )
      .join('');
    return JSON.parse(decodeURIComponent(atob(deobfuscated)));
  } catch {
    return null;
  }
};

/**
 * Sanitizes user input
 */
export const sanitizeInput = (input = '') =>
  input
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');

/**
 * Email validation
 */
export const isValidEmail = (email) =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email).toLowerCase());

/**
 * Password strength validation
 */
export const isStrongPassword = (password) =>
  /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$/.test(password);

/**
 * Secure storage wrapper
 */
export const createSecureStorage = (storage) => ({
  setItem(key, value) {
    const secured = obfuscateData(
      typeof value === 'string' ? { data: value } : value
    );
    storage.setItem(key, secured);
  },
  getItem(key) {
    const item = storage.getItem(key);
    if (!item) return null;
    const result = deobfuscateData(item);
    return result?.data ?? result;
  },
  removeItem(key) {
    storage.removeItem(key);
  },
  clear() {
    storage.clear();
  },
});

export const secureLocalStorage = createSecureStorage(localStorage);
export const secureSessionStorage = createSecureStorage(sessionStorage);
