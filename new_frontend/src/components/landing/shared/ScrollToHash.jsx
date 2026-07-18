import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

// React Router v6 does not auto-scroll to #hash targets on navigation.
// This mounts once at app root: on every location change it scrolls the
// matching element into view (or to top when there is no hash), so footer/nav
// links like /about#contact land on the right section.
export default function ScrollToHash() {
  const { pathname, hash } = useLocation();

  useEffect(() => {
    if (hash) {
      // Defer so the destination page (and its sections) has mounted.
      const id = hash.replace('#', '');
      const tryScroll = () => {
        const el = document.getElementById(id);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      };
      const t = setTimeout(tryScroll, 60);
      return () => clearTimeout(t);
    }
    window.scrollTo(0, 0);
  }, [pathname, hash]);

  return null;
}
