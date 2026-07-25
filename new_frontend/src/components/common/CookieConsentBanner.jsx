import React, { useEffect, useState } from 'react';
import apiClient from '../../services/api';
import { trackConsentChange, optIntoAnalytics, optOutOfAnalytics } from '../../services/analytics';
import { DEFAULT_PREFERENCES, getStoredConsent, saveConsentToLocal, COOKIE_VERSION } from '../../utils/cookieConsent';

export default function CookieConsentBanner() {
  const [visible, setVisible] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const stored = getStoredConsent();
    if (!stored) {
      setVisible(true);
      return;
    }
    if (stored.preferences) {
      setPreferences({ ...DEFAULT_PREFERENCES, ...stored.preferences });
    }
  }, []);

  const saveConsent = async (prefs) => {
    setSaving(true);
    const payload = {
      consent_type: 'cookie_preferences',
      version: COOKIE_VERSION,
      preferences: prefs,
      source: 'web',
    };
    saveConsentToLocal(prefs);
    setPreferences(prefs);
    setVisible(false);
    setExpanded(false);
    setError('');

    // Actually toggle event transmission — must happen before the
    // trackConsentChange capture() call below so a rejection doesn't sneak
    // out as one last tracked event.
    if (prefs.analytics) {
      optIntoAnalytics();
    } else {
      optOutOfAnalytics();
    }

    // Track consent change in analytics (only actually transmits if
    // analytics was accepted, since optOutOfAnalytics() above is a no-op gate).
    try {
      trackConsentChange('cookie', prefs.analytics, prefs);
    } catch (err) {
      console.warn('Failed to track consent change:', err);
    }

    // Post to backend (unauthenticated endpoint, so no error blocking)
    try {
      await apiClient.post('users/consent-events/', payload);
    } catch (err) {
      console.warn('Consent event not recorded on server', err?.response?.data || err?.message || err);
    }
    setSaving(false);
  };

  const handleToggle = (key) => {
    if (key === 'necessary') return;
    setPreferences((current) => ({
      ...current,
      [key]: !current[key],
    }));
  };

  const handleAcceptAll = () => {
    saveConsent({
      necessary: true,
      analytics: true,
      marketing: true,
      personalization: true,
    });
  };

  const handleRejectAll = () => {
    saveConsent({
      necessary: true,
      analytics: false,
      marketing: false,
      personalization: false,
    });
  };

  const handleSavePreferences = () => {
    if (!preferences.necessary) {
      setError('Necessary cookies are required.');
      return;
    }
    saveConsent(preferences);
  };

  if (!visible) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 bg-slate-950 text-slate-100 border-t border-slate-700 shadow-2xl">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-start">
          <div>
            <h2 className="text-lg font-semibold text-white">We use cookies and similar technologies</h2>
            <p className="mt-2 text-sm text-slate-300 max-w-3xl">
              We use cookies to keep the site working, personalize your experience, and measure usage. You can accept all cookies, reject optional cookies, or save your own preferences.
            </p>
            <div className="mt-3 text-xs text-slate-400">
              By continuing, you agree to our{' '}
              <a href="/legal/terms.html" target="_blank" rel="noopener noreferrer" className="font-medium text-white underline">
                Terms of Service
              </a>
              {' '}and{' '}
              <a href="/legal/privacy.html" target="_blank" rel="noopener noreferrer" className="font-medium text-white underline">
                Privacy Policy
              </a>
              .
            </div>
          </div>

          <div className="flex flex-wrap gap-3 justify-end">
            <button
              type="button"
              onClick={handleRejectAll}
              className="rounded-full border border-slate-600 bg-slate-900 px-4 py-2 text-sm font-semibold text-slate-200 hover:border-slate-500 hover:text-white"
            >
              Reject optional cookies
            </button>
            <button
              type="button"
              onClick={() => setExpanded((prev) => !prev)}
              className="rounded-full border border-slate-600 bg-slate-900 px-4 py-2 text-sm font-semibold text-slate-200 hover:border-slate-500 hover:text-white"
            >
              {expanded ? 'Hide options' : 'Manage preferences'}
            </button>
            <button
              type="button"
              onClick={handleAcceptAll}
              className="rounded-full bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm shadow-primary/20 hover:bg-primary-dark"
            >
              Accept all cookies
            </button>
          </div>
        </div>

        {expanded && (
          <div className="rounded-3xl border border-slate-700 bg-slate-900/90 p-4">
            <div className="grid gap-4 md:grid-cols-2">
              {[
                {
                  key: 'necessary',
                  label: 'Necessary cookies',
                  description: 'Always active. Needed for login, security, and basic site functions.',
                },
                {
                  key: 'analytics',
                  label: 'Analytics cookies',
                  description: 'Help us understand how the product is used and improve the service.',
                },
                {
                  key: 'marketing',
                  label: 'Marketing cookies',
                  description: 'Allow us to show relevant offers and product updates.',
                },
                {
                  key: 'personalization',
                  label: 'Personalization cookies',
                  description: 'Remember your preferences and selected experience settings.',
                },
              ].map((item) => (
                <div key={item.key} className="rounded-2xl border border-slate-700 bg-slate-950 p-4">
                  <div className="flex items-start gap-3">
                    <div className="flex h-5 items-center">
                      <input
                        type="checkbox"
                        checked={preferences[item.key]}
                        onChange={() => handleToggle(item.key)}
                        disabled={item.key === 'necessary'}
                        className="h-4 w-4 rounded border-slate-500 bg-slate-900 text-primary focus:ring-primary/60"
                      />
                    </div>
                    <div>
                      <p className="font-semibold text-white">{item.label}</p>
                      <p className="mt-1 text-sm text-slate-400">{item.description}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={handleRejectAll}
                className="inline-flex items-center justify-center rounded-full border border-slate-600 bg-slate-900 px-4 py-2 text-sm font-semibold text-slate-200 hover:border-slate-500 hover:text-white"
              >
                Reject optional
              </button>
              <button
                type="button"
                onClick={handleSavePreferences}
                disabled={saving}
                className="inline-flex items-center justify-center rounded-full bg-primary px-4 py-2 text-sm font-semibold text-white shadow-sm shadow-primary/20 hover:bg-primary-dark disabled:cursor-not-allowed disabled:opacity-60"
              >
                Save preferences
              </button>
              <button
                type="button"
                onClick={handleAcceptAll}
                className="inline-flex items-center justify-center rounded-full border border-slate-600 bg-slate-900 px-4 py-2 text-sm font-semibold text-slate-200 hover:border-slate-500 hover:text-white"
              >
                Accept all
              </button>
            </div>
            {error && <p className="mt-3 text-sm text-rose-300">{error}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
