import posthog from 'posthog-js';

function safeSessionGet(key) {
  try { return sessionStorage.getItem(key); } catch { return null; }
}
function safeSessionSet(key, value) {
  try { sessionStorage.setItem(key, value); } catch { /* storage blocked */ }
}

export function initializeAnalytics() {
  // index.js owns posthog.init via PostHogProvider — skip if already loaded
  if (posthog.__loaded) {
    const sessionId = safeSessionGet('session_id') || generateSessionId();
    safeSessionSet('session_id', sessionId);
    posthog.register({ session_id: sessionId });
    return true;
  }

  const key = process.env.REACT_APP_POSTHOG_KEY;
  const host = process.env.REACT_APP_POSTHOG_HOST || 'https://eu.i.posthog.com';

  if (!key) {
    console.warn('[Analytics] REACT_APP_POSTHOG_KEY not set');
    return false;
  }

  try {
    posthog.init(key, {
      api_host: host,
      autocapture: false,
      capture_pageview: false,
      capture_pageleave: false,
      disable_session_recording: true,
      persistence: 'localStorage',
      opt_out_capturing_by_default: true,
    });

    const sessionId = safeSessionGet('session_id') || generateSessionId();
    safeSessionSet('session_id', sessionId);
    posthog.register({ session_id: sessionId });

    return true;
  } catch (error) {
    console.error('[Analytics] Failed to initialize PostHog:', error);
    return false;
  }
}

export function setAnalyticsUser(userId, userEmail, userType = 'user') {
  try {
    posthog.identify(userId, { email: userEmail, user_type: userType });
  } catch (error) {
    console.error('[Analytics] Failed to set user:', error);
  }
}

export function clearAnalyticsUser() {
  try {
    posthog.reset();
  } catch (error) {
    console.error('[Analytics] Failed to clear user:', error);
  }
}

export function trackPageView(pageName, properties = {}) {
  try {
    posthog.capture('$pageview', { path: pageName, ...properties });
  } catch (error) {
    console.error('[Analytics] Failed to track page view:', error);
  }
}

export function trackFeatureUse(feature, action, metadata = {}) {
  try {
    posthog.capture('feature_used', { feature, action, ...metadata });
  } catch (error) {
    console.error('[Analytics] Failed to track feature use:', error);
  }
}

export function trackConsentChange(consentType, accepted, categories = {}) {
  try {
    posthog.capture('consent_changed', { consent_type: consentType, accepted, ...categories });
  } catch (error) {
    console.error('[Analytics] Failed to track consent change:', error);
  }
}

// Toggle actual event transmission based on the user's cookie-consent choice.
// posthog.init() always runs (see index.js) with opt_out_capturing_by_default:
// true, so no event leaves the browser until one of these is called.
export function optIntoAnalytics() {
  try {
    posthog.opt_in_capturing();
  } catch (error) {
    console.error('[Analytics] Failed to opt in to capturing:', error);
  }
}

export function optOutOfAnalytics() {
  try {
    posthog.opt_out_capturing();
  } catch (error) {
    console.error('[Analytics] Failed to opt out of capturing:', error);
  }
}

export function trackCheckout(action, orderValue = null, metadata = {}) {
  try {
    posthog.capture('checkout', { action, order_value: orderValue, ...metadata });
  } catch (error) {
    console.error('[Analytics] Failed to track checkout:', error);
  }
}

export function trackError(errorType, message, context = {}) {
  try {
    posthog.capture('$exception', { error_type: errorType, message, ...context });
  } catch (error) {
    console.error('[Analytics] Failed to track error:', error);
  }
}

export function getSessionId() {
  return safeSessionGet('session_id');
}

export function isAnalyticsReady() {
  return !!posthog.__loaded;
}

function generateSessionId() {
  return 'session-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
}
