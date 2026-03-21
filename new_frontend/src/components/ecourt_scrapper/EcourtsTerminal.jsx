import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import apiClient from '../../services/api';

const MODULES = [
  {
    key: 'cnr',
    title: 'CNR Lookup',
    description: 'Direct case fetch through the scraper runtime with cached detail and order access.',
    status: 'live',
    href: null,
  },
  {
    key: 'case-status',
    title: 'Case Status',
    description: 'Stitched case-status flow, with the advocate path live on the scraper and staged modes shown explicitly.',
    status: 'live',
    href: '/ecourts/case-status',
  },
  {
    key: 'court-orders',
    title: 'Court Orders',
    description: 'Scraper-first court orders via CNR-backed case cache and parsed order rows.',
    status: 'live',
    href: '/ecourts/court-orders',
  },
  {
    key: 'cause-list',
    title: 'Cause List',
    description: 'High-court cause lists are live now, with district-court reference data already stored in Mongo.',
    status: 'live',
    href: '/ecourts/cause-list',
  },
  {
    key: 'caveat',
    title: 'Caveat',
    description: 'Mapped into the terminal with reference data and a staged scraper implementation notice.',
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
        const [courtStructure, districtStates, caseStatusRef, orderRef, causeListRef, caveatRef] = await Promise.all([
          apiClient.get('ecourts/court-structure/'),
          apiClient.get('ecourts/court-structure/district/states/'),
          apiClient.get('ecourts/reference/case-status/'),
          apiClient.get('ecourts/reference/court-orders/'),
          apiClient.get('ecourts/reference/cause-list/'),
          apiClient.get('ecourts/reference/caveat/'),
        ]);

        if (!active) return;

        const structureData = courtStructure.data?.data || {};
        const districtStateRows = districtStates.data?.data || [];
        const references = [caseStatusRef, orderRef, causeListRef, caveatRef].filter(
          (response) => Array.isArray(response.data?.data?.tabs) || Array.isArray(response.data?.data?.search_modes) || Array.isArray(response.data?.data?.list_types),
        );

        setStats({
          districtStates: districtStateRows.length,
          highCourts: (structureData.high_courts || []).length,
          referencesReady: references.length,
        });
      } catch (err) {
        if (!active) return;
        setError(err.response?.data?.error || 'Unable to load scraper terminal metadata right now.');
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
            <p className="text-[11px] font-black uppercase tracking-[0.28em] text-primary">Scraper-first eCourts</p>
            <h1 className="mt-3 text-3xl font-black tracking-tight text-ink">New terminal flow is now anchored on the scraper runtime</h1>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              The third-party partner API is being retired from runtime. This screen tracks the stitched-module migration while routing live case lookups through the scraper stack and Mongo-backed reference datasets.
            </p>
          </div>

          <div className="grid min-w-[280px] gap-3 sm:grid-cols-3 lg:w-[420px]">
            <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-4">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">District States</p>
              <p className="mt-2 text-2xl font-black text-ink">{loading ? '...' : stats.districtStates || '0'}</p>
            </div>
            <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-4">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">High Courts</p>
              <p className="mt-2 text-2xl font-black text-ink">{loading ? '...' : stats.highCourts || '0'}</p>
            </div>
            <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-4">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Reference Sets</p>
              <p className="mt-2 text-2xl font-black text-ink">{loading ? '...' : stats.referencesReady || '0'}</p>
            </div>
          </div>
        </div>

        {error ? (
          <div className="mt-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <div className="mt-8 rounded-[24px] border border-primary/10 bg-background-light p-5">
          <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">Live right now</p>
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
              placeholder="Enter 16-20 character CNR"
              className="input-base flex-1 font-mono uppercase"
            />
            <button type="button" onClick={handleLookup} className="btn-primary flex items-center justify-center gap-2 md:min-w-[180px]">
              <span className="material-symbols-outlined text-base">search</span>
              Open Case
            </button>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            This calls the scraper-backed case lookup and continues into the existing case-detail screen.
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
                {module.status === 'live' ? 'Live' : 'In migration'}
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
        <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">Migration notes</p>
        <ul className="mt-3 space-y-2 text-sm leading-7 text-slate-600">
          <li>The runtime route has moved to `ecourts_scraper` and no longer consumes `ECOURT_TOKEN`.</li>
          <li>Reference dropdown payloads are now stored in Mongo under `ecourts_reference_data` for reuse across sessions.</li>
          <li>The new terminal now routes active stitched screens for case status, court orders, and cause list through scraper-aware UI.</li>
        </ul>
        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          {readyModules} of {MODULES.length} module surfaces are fully live in this first migration slice. The remaining stitched screens are being moved off the old direct-API assumptions next.
        </div>
      </div>
    </div>
  );
}