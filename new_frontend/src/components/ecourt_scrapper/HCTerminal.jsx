import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getHCHealth, searchHCCnr } from './apiHC';

// Known 4-letter national HC codes used in CNR numbers.
// If a CNR starts with one of these the user should be sent to the HC detail page.
// Runtime-expandable — confirmed unknown prefixes are added during the session.
const HC_CNR_PREFIXES = new Set([
  'UPHC', 'DLHC', 'MHHC', 'TNHC', 'KRHC', 'KLHC', 'GJHC', 'RJHC', 'MPHC',
  'APHC', 'TSHC', 'PHHC', 'ORHC', 'AZHC', 'BRHC', 'JHHC', 'CGHC', 'HPHC',
  'UKHC', 'JKHC', 'MNHC', 'MLHC', 'TRHC', 'SKHC', 'WBHC',
  // Calcutta special prefixes
  'WBCHCJ', 'WBCHCO', 'WBCHCP',
]);

// Heuristic: 4-char prefix that starts with "HC" or ends with "HC" is likely a HC CNR
function looksLikeHcPrefix(p4) {
  return p4.startsWith('HC') || p4.endsWith('HC');
}

const HC_MODULES = [
  {
    key: 'case-status',
    title: 'Case Search',
    description: 'Search by CNR, party name, advocate, bar code, filing number, or FIR across any High Court bench.',
    href: '/ecourts/hc/case-status',
  },
  {
    key: 'court-orders',
    title: 'Court Orders',
    description: 'Retrieve court orders and judgements by party name, court/judge number, or date range with direct PDF links.',
    href: '/ecourts/hc/court-orders',
  },
  {
    key: 'cause-list',
    title: 'Cause List',
    description: 'Browse daily bench cause lists for any High Court. PDF links for each bench listing.',
    href: '/ecourts/hc/cause-list',
  },
];

export default function HCTerminal() {
  const navigate = useNavigate();
  const cnrInputRef = useRef(null);
  const [cnr, setCnr] = useState('');
  const [serviceOk, setServiceOk] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lookupError, setLookupError] = useState('');
  const [pendingCnr, setPendingCnr] = useState('');
  const [showConfirm, setShowConfirm] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    getHCHealth()
      .then((res) => { if (active) setServiceOk(res.data?.status === 'ok'); })
      .catch(() => { if (active) setServiceOk(false); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  function handleLookup() {
    const normalized = cnr.trim().toUpperCase().replace(/[-\s]/g, '');
    if (!normalized) return;
    setLookupError('');
    setShowConfirm(false);
    const prefix4 = normalized.slice(0, 4);
    const prefix6 = normalized.slice(0, 6);
    if (HC_CNR_PREFIXES.has(prefix6) || HC_CNR_PREFIXES.has(prefix4)) {
      navigate(`/ecourts/hc/case/${encodeURIComponent(normalized)}`);
    } else {
      // Unknown prefix — show soft confirmation instead of hard error
      setPendingCnr(normalized);
      setShowConfirm(true);
    }
  }

  function handleConfirmSearch() {
    // Remember this prefix for the rest of the session
    if (pendingCnr.length >= 4) {
      HC_CNR_PREFIXES.add(pendingCnr.slice(0, 4));
    }
    setShowConfirm(false);
    setPendingCnr('');
    navigate(`/ecourts/hc/case/${encodeURIComponent(pendingCnr)}`);
  }

  function handleCancelConfirm() {
    setShowConfirm(false);
    setPendingCnr('');
  }

  return (
    <div className="p-8 max-w-6xl">
      {/* ── Top bar: DC / HC toggle ── */}
      <div className="mb-6 flex gap-2">
        <button
          type="button"
          onClick={() => navigate('/ecourts')}
          className="rounded-2xl border border-primary/15 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:border-primary/40 hover:text-primary"
        >
          ← District Court
        </button>
        <span className="rounded-2xl bg-primary px-4 py-2 text-sm font-bold text-white">
          High Court
        </span>
      </div>

      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="text-[11px] font-black uppercase tracking-[0.28em] text-primary">High Court Case Search</p>
            <h1 className="mt-3 text-3xl font-black tracking-tight text-ink">Live access to High Court records across India</h1>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              Search and track cases from all 25 Indian High Courts. Access case status, court orders,
              cause lists, and CNR lookups — powered by hcservices.ecourts.gov.in.
            </p>
          </div>

          <div className="grid min-w-[200px] gap-3 sm:grid-cols-2 lg:w-[280px]">
            <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-4">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">HCs Covered</p>
              <p className="mt-2 text-2xl font-black text-ink">25</p>
            </div>
            <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-4">
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Service</p>
              <p className="mt-2 text-2xl font-black text-ink">
                {loading ? '…' : serviceOk ? '✓' : '—'}
              </p>
            </div>
          </div>
        </div>

        {/* CNR Quick Lookup */}
        <div className="mt-8 rounded-[24px] border border-primary/10 bg-background-light p-5">
          <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">CNR Quick Lookup</p>
          <div className="mt-3 flex flex-col gap-3 md:flex-row">
            <input
              ref={cnrInputRef}
              type="text"
              value={cnr}
              onChange={(e) => { setCnr(e.target.value.toUpperCase()); setLookupError(''); setShowConfirm(false); }}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleLookup(); } }}
              placeholder="Enter HC CNR (e.g. UPHC010551112017)"
              className="input-base flex-1 font-mono uppercase"
            />
            <button type="button" onClick={handleLookup} className="btn-primary flex items-center justify-center gap-2 md:min-w-[180px]">
              <span className="material-symbols-outlined text-base">search</span>
              Open Case
            </button>
          </div>

          {/* Soft confirmation for unknown prefixes */}
          {showConfirm && (
            <div className="mt-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3">
              <div className="flex items-start gap-2">
                <span className="material-symbols-outlined text-amber-500 text-base mt-0.5">warning</span>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-amber-800">
                    &ldquo;{pendingCnr.slice(0, 4)}&rdquo; is not in our known HC prefix list.
                  </p>
                  <p className="mt-0.5 text-xs text-amber-700">
                    {looksLikeHcPrefix(pendingCnr.slice(0, 4))
                      ? `${pendingCnr.slice(0, 4)} looks like it could be a High Court bench code (e.g. Bombay HC Mumbai bench = HCBM). You can still search — if a result comes back the prefix will be remembered.`
                      : 'This may be a district court CNR. If you are sure it is a High Court case, you can still search.'}
                  </p>
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      onClick={handleConfirmSearch}
                      className="rounded-xl bg-amber-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-amber-700"
                    >
                      Search Anyway
                    </button>
                    <button
                      type="button"
                      onClick={handleCancelConfirm}
                      className="rounded-xl border border-amber-300 px-3 py-1.5 text-xs font-semibold text-amber-700 hover:bg-amber-100"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {lookupError && (
            <p className="mt-2 text-xs text-red-600">{lookupError}</p>
          )}
          {!lookupError && !showConfirm && (
            <p className="mt-2 text-xs text-slate-500">
              HC CNRs start with the court code: UPHC (Allahabad), DLHC (Delhi), MHHC (Bombay), HCBM (Bombay Mumbai bench), WBHC (Calcutta), etc.
            </p>
          )}
        </div>
      </div>

      {/* Module cards */}
      <div className="mt-8 grid gap-4 lg:grid-cols-3">
        {HC_MODULES.map((module) => (
          <div key={module.key} className="rounded-[24px] border border-primary/10 bg-white p-6 shadow-sm">
            <p className="text-lg font-black text-ink">{module.title}</p>
            <p className="mt-2 text-sm leading-6 text-slate-600">{module.description}</p>
            <button
              type="button"
              onClick={() => navigate(module.href)}
              className="mt-5 rounded-2xl border border-primary/15 px-4 py-3 text-sm font-semibold text-slate-600 transition-colors hover:border-primary/40 hover:text-primary"
            >
              Open {module.title}
            </button>
          </div>
        ))}
      </div>

      <div className="mt-8 rounded-[24px] border border-primary/10 bg-background-light p-6">
        <p className="text-[11px] font-black uppercase tracking-[0.24em] text-slate-400">Note</p>
        <ul className="mt-3 space-y-2 text-sm leading-7 text-slate-600">
          <li>Response times may be 10–30 seconds depending on portal load.</li>
          <li>All 25 High Courts (+ circuit benches) are supported. Use <strong>Case Search → CNR</strong> for the fastest lookup.</li>
        </ul>
        {serviceOk === false && (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
            HC fetch service is currently unreachable. Ensure the HC backend server is running on correct port.
          </div>
        )}
      </div>
    </div>
  );
}
