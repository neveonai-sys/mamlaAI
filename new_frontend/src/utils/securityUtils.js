/**
 * securityUtils.js
 * Obfuscation wrappers around localStorage / sessionStorage.
 * Same contract as the Adalatai reference app.
 */

const KEY_ROTATION_PREFIX = 'mml_';

function caesar(str, shift) {
  return str
    .split('')
    .map((ch) => String.fromCharCode(ch.charCodeAt(0) + shift))
    .join('');
}

function obfuscate(value) {
  try {
    const json = JSON.stringify(value);
    return btoa(caesar(json, 3));
  } catch {
    return null;
  }
}

function deobfuscate(raw) {
  try {
    const json = caesar(atob(raw), -3);
    return JSON.parse(json);
  } catch {
    return null;
  }
}

function makeKey(key) {
  return KEY_ROTATION_PREFIX + btoa(key);
}

// Public helpers
export function obfuscateData(value) {
  return obfuscate(value);
}

export const secureLocalStorage = {
  setItem(key, value) {
    try {
      window.localStorage.setItem(makeKey(key), obfuscate(value));
    } catch {
      /* quota or private mode */
    }
  },
  getItem(key) {
    try {
      const raw = window.localStorage.getItem(makeKey(key));
      return raw ? deobfuscate(raw) : null;
    } catch {
      return null;
    }
  },
  removeItem(key) {
    try {
      window.localStorage.removeItem(makeKey(key));
    } catch {
      /* ignore */
    }
  },
  clear() {
    try {
      const toDelete = [];
      for (let i = 0; i < window.localStorage.length; i++) {
        const k = window.localStorage.key(i);
        if (k && k.startsWith(KEY_ROTATION_PREFIX)) toDelete.push(k);
      }
      toDelete.forEach((k) => window.localStorage.removeItem(k));
    } catch {
      /* ignore */
    }
  },
};

export const secureSessionStorage = {
  setItem(key, value) {
    try {
      window.sessionStorage.setItem(makeKey(key), obfuscate(value));
    } catch {
      /* ignore */
    }
  },
  getItem(key) {
    try {
      const raw = window.sessionStorage.getItem(makeKey(key));
      return raw ? deobfuscate(raw) : null;
    } catch {
      return null;
    }
  },
  removeItem(key) {
    try {
      window.sessionStorage.removeItem(makeKey(key));
    } catch {
      /* ignore */
    }
  },
};
