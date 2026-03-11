import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getCourtStructure, getEcourtsDefaults, unwrapEcourtsPayload } from './common/ecourtsApi';

const ECOURTS_TOOLS = [
  {
    title: 'Case Search',
    desc: 'Search cases by CNR number, party name, or advocate name across Indian courts.',
    icon: 'manage_search',
    to: '/ecourts/case-search',
    color: 'bg-blue-50 text-blue-600',
    section: 'cases',
  },
  {
    title: 'Lawyer Search',
    desc: 'Find advocate information, bar registration, and cases associated with a lawyer.',
    icon: 'person_search',
    to: '/ecourts/lawyers',
    color: 'bg-primary/10 text-primary',
    section: 'lawyers',
  },
  {
    title: 'Litigant Search',
    desc: 'Look up cases filed by or against specific individuals or organizations.',
    icon: 'groups',
    to: '/ecourts/litigants',
    color: 'bg-emerald-50 text-emerald-600',
    section: 'litigants',
  },
  {
    title: 'Cause List',
    desc: 'Browse daily cause lists for your court and bench combination.',
    icon: 'list_alt',
    to: '/ecourts/cause-list',
    color: 'bg-violet-50 text-violet-600',
    section: 'cause-list',
  },
];

const SECTION_ROUTES = {
  cases: '/ecourts/case-search',
  lawyers: '/ecourts/lawyers',
  litigants: '/ecourts/litigants',
};

const SECTION_LABELS = {
  cases: 'Cases',
  lawyers: 'Lawyers',
  litigants: 'Litigants',
};

const DEFAULT_SECTIONS = [
  { key: 'cases', title: 'Default Cases', emptyMessage: 'No cached case defaults are available right now.' },
  { key: 'lawyers', title: 'Default Lawyer Matches', emptyMessage: 'No cached lawyer defaults are available right now.' },
  { key: 'litigants', title: 'Default Litigant Matches', emptyMessage: 'No cached litigant defaults are available right now.' },
];

function loadRecentSearches() {
  const sections = ['cases', 'lawyers', 'litigants'];
  const recent = [];

  for (const section of sections) {
    try {
      const raw = sessionStorage.getItem(`ecourts_src_v1_${section}`);
      if (!raw) continue;

      const cached = JSON.parse(raw);
      if (!cached?.query || !cached?.ts) continue;
      if (Date.now() - cached.ts > 30 * 60 * 1000) continue;

      recent.push({
        section,
        query: cached.query,
        page: cached.page || 1,
        timestamp: cached.ts,
        total: cached.results?.total || cached.results?.case_list?.length || 0,
      });
    } catch {
      // Ignore malformed sessionStorage entries.
    }
  }

  return recent.sort((a, b) => b.timestamp - a.timestamp);
}

