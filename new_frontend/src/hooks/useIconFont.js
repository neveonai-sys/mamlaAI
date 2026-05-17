import { useEffect } from 'react';

const MATERIAL_SYMBOLS_URL =
  'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=block';

/**
 * Lazily injects the Material Symbols Outlined font stylesheet once into <head>.
 * Safe to call from multiple components — duplicate links are never added.
 */
export function useIconFont() {
  useEffect(() => {
    if (document.querySelector(`link[href="${MATERIAL_SYMBOLS_URL}"]`)) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = MATERIAL_SYMBOLS_URL;
    document.head.appendChild(link);
  }, []);
}
