import React from 'react';
import { createRoot, hydrateRoot } from 'react-dom/client';
import { Provider } from 'react-redux';
import { HelmetProvider } from 'react-helmet-async';
import { store } from './store';
import App from './App';
import ErrorBoundary from './components/common/ErrorBoundary';
import './index.css';

import posthog from 'posthog-js';
import { PostHogProvider, PostHogErrorBoundary } from '@posthog/react';
import { getStoredConsent } from './utils/cookieConsent';

// On some Android devices (Samsung Secure Folder, WebView, strict privacy mode)
// accessing window.sessionStorage or window.localStorage throws a SecurityError.
// Detect this upfront so PostHog can fall back to in-memory persistence.
function storageAvailable(type) {
  try {
    const s = window[type];
    s.setItem('__ph_test__', '1');
    s.removeItem('__ph_test__');
    return true;
  } catch {
    return false;
  }
}
const phPersistence = storageAvailable('localStorage') ? 'localStorage+cookie' : 'memory';

posthog.init(process.env.REACT_APP_POSTHOG_KEY, {
  // Route through our own domain so ad blockers don't block eu.i.posthog.com
  api_host: process.env.REACT_APP_POSTHOG_HOST || 'https://eu.i.posthog.com',
  ui_host: 'https://eu.posthog.com',
  defaults: '2026-01-30',
  autocapture: false,
  capture_pageview: false,
  disable_session_recording: true,
  persistence: phPersistence,
  // Analytics is an "Optional" cookie category per our Cookie Policy — no
  // event should transmit until the user has explicitly opted in via the
  // consent banner. See CookieConsentBanner.jsx for the opt-in/opt-out calls.
  opt_out_capturing_by_default: true,
});

// Returning visitor who already chose "Accept" for analytics: activate
// capturing immediately so they aren't silently untracked forever, without
// re-showing the consent banner (CookieConsentBanner.jsx only renders when
// no stored decision exists).
const storedConsent = getStoredConsent();
if (storedConsent?.preferences?.analytics) {
  posthog.opt_in_capturing();
}

const container = document.getElementById('root');

const tree = (
  <React.StrictMode>
    <PostHogProvider client={posthog}>
      <PostHogErrorBoundary>
        <ErrorBoundary>
          <Provider store={store}>
            <HelmetProvider>
              <App />
            </HelmetProvider>
          </Provider>
        </ErrorBoundary>
      </PostHogErrorBoundary>
    </PostHogProvider>
  </React.StrictMode>
);

// `react-snap` prerenders the hub pages to static HTML at build time. When that
// prerendered markup is present we hydrate it; otherwise we render fresh.
// The hand-tuned static landing (`.sl`) baked into index.html for fast LCP must
// NOT be hydrated (its markup intentionally differs from <MinimalLanding/>), so
// we treat it as an empty mount and render over it.
const firstChild = container.firstElementChild;
const isStaticLanding = firstChild && firstChild.classList.contains('sl');

if (container.hasChildNodes() && !isStaticLanding) {
  hydrateRoot(container, tree);
} else {
  createRoot(container).render(tree);
}