function formatDate(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function statusBadgeClass(status) {
  if ((status || '').toString().trim().toLowerCase() === 'disposed') {
    return 'bg-slate-100 text-slate-500';
  }
  return 'bg-emerald-100 text-emerald-600';
}

function PreviewCard({ item }) {
  return (
    <Link
      to={`/ecourts/case/${encodeURIComponent(item.cnr || item.cnr_number || item.id || '')}`}
      className="block rounded-2xl border border-primary/10 bg-white px-4 py-4 transition-all hover:border-primary/30 hover:shadow-sm"
    >
      <div className="mb-2 flex items-center gap-2">
        <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${statusBadgeClass(item.status || item.case_status)}`}>
          {item.status || item.case_status || 'Active'}
        </span>
        <span className="text-xs font-mono text-slate-400">{item.cnr || item.cnr_number || '—'}</span>
      </div>
      <p className="font-semibold text-ink">{item.case_title || item.title || 'Case result'}</p>
      <p className="mt-1 text-xs text-slate-500">
        {[item.case_type, item.case_number && item.year ? `${item.case_number}/${item.year}` : item.case_number, item.court || item.court_name].filter(Boolean).join(' — ') || 'Court data unavailable'}
      </p>
      {item.next_hearing_date ? (
        <p className="mt-2 text-xs font-semibold text-primary">Next hearing: {formatDate(item.next_hearing_date)}</p>
      ) : null}
    </Link>
  );
}

function RecentSearchCard({ item, onOpen }) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="rounded-2xl border border-primary/10 bg-white px-4 py-4 text-left transition-all hover:border-primary/30 hover:shadow-sm"
    >
      <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">{SECTION_LABELS[item.section]}</p>
      <p className="mt-2 text-sm font-semibold text-ink">{item.query}</p>
      <p className="mt-1 text-xs text-slate-500">
        {item.total ? `${item.total} cached result${item.total > 1 ? 's' : ''}` : 'Cached search'} • page {item.page}
      </p>
      <p className="mt-2 text-xs font-semibold text-primary">Reopen search</p>
    </button>
  );
}

export default function EcourtsHome() {
  const navigate = useNavigate();
  const [quickCnr, setQuickCnr] = useState('');
  const [defaults, setDefaults] = useState({ cases: null, lawyers: null, litigants: null });
  const [defaultsLoading, setDefaultsLoading] = useState(true);
  const [courtStats, setCourtStats] = useState(null);
  const [courtStatsError, setCourtStatsError] = useState('');

  const recentSearches = useMemo(loadRecentSearches, []);

  useEffect(() => {
    let active = true;

    async function hydrateHome() {
      setDefaultsLoading(true);
      setCourtStatsError('');

      const [courtStructureResult, ...defaultResults] = await Promise.allSettled([
        getCourtStructure(),
        ...DEFAULT_SECTIONS.map((section) => getEcourtsDefaults(section.key)),
      ]);

      if (!active) return;

      if (courtStructureResult.status === 'fulfilled') {
        setCourtStats(unwrapEcourtsPayload(courtStructureResult.value) || null);
      } else {
        setCourtStats(null);
        setCourtStatsError(courtStructureResult.reason?.response?.data?.error || 'Court structure is unavailable right now.');
      }

      const nextDefaults = { cases: null, lawyers: null, litigants: null };
      DEFAULT_SECTIONS.forEach((section, index) => {
        const result = defaultResults[index];
        if (result.status !== 'fulfilled') return;

        const payload = result.value?.data?.data || unwrapEcourtsPayload(result.value) || null;
        if (payload?.case_list?.length) {
          nextDefaults[section.key] = {
            ...payload,
            refreshedAt: result.value?.data?.refreshed_at || null,
          };
        }
      });

      setDefaults(nextDefaults);
      setDefaultsLoading(false);
    }

    hydrateHome();
    return () => {
      active = false;
    };
  }, []);

  function handleQuickLookup() {
    const value = quickCnr.trim().toUpperCase();
    if (!value) return;
    navigate(`/ecourts/case/${encodeURIComponent(value)}`);
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-3">
          <div className="size-12 bg-primary/10 rounded-xl flex items-center justify-center">
            <span className="material-symbols-outlined text-primary text-2xl">balance</span>
          </div>
          <div>
            <h2 className="text-2xl font-black text-ink tracking-tight">eCourts India</h2>
            <p className="text-sm text-slate-500">Real-time access to Indian court case data</p>
          </div>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-xl px-4 py-3 flex items-start gap-3 mt-4">
          <span className="material-symbols-outlined text-amber-600 text-lg mt-0.5 flex-shrink-0">info</span>
          <p className="text-sm text-amber-700">
            Data is sourced from the eCourts partner API. Information is subject to the availability
            and accuracy of the official eCourts portal.
          </p>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-4">
            <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">States</p>
            <p className="mt-2 text-2xl font-black text-ink">{courtStats?.total_states ?? '—'}</p>
            <p className="mt-1 text-xs text-slate-500">Court-structure coverage from the free hierarchy API.</p>
          </div>
          <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-4">
            <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">High Courts</p>
            <p className="mt-2 text-2xl font-black text-ink">{courtStats?.high_courts?.length ?? '—'}</p>
            <p className="mt-1 text-xs text-slate-500">Configured from the current backend court map.</p>
          </div>
          <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-4">
            <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">Recent Searches</p>
            <p className="mt-2 text-2xl font-black text-ink">{recentSearches.length}</p>
            <p className="mt-1 text-xs text-slate-500">Recovered from this tab&apos;s eCourts search cache.</p>
          </div>
        </div>

        {courtStatsError ? (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            {courtStatsError}
          </div>
        ) : null}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
        {ECOURTS_TOOLS.map((tool) => (
          <Link
            key={tool.to}
            to={tool.to}
            className="card p-6 hover:shadow-md hover:border-primary/30 transition-all group flex gap-5 items-start"
          >
            <div className={`size-12 ${tool.color} rounded-xl flex items-center justify-center flex-shrink-0`}>
              <span className="material-symbols-outlined text-2xl">{tool.icon}</span>
            </div>
            <div>
              <h3 className="font-bold text-ink group-hover:text-primary transition-colors">
                {tool.title}
              </h3>
              <p className="text-sm text-slate-500 mt-1 leading-relaxed">{tool.desc}</p>
              <div className="mt-3 flex items-center gap-1 text-primary text-xs font-semibold">
                Open
                <span className="material-symbols-outlined text-sm group-hover:translate-x-1 transition-transform">
                  arrow_forward
                </span>
              </div>
            </div>
          </Link>
        ))}
      </div>

      <div className="mt-8 card p-5">
        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Quick CNR Lookup</p>
        <div className="flex gap-3">
          <input
            type="text"
            maxLength={20}
            placeholder="Enter CNR number (e.g., MHAU010001232024)"
            className="input-base flex-1 font-mono uppercase"
            value={quickCnr}
            onChange={(e) => setQuickCnr(e.target.value.toUpperCase())}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && quickCnr.trim()) {
                handleQuickLookup();
              }
            }}
          />
          <button className="btn-primary flex items-center gap-2" onClick={handleQuickLookup}>
            <span className="material-symbols-outlined text-base">search</span>
            Search
          </button>
        </div>
      </div>

      {recentSearches.length > 0 ? (
        <div className="mt-8">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">Continue Where You Left Off</p>
              <h3 className="mt-1 text-lg font-black text-ink">Recent eCourts searches from this tab</h3>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {recentSearches.map((item) => (
              <RecentSearchCard
                key={`${item.section}-${item.query}`}
                item={item}
                onOpen={() => navigate(`${SECTION_ROUTES[item.section]}?q=${encodeURIComponent(item.query)}&page=${item.page}`)}
              />
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-8">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">Backend Defaults</p>
            <h3 className="mt-1 text-lg font-black text-ink">What the backend currently has ready</h3>
          </div>
          {defaultsLoading ? (
            <p className="text-sm text-slate-500">Loading default previews…</p>
          ) : null}
        </div>

        <div className="grid gap-5 lg:grid-cols-3">
          {DEFAULT_SECTIONS.map((section) => {
            const payload = defaults[section.key];
            const items = payload?.case_list?.slice(0, 3) || [];

            return (
              <div key={section.key} className="card p-5">
                <div className="mb-4 flex items-start justify-between gap-3">
                  <div>
                    <h4 className="font-bold text-ink">{section.title}</h4>
                    {payload?.refreshedAt ? (
                      <p className="mt-1 text-xs text-slate-400">Updated {formatDate(payload.refreshedAt)}</p>
                    ) : null}
                  </div>
                  <Link to={SECTION_ROUTES[section.key]} className="text-xs font-semibold uppercase tracking-[0.18em] text-primary hover:underline">
                    Open
                  </Link>
                </div>

                {items.length > 0 ? (
                  <div className="space-y-3">
                    {items.map((item, index) => (
                      <PreviewCard key={item.cnr || item.cnr_number || `${section.key}-${index}`} item={item} />
                    ))}
                  </div>
                ) : (
                  <div className="rounded-2xl border border-dashed border-primary/15 bg-background-light px-4 py-5">
                    <p className="text-sm text-slate-500">{section.emptyMessage}</p>
                    <p className="mt-2 text-xs text-slate-400">
                      The search page still works for direct user queries even when no warm default cache is available.
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
