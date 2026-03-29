import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { scraperHealth, getStates, cnrSearch } from './apiV2';

const MODULES = [
  {
    key: 'cnr',
    title: 'CNR Lookup',
    description: 'Fetch complete case details using the CNR number — orders, hearings, party information, and case history in one view.',
    status: 'live',
    href: null,
  },
  {
    key: 'case-status',
    title: 'Case Status',
    description: 'Search by party name, filing number, advocate name, or FIR reference across any district court in India.',
    status: 'live',
    href: '/ecourts/case-status',
  },
  {
    key: 'court-orders',
    title: 'Court Orders',
    description: 'Search court orders by party, case number, court number, or date range. Direct PDF download.',
    status: 'live',
    href: '/ecourts/court-orders',
  },
  {
    key: 'cause-list',
    title: 'Cause List',
    description: 'Browse daily cause lists for any district court across all states in India.',
    status: 'live',
    href: '/ecourts/cause-list',
  },
  {
    key: 'caveat',
    title: 'Caveat',
    description: 'Search for caveats filed in any district court. This feature will be available shortly.',
    status: 'migration',
    href: '/ecourts/caveat',
  },
];

function toneClass(status) {
  if (status === 'live') return 'bg-emerald-100 text-emerald-700 border-emerald-200';
  return 'bg-amber-100 text-amber-700 border-amber-200';
}

export default function EcourtsTerminal() {
  const navigate = useNavigate();
  const cnrInputRef = useRef(null);
  const [cnr, setCnr] = useState('');
  const [stats, setStats] = useState({
    districtStates: 0,
    highCourts: 0,
    referencesReady: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const readyModules = useMemo(
    () => MODULES.filter((module) => module.status === 'live').length,
    [],
  );

  useEffect(() => {
    let active = true;

    async function hydrate() {
      setLoading(true);
      setError('');
      try {
        const [healthRes, statesRes] = await Promise.all([
          scraperHealth(),
          getStates(),
        ]);

        if (!active) return;

        const statesList = statesRes.data || [];
        const scraperStatus = healthRes.data?.status || 'unknown';

        setStats({
          districtStates: statesList.length,
          highCourts: 0,
          referencesReady: scraperStatus === 'ok' ? 1 : 0,
        });
      } catch (err) {
        if (!active) return;
        setError(err.response?.data?.error || 'Unable to connect to eCourts services right now. Please try again shortly.');
      } finally {
        if (active) setLoading(false);
      }
    }

    hydrate();
    return () => {
      active = false;
    };
  }, []);

  function handleLookup() {
    const normalized = cnr.trim().toUpperCase();
    if (!normalized) return;
    navigate(`/ecourts/case/${encodeURIComponent(normalized)}`);
  }

  function focusQuickLookup() {
    cnrInputRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    cnrInputRef.current?.focus();
  }

  return (
    <div className="p-8 max-w-6xl">
      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="text-[11px] font-black uppercase tracking-[0.28em] text-primary">eCourts Case Search</p>
            <h1 className="mt-3 text-3xl font-black tracking-tight text-ink">Live access to district court records across India</h1>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              Search and track cases from district courts across all states in India. Access case status, court orders, cause lists, and CNR lookups — all from a single place.
            </p>
          </div>

          <div className="grid min-w-[280px] gap-3 sm:grid-cols-3 lg:w-[420px]">
            <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-4">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">States Loaded</p>
              <p className="mt-2 text-2xl font-black text-ink">{loading ? '...' : stats.districtStates || '0'}</p>
            </div>
            <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-4">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Service</p>
              <p className="mt-2 text-2xl font-black text-ink">{loading ? '...' : stats.referencesReady ? '✓' : '—'}</p>
            </div>
            <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-4">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Live Modules</p>
              <p className="mt-2 text-2xl font-black text-ink">{readyModules}</p>
            </div>
          </div>
        </div>

        {error ? (
          <div className="mt-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <div className="mt-8 rounded-[24px] border border-primary/10 bg-background-light p-5">
          <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">CNR Quick Lookup</p>
          <div className="mt-3 flex flex-col gap-3 md:flex-row">
            <input
              ref={cnrInputRef}
              type="text"
              value={cnr}
              onChange={(event) => setCnr(event.target.value.toUpperCase())}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault();
                  handleLookup();
                }
              }}
              placeholder="Enter CNR number (e.g. MHPU010023452024)"
              className="input-base flex-1 font-mono uppercase"
            />
            <button type="button" onClick={handleLookup} className="btn-primary flex items-center justify-center gap-2 md:min-w-[180px]">
              <span className="material-symbols-outlined text-base">search</span>
              Open Case
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Enter a valid CNR to view the complete case record including orders, hearings, and party details.
          </p>
        </div>
      </div>

      <div className="mt-8 grid gap-4 lg:grid-cols-2">
        {MODULES.map((module) => (
          <div key={module.key} className="rounded-[24px] border border-primary/10 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-lg font-black text-ink">{module.title}</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">{module.description}</p>
              </div>
              <span className={`rounded-full border px-3 py-1 text-[11px] font-black uppercase tracking-[0.18em] ${toneClass(module.status)}`}>
                {module.status === 'live' ? 'Live' : 'Coming Soon'}
              </span>
            </div>
            {module.href ? (
              <button
                type="button"
                onClick={() => navigate(module.href)}
                className="mt-5 rounded-2xl border border-primary/15 px-4 py-3 text-sm font-semibold text-slate-600 transition-colors hover:border-primary/40 hover:text-primary"
              >
                Open {module.title}
              </button>
            ) : (
              <button
                type="button"
                onClick={focusQuickLookup}
                className="mt-5 rounded-2xl border border-primary/15 px-4 py-3 text-sm font-semibold text-slate-600 transition-colors hover:border-primary/40 hover:text-primary"
              >
                Use Quick Lookup
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="mt-8 rounded-[24px] border border-primary/10 bg-background-light p-6">
        <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">Service Notes</p>
        <ul className="mt-3 space-y-2 text-sm leading-7 text-slate-600">
          <li>Case data is sourced directly from official eCourts records, ensuring accuracy and up-to-date availability.</li>
          <li>Court and district references are cached for faster load times across all your searches.</li>
          <li>Case Status, Court Orders, and Cause List are fully active and available for all supported courts.</li>
        </ul>
        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          {readyModules} of {MODULES.length} search modules are currently active. Additional features will be available shortly.
        </div>
      </div>
    </div>
  );
}