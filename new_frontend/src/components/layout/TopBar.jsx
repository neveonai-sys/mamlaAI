import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import apiClient from '../../services/api';

const CNR_LENGTH = 16;

const SEARCH_ITEMS = [
  {
    label: 'Dashboard',
    path: '/dashboard',
    icon: 'dashboard',
    description: 'Workspace overview and agenda',
    keywords: ['home', 'overview', 'summary', 'agenda'],
  },
  {
    label: 'AI Drafting',
    path: '/drafting',
    icon: 'edit_note',
    description: 'Create or continue legal drafts',
    keywords: ['draft', 'petition', 'editor', 'document'],
  },
  {
    label: 'Calendar & Events',
    path: '/calendar',
    icon: 'calendar_month',
    description: 'Hearings, deadlines, and scheduling',
    keywords: ['calendar', 'events', 'hearing', 'deadline', 'schedule'],
  },
  // {
  //   label: 'Court Updates',
  //   path: '/court-updates',
  //   icon: 'account_balance',
  //   description: 'Recent court notices and subscribed feeds',
  //   keywords: ['court', 'notices', 'updates', 'orders'],
  // },
  {
    label: 'eCourts',
    path: '/ecourts',
    icon: 'search',
    description: 'Case, lawyer, litigant, and cause list lookup',
    keywords: ['cnr', 'search', 'case', 'lawyer', 'litigant'],
  },
  {
    label: 'Clients',
    path: '/clients',
    icon: 'people',
    description: 'Onboard and manage clients',
    keywords: ['client', 'onboarding', 'people'],
    roles: ['Lawyer', 'Paralegal'],
  },
  {
    label: 'Sessions',
    path: '/sessions',
    icon: 'forum',
    description: 'Review and manage active sessions',
    keywords: ['session', 'devices', 'security'],
  },
  {
    label: 'Feedback',
    path: '/feedback',
    icon: 'rate_review',
    description: 'Report bugs or request improvements',
    keywords: ['feedback', 'bug', 'feature', 'support', 'help'],
  },
];

function buildQuotaAlert(feature, label, path, messagePrefix, icon = 'auto_awesome') {
  if (!feature || typeof feature.remaining_included !== 'number') return null;
  if (feature.allowed === false) {
    return {
      id: `${path}-blocked`,
      title: `${label} unavailable`,
      detail: `${messagePrefix} is blocked until quota resets or credits are added.`,
      path,
      icon,
      tone: 'error',
    };
  }
  if (feature.remaining_included <= 2) {
    return {
      id: `${path}-low`,
      title: `${label} running low`,
      detail: `${feature.remaining_included} included ${messagePrefix.toLowerCase()} left.`,
      path,
      icon,
      tone: 'warning',
    };
  }
  return null;
}

function alertToneClasses(tone) {
  if (tone === 'error') return 'border-red-200 bg-red-50 text-red-700';
  if (tone === 'warning') return 'border-amber-200 bg-amber-50 text-amber-700';
  return 'border-sky-200 bg-sky-50 text-sky-700';
}

function normalizeSavedDraftRows(savedDrafts) {
  return (savedDrafts || []).map((draft) => ({
    ...draft,
    session_id: draft.session_id || draft.id || '',
    draft_id: draft.draft_id || '',
    draft_name: draft.draft_name || draft.title || 'Untitled Draft',
  }));
}

