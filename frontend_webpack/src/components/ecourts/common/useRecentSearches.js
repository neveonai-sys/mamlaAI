import { useState, useCallback } from 'react';

const STORAGE_KEY = 'ecourts_recent_searches';
const MAX_PER_SECTION = 3;

function load() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
  } catch {
    return {};
  }
}

function persist(data) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

/**
 * Hook that tracks the last 3 searches per section in localStorage.
 *
 * @param {string} section  One of 'cases', 'lawyers', 'litigants', 'causelist'
 * @returns {{ recent: Array<{query, timestamp, meta?}>, addSearch, clearSection }}
 */
export default function useRecentSearches(section) {
  const [recent, setRecent] = useState(() => (load()[section] || []));

  const addSearch = useCallback((query, meta) => {
    if (!query || !query.trim()) return;
    const all = load();
    const list = all[section] || [];

    const filtered = list.filter(
      (item) => item.query.toLowerCase() !== query.trim().toLowerCase(),
    );
    filtered.unshift({ query: query.trim(), timestamp: Date.now(), meta });
    all[section] = filtered.slice(0, MAX_PER_SECTION);

    persist(all);
    setRecent(all[section]);
  }, [section]);

  const clearSection = useCallback(() => {
    const all = load();
    delete all[section];
    persist(all);
    setRecent([]);
  }, [section]);

  return { recent, addSearch, clearSection };
}