export default function TopBar({ onToggleSidebar, title }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { planCode, trial, wallet, features } = useSelector((s) => s.entitlements);
  const { user_type } = useSelector((s) => s.user);
  const brainRemaining = features?.brain_doc_analysis?.remaining_included;
  const legalChatRemaining = features?.general_legal_chat?.remaining_included;
  const planLabel = trial?.active
    ? `Trial (${trial.daysRemaining != null ? trial.daysRemaining : ''}d)`
    : (planCode || 'Plan').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  const [query, setQuery] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [notificationLoading, setNotificationLoading] = useState(false);
  const [notificationData, setNotificationData] = useState(null);
  const [notificationError, setNotificationError] = useState('');
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [searchDataLoaded, setSearchDataLoaded] = useState(false);
  const [searchData, setSearchData] = useState({ savedDrafts: [] });
  const searchRef = useRef(null);
  const notificationRef = useRef(null);
  const helpRef = useRef(null);

  const availableSearchItems = useMemo(() => {
    return SEARCH_ITEMS.filter((item) => !item.roles || item.roles.includes(user_type));
  }, [user_type]);

  const routeResults = useMemo(() => {
    const trimmedQuery = query.trim().toLowerCase();
    const candidates = availableSearchItems.filter((item) => item.path !== location.pathname);
    if (!trimmedQuery) {
      return candidates.slice(0, 6).map((item) => ({
        id: item.path,
        label: item.label,
        description: item.description,
        icon: item.icon,
        path: item.path,
        kind: 'route',
      }));
    }
    return candidates.filter((item) => {
      const haystack = [item.label, item.description, ...(item.keywords || [])].join(' ').toLowerCase();
      return haystack.includes(trimmedQuery);
    }).slice(0, 6).map((item) => ({
      id: item.path,
      label: item.label,
      description: item.description,
      icon: item.icon,
      path: item.path,
      kind: 'route',
    }));
  }, [availableSearchItems, location.pathname, query]);

  const smartResults = useMemo(() => {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) return routeResults;

    const lowered = trimmedQuery.toLowerCase();
    const condensedAlphaNumeric = trimmedQuery.toUpperCase().replace(/[^A-Z0-9]/g, '');
    const results = [];

    if (condensedAlphaNumeric.length === CNR_LENGTH) {
      results.push({
        id: `cnr-${condensedAlphaNumeric}`,
        label: `Open eCourts case ${condensedAlphaNumeric}`,
        description: 'Direct CNR shortcut into case detail',
        icon: 'badge',
        path: `/ecourts/case/${condensedAlphaNumeric}`,
        kind: 'cnr',
      });
    }

    const matchingDrafts = searchData.savedDrafts.filter((draft) => {
      const haystack = [draft.draft_name, draft.session_id, draft.draft_id]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      return haystack.includes(lowered);
    }).slice(0, 4);

    matchingDrafts.forEach((draft) => {
      if (!draft.session_id) return;
      results.push({
        id: `draft-${draft.session_id}-${draft.draft_id || 'live'}`,
        label: draft.draft_name,
        description: `Draft session ${draft.session_id}${draft.draft_id ? ` · saved draft ${draft.draft_id}` : ''}`,
        icon: 'edit_note',
        path: `/drafting/${draft.session_id}`,
        kind: 'draft',
      });
    });

    const draftIdLike = /^[A-Za-z0-9_-]{8,}$/.test(trimmedQuery);
    if (draftIdLike && !matchingDrafts.some((draft) => draft.session_id === trimmedQuery)) {
      results.push({
        id: `draft-shortcut-${trimmedQuery}`,
        label: `Open drafting session ${trimmedQuery}`,
        description: 'Direct session shortcut if you already know the draft session id',
        icon: 'quick_reference_all',
        path: `/drafting/${trimmedQuery}`,
        kind: 'draft-shortcut',
      });
    }

    return [...results, ...routeResults].slice(0, 8);
  }, [query, routeResults, searchData.savedDrafts]);

  const alerts = useMemo(() => {
    const items = [];
    const docAlert = buildQuotaAlert(features?.brain_doc_analysis, 'Document analysis', '/chat', 'document analyses', 'description');
    const chatAlert = buildQuotaAlert(features?.general_legal_chat, 'General legal chat', '/chat', 'general legal chats', 'forum');
    const draftingAlert = buildQuotaAlert(features?.brain_drafting_actions, 'Drafting actions', '/drafting', 'drafting actions', 'edit_note');
    if (docAlert) items.push(docAlert);
    if (chatAlert) items.push(chatAlert);
    if (draftingAlert) items.push(draftingAlert);
    if ((wallet?.balance ?? 0) === 0) {
      items.push({
        id: 'wallet-empty',
        title: 'Wallet credits are empty',
        detail: 'Add credits before quota spillover actions are needed.',
        path: '/dashboard',
        icon: 'account_balance_wallet',
        tone: 'warning',
      });
    }
    const events = notificationData?.upcoming_events_list || [];
    events.slice(0, 2).forEach((event, index) => {
      const dateLabel = event.start
        ? new Date(event.start).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
        : 'Upcoming';
      items.push({
        id: `event-${event.id || index}`,
        title: event.title || 'Upcoming event',
        detail: `${dateLabel}${event.location ? ` · ${event.location}` : ''}`,
        path: '/calendar',
        icon: 'event_note',
        tone: 'info',
      });
    });
    const updates = notificationData?.recent_updates || [];
    updates.slice(0, 2).forEach((update, index) => {
      items.push({
        id: `update-${update.id || index}`,
        title: update.case_title || update.title || 'Court update',
        detail: update.court || update.detail || update.update_type || 'Recent court update',
        path: '/court-updates',
        icon: update.is_critical ? 'warning' : 'dynamic_feed',
        tone: update.is_critical ? 'warning' : 'info',
      });
    });
    return items.slice(0, 6);
  }, [features, notificationData, wallet?.balance]);

  const helpItems = useMemo(() => {
    return [
      {
        id: 'help-feedback',
        title: 'Send feedback',
        description: 'Report bugs or request product changes.',
        icon: 'rate_review',
        onClick: () => navigate('/feedback'),
      },
      {
        id: 'help-sessions',
        title: 'Review sessions',
        description: 'Inspect active logins and sign out stale devices.',
        icon: 'devices',
        onClick: () => navigate('/sessions'),
      },
    ];
  }, [navigate]);

  useEffect(() => {
    function handlePointerDown(event) {
      if (searchRef.current && !searchRef.current.contains(event.target)) {
        setSearchOpen(false);
      }
      if (notificationRef.current && !notificationRef.current.contains(event.target)) {
        setNotificationOpen(false);
      }
      if (helpRef.current && !helpRef.current.contains(event.target)) {
        setHelpOpen(false);
      }
    }

    function handleKeyDown(event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setSearchOpen(true);
        searchRef.current?.querySelector('input')?.focus();
      }
      if (event.key === 'Escape') {
        setSearchOpen(false);
        setNotificationOpen(false);
        setHelpOpen(false);
      }
    }

    window.addEventListener('pointerdown', handlePointerDown);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('pointerdown', handlePointerDown);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  useEffect(() => {
    setSearchOpen(false);
    setNotificationOpen(false);
    setHelpOpen(false);
    setQuery('');
  }, [location.pathname]);

  useEffect(() => {
    if (!notificationOpen || notificationData || notificationLoading) return;
    setNotificationLoading(true);
    setNotificationError('');
    apiClient.get('dashboard/home/')
      .then((response) => setNotificationData(response.data || {}))
      .catch(() => setNotificationError('Could not load live alerts right now.'))
      .finally(() => setNotificationLoading(false));
  }, [notificationData, notificationLoading, notificationOpen]);

  useEffect(() => {
    if (!searchOpen || searchDataLoaded || searchLoading) return;
    setSearchLoading(true);
    setSearchError('');

    apiClient.get('aidrafts/get_user_saved_drafts_v2')
      .then((response) => {
        const savedDrafts = normalizeSavedDraftRows(response.data?.saved_drafts || response.data?.results || []);
        setSearchData({ savedDrafts });
      })
      .catch(() => {
        setSearchData({ savedDrafts: [] });
        setSearchError('Could not load draft suggestions right now.');
      })
      .finally(() => {
        setSearchDataLoaded(true);
        setSearchLoading(false);
      });
  }, [searchDataLoaded, searchLoading, searchOpen]);

  function handleSearchSubmit(event) {
    event.preventDefault();
    if (!smartResults.length) return;
    navigate(smartResults[0].path);
    setSearchOpen(false);
  }

  function openNotificationPanel() {
    setNotificationOpen((current) => !current);
    setHelpOpen(false);
    setSearchOpen(false);
  }

  function openHelpPanel() {
    setHelpOpen((current) => !current);
    setNotificationOpen(false);
    setSearchOpen(false);
  }

  return (
    <header className="z-10 mt-3 mb-3 flex h-20 items-center gap-4 rounded-[28px] border border-white/70 bg-white/90 px-6 shadow-card backdrop-blur flex-shrink-0">
      {/* Mobile hamburger */}
      <button
        className="rounded-md p-1.5 text-ink/70 transition-colors hover:bg-primary/5 hover:text-primary lg:hidden"
        onClick={onToggleSidebar}
        aria-label="Open menu"
      >
        <span className="material-symbols-outlined">menu</span>
      </button>

      {/* Search */}
      <div ref={searchRef} className="relative flex-1 max-w-lg">
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-background-light px-3 py-2.5">
          <span className="material-symbols-outlined text-ink/55 text-lg">search</span>
          <input
            type="text"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setSearchOpen(true);
            }}
            onFocus={() => setSearchOpen(true)}
            placeholder="Search pages, tools, and actions…"
            className="flex-1 bg-transparent text-sm font-medium text-ink placeholder:text-ink/45 outline-none"
          />
          <button
            type="submit"
            className="hidden rounded-lg border border-slate-200 bg-white px-2 py-1 text-[11px] font-semibold text-slate-500 transition-colors hover:border-primary/30 hover:text-primary sm:block"
          >
            Go
          </button>
          <span className="hidden font-mono text-xs text-ink/40 sm:block">Ctrl K</span>
        </form>

        {searchOpen && (
          <div className="absolute left-0 right-0 top-[calc(100%+0.6rem)] z-30 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
            <div className="border-b border-slate-100 px-4 py-3 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">
              Quick navigation
            </div>
            {searchLoading && (
              <div className="border-b border-slate-100 px-4 py-3 text-xs text-slate-500">Loading draft and case matches…</div>
            )}
            {searchError && (
              <div className="border-b border-red-100 bg-red-50 px-4 py-3 text-xs text-red-700">{searchError}</div>
            )}
            {smartResults.length > 0 ? (
              <div className="max-h-80 overflow-y-auto custom-scrollbar py-2">
                {smartResults.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      navigate(item.path);
                      setSearchOpen(false);
                    }}
                    className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-primary/5"
                  >
                    <span className="material-symbols-outlined mt-0.5 text-primary">{item.icon}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold text-ink">{item.label}</span>
                      <span className="block text-xs leading-5 text-slate-500">{item.description}</span>
                    </span>
                    <span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                      {item.kind === 'route' ? 'Page' : item.kind}
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <div className="px-4 py-5 text-sm text-slate-500">No matching pages or actions.</div>
            )}
          </div>
        )}
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-2 ml-auto">
        <div className="hidden xl:flex items-center gap-2 mr-2">
          {planCode ? (
            <>
              <span className={`rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-white ${
                trial?.active && (trial?.daysRemaining ?? 99) <= 3
                  ? 'border-amber-500 bg-amber-500'
                  : 'border-primary/15 bg-primary-dark'
              }`}>
                {planLabel}
              </span>
              {typeof brainRemaining === 'number' && (
                <span className="rounded-full bg-primary/10 px-3 py-1 text-[11px] font-semibold text-primary">
                  {brainRemaining} doc analyses left
                </span>
              )}
              {typeof legalChatRemaining === 'number' && (
                <span className="rounded-full bg-slate-900 px-3 py-1 text-[11px] font-semibold text-white">
                  {legalChatRemaining} legal chats left
                </span>
              )}
              <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-semibold text-slate-700">
                {wallet?.balance ?? 0} credits
              </span>
            </>
          ) : (
            /* Skeleton — reserves space while entitlements load, prevents header CLS */
            <span className="inline-block h-6 w-28 rounded-full bg-primary-dark/30 animate-pulse" />
          )}
        </div>
        {/* Quick draft */}
        <button
          className="hidden md:flex items-center gap-1.5 btn-primary text-xs px-3 py-2"
          onClick={() => navigate('/drafting')}
        >
          <span className="material-symbols-outlined text-sm">add</span>
          New Draft
        </button>

        {/* Notifications */}
        <div ref={notificationRef} className="relative">
          <button
            type="button"
            onClick={openNotificationPanel}
            className="relative rounded-xl border border-slate-200 p-2 text-ink/60 transition-colors hover:bg-primary/5 hover:text-primary"
            aria-label="Open alerts"
          >
            <span className="material-symbols-outlined text-xl">notifications</span>
            {alerts.length > 0 && <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-primary"></span>}
          </button>

          {notificationOpen && (
            <div className="absolute right-0 top-[calc(100%+0.6rem)] z-30 w-[24rem] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Alerts</p>
                  <h3 className="mt-1 text-sm font-semibold text-ink">Live workspace signals</h3>
                </div>
                <button
                  type="button"
                  onClick={() => navigate('/dashboard')}
                  className="text-xs font-semibold text-primary transition-colors hover:text-primary-dark"
                >
                  View dashboard
                </button>
              </div>

              <div className="max-h-[28rem] overflow-y-auto custom-scrollbar p-3">
                {notificationLoading && <div className="px-2 py-3 text-sm text-slate-500">Loading live alerts…</div>}
                {!notificationLoading && notificationError && (
                  <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-3 text-sm text-red-700">{notificationError}</div>
                )}
                {!notificationLoading && !notificationError && alerts.length === 0 && (
                  <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-4 text-sm text-slate-500">
                    No immediate alerts. Quotas and upcoming events will appear here when action is needed.
                  </div>
                )}
                {!notificationLoading && !notificationError && alerts.length > 0 && (
                  <div className="space-y-3">
                    {alerts.map((alert) => (
                      <button
                        key={alert.id}
                        type="button"
                        onClick={() => navigate(alert.path)}
                        className={`w-full rounded-2xl border px-4 py-3 text-left transition-colors hover:border-primary/30 ${alertToneClasses(alert.tone)}`}
                      >
                        <div className="flex items-start gap-3">
                          <span className="material-symbols-outlined mt-0.5 text-base">{alert.icon}</span>
                          <span className="min-w-0 flex-1">
                            <span className="block text-sm font-semibold">{alert.title}</span>
                            <span className="mt-1 block text-xs leading-5 opacity-90">{alert.detail}</span>
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Help */}
        <div ref={helpRef} className="relative">
          <button
            type="button"
            onClick={openHelpPanel}
            className="rounded-xl border border-slate-200 p-2 text-ink/60 transition-colors hover:bg-primary/5 hover:text-primary"
            aria-label="Open help"
          >
            <span className="material-symbols-outlined text-xl">help_outline</span>
          </button>

          {helpOpen && (
            <div className="absolute right-0 top-[calc(100%+0.6rem)] z-30 w-[21rem] overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
              <div className="border-b border-slate-100 px-4 py-3">
                <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Help</p>
                <h3 className="mt-1 text-sm font-semibold text-ink">Useful actions</h3>
              </div>

              <div className="space-y-2 p-3">
                {helpItems.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={item.onClick}
                    className="flex w-full items-start gap-3 rounded-2xl border border-slate-200 px-4 py-3 text-left transition-colors hover:border-primary/30 hover:bg-primary/5"
                  >
                    <span className="material-symbols-outlined mt-0.5 text-primary">{item.icon}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold text-ink">{item.title}</span>
                      <span className="mt-1 block text-xs leading-5 text-slate-500">{item.description}</span>
                    </span>
                  </button>
                ))}
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs leading-6 text-slate-500">
                  <div className="flex items-center justify-between gap-3">
                    <span>Quick search</span>
                    <span className="font-mono text-[11px] text-slate-600">Ctrl K</span>
                  </div>
                  <div className="mt-1 flex items-center justify-between gap-3">
                    <span>Start draft</span>
                    <span className="font-medium text-slate-600">Top bar action</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
