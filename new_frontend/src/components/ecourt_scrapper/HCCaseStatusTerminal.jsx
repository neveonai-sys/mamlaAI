import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import HCCourtSelector from './HCCourtSelector';
import {
  searchHCCnr,
  searchHCParty,
  searchHCAdvocate,
  searchHCBarCode,
  searchHCFiling,
  searchHCFir,
  getHCPoliceStations,
} from './apiHC';

const TABS = [
  { key: 'cnr',       label: 'CNR' },
  { key: 'party',     label: 'Party Name' },
  { key: 'advocate',  label: 'Advocate' },
  { key: 'bar_code',  label: 'Bar Code' },
  { key: 'filing',    label: 'Filing No.' },
  { key: 'fir',       label: 'FIR' },
];

const STATUS_OPTIONS = ['Both', 'Pending', 'Disposed'];

const SESSION_KEY = 'hcCaseStatusSearchState';

function saveSession(state) {
  try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(state)); } catch (_) {}
}

function loadSession() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null'); } catch (_) { return null; }
}

// ── Case result card ─────────────────────────────────────────────────────────

function CaseCard({ item, onOpen }) {
  return (
    <div className="rounded-[18px] border border-primary/10 bg-background-light p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="truncate font-bold text-ink">{item.petitioner}</p>
          <p className="mt-0.5 truncate text-xs text-slate-500">vs {item.respondent}</p>
          <p className="mt-1 font-mono text-xs text-slate-400">{item.cino}</p>
        </div>
        <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-bold ${
          item.status === 'Pending'
            ? 'border-amber-200 bg-amber-50 text-amber-700'
            : 'border-emerald-200 bg-emerald-50 text-emerald-700'
        }`}>
          {item.status || 'Unknown'}
        </span>
      </div>
      <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-500">
        <span>{item.case_type_name} / {item.case_no} / {item.case_year}</span>
        {item.next_hearing && <span>· Next: {item.next_hearing}</span>}
      </div>
      <button
        type="button"
        onClick={() => onOpen(item.cino)}
        className="mt-3 rounded-xl border border-primary/15 px-3 py-1.5 text-xs font-semibold text-slate-600 transition-colors hover:border-primary/40 hover:text-primary"
      >
        View Details →
      </button>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function HCCaseStatusTerminal() {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const saved = loadSession();
  const [tab, setTab] = useState(saved?.tab || 'cnr');

  // Shared location
  const [location, setLocation] = useState(saved?.location || { hc: '', bench: '', isComplete: false });

  // CNR tab
  const [cnrInput, setCnrInput] = useState(saved?.cnrInput || '');

  // Party tab
  const [partyName, setPartyName]     = useState(saved?.partyName || '');
  const [partyYear, setPartyYear]     = useState(saved?.partyYear || '');
  const [partyStatus, setPartyStatus] = useState(saved?.partyStatus || 'Both');

  // Advocate tab
  const [advQuery, setAdvQuery]       = useState(saved?.advQuery || '');
  const [advStatus, setAdvStatus]     = useState(saved?.advStatus || 'Both');

  // Bar Code tab
  const [barCode, setBarCode]         = useState(saved?.barCode || '');
  const [barStatus, setBarStatus]     = useState(saved?.barStatus || 'Both');

  // Filing tab
  const [filingNo, setFilingNo]       = useState(saved?.filingNo || '');
  const [filingYear, setFilingYear]   = useState(saved?.filingYear || '');

  // FIR tab
  const [psCode, setPsCode]           = useState(saved?.psCode || '');
  const [psOptions, setPsOptions]     = useState([]);
  const [firNo, setFirNo]             = useState(saved?.firNo || '');
  const [firYear, setFirYear]         = useState(saved?.firYear || '');
  const [firStatus, setFirStatus]     = useState(saved?.firStatus || 'Both');
  const [loadingPS, setLoadingPS]     = useState(false);

  // Result state
  const [results, setResults]         = useState(saved?.results || null);
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState('');
  const [statusText, setStatusText]   = useState('');

  // Save session on key state changes
  useEffect(() => {
    saveSession({ tab, location, cnrInput, partyName, partyYear, partyStatus,
      advQuery, advStatus, barCode, barStatus, filingNo, filingYear,
      firNo, firYear, firStatus, psCode, results });
  }, [tab, location, cnrInput, partyName, partyYear, partyStatus, advQuery, advStatus,
      barCode, barStatus, filingNo, filingYear, firNo, firYear, firStatus, psCode, results]);

  // Load police stations when HC+bench selected and FIR tab active
  useEffect(() => {
    if (tab !== 'fir' || !location.hc || !location.bench) return;
    let active = true;
    setLoadingPS(true);
    getHCPoliceStations(location.hc, location.bench)
      .then((res) => { if (active) setPsOptions(res.data || []); })
      .catch(() => { if (active) setPsOptions([]); })
      .finally(() => { if (active) setLoadingPS(false); });
    return () => { active = false; };
  }, [tab, location.hc, location.bench]);

  function clearResults() {
    setResults(null);
    setError('');
    setStatusText('');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    clearResults();
    setLoading(true);
    dispatch(beginBlocking({ message: 'Searching High Court cases...' }));

    try {
      let res;
      if (tab === 'cnr') {
        const normalized = cnrInput.trim().toUpperCase().replace(/[-\s]/g, '');
        if (!normalized) { setError('Enter a CNR number.'); setLoading(false); dispatch(stopBlocking()); return; }
        navigate(`/ecourts/hc/case/${encodeURIComponent(normalized)}`);
        setLoading(false);
        dispatch(stopBlocking());
        return;
      }
      if (!location.isComplete) { setError('Select a High Court and Bench first.'); setLoading(false); dispatch(stopBlocking()); return; }

      if (tab === 'party') {
        res = await searchHCParty({ hc: location.hc, bench: location.bench, name: partyName, year: partyYear, status: partyStatus });
      } else if (tab === 'advocate') {
        res = await searchHCAdvocate({ hc: location.hc, bench: location.bench, query: advQuery, status: advStatus });
      } else if (tab === 'bar_code') {
        res = await searchHCBarCode({ hc: location.hc, bench: location.bench, bar_code: barCode, status: barStatus });
      } else if (tab === 'filing') {
        res = await searchHCFiling({ hc: location.hc, bench: location.bench, filing_number: filingNo, year: filingYear });
      } else if (tab === 'fir') {
        res = await searchHCFir({ hc: location.hc, bench: location.bench, police_station: psCode, status: firStatus, fir_number: firNo, fir_year: firYear });
      }

      const data = res.data;
      const caseList = data?.cases || [];
      setResults(caseList);
      setStatusText(
        data?.total != null
          ? `${data.total} result${data.total !== 1 ? 's' : ''} — ${data.high_court}${data.bench ? ', ' + data.bench : ''}`
          : `${caseList.length} result${caseList.length !== 1 ? 's' : ''}`
      );
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.detail || 'Search failed. Please try again.');
    } finally {
      setLoading(false);
      dispatch(stopBlocking());
    }
  }

  return (
    <div className="p-8 max-w-5xl">
      {/* Back + title */}
      <div className="mb-4 flex items-center gap-3">
        <button type="button" onClick={() => navigate('/ecourts/hc')}
          className="rounded-xl border border-primary/15 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-primary">
          ← High Court
        </button>
        <h1 className="text-2xl font-black text-ink">Case Search</h1>
      </div>

      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        {/* Tabs */}
        <div className="flex flex-wrap gap-2 border-b border-primary/10 pb-4">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => { setTab(t.key); clearResults(); }}
              className={`rounded-xl px-4 py-2 text-sm font-semibold transition-colors ${
                tab === t.key
                  ? 'bg-primary text-white'
                  : 'border border-primary/15 text-slate-600 hover:border-primary/40 hover:text-primary'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">

          {/* CNR tab */}
          {tab === 'cnr' && (
            <div>
              <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">CNR Number</label>
              <input
                type="text"
                value={cnrInput}
                onChange={(e) => setCnrInput(e.target.value.toUpperCase())}
                placeholder="e.g. UPHC010551112017"
                className="input-base w-full font-mono uppercase"
              />
              <p className="mt-1 text-xs text-slate-500">HC and bench are auto-detected from the CNR prefix.</p>
            </div>
          )}

          {/* All other tabs need HC selector */}
          {tab !== 'cnr' && (
            <HCCourtSelector
              onChange={setLocation}
              initialValues={saved?.location}
            />
          )}

          {tab === 'party' && (
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Party Name</label>
                <input type="text" value={partyName} onChange={(e) => setPartyName(e.target.value)}
                  placeholder="Min. 3 characters" className="input-base w-full" required />
              </div>
              <div className="w-32">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Year</label>
                <input type="text" value={partyYear} onChange={(e) => setPartyYear(e.target.value)}
                  placeholder="2024" maxLength={4} className="input-base w-full" required />
              </div>
              <div className="w-36">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Status</label>
                <select value={partyStatus} onChange={(e) => setPartyStatus(e.target.value)} className="input-base w-full">
                  {STATUS_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
            </div>
          )}

          {tab === 'advocate' && (
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Advocate Name</label>
                <input type="text" value={advQuery} onChange={(e) => setAdvQuery(e.target.value)}
                  placeholder="Min. 3 characters" className="input-base w-full" required />
              </div>
              <div className="w-36">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Status</label>
                <select value={advStatus} onChange={(e) => setAdvStatus(e.target.value)} className="input-base w-full">
                  {STATUS_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
            </div>
          )}

          {tab === 'bar_code' && (
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Bar Registration Code</label>
                <input type="text" value={barCode} onChange={(e) => setBarCode(e.target.value)}
                  placeholder="e.g. UP12345 or MH/1234/2005" className="input-base w-full" required />
              </div>
              <div className="w-36">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Status</label>
                <select value={barStatus} onChange={(e) => setBarStatus(e.target.value)} className="input-base w-full">
                  {STATUS_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              </div>
            </div>
          )}

          {tab === 'filing' && (
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Filing Number</label>
                <input type="text" value={filingNo} onChange={(e) => setFilingNo(e.target.value)}
                  placeholder="e.g. 32226" className="input-base w-full" required />
              </div>
              <div className="w-32">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Year</label>
                <input type="text" value={filingYear} onChange={(e) => setFilingYear(e.target.value)}
                  placeholder="2024" maxLength={4} className="input-base w-full" required />
              </div>
            </div>
          )}

          {tab === 'fir' && (
            <>
              <div className="flex flex-col gap-4 sm:flex-row">
                <div className="flex-1">
                  <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Police Station</label>
                  <select
                    value={psCode}
                    onChange={(e) => setPsCode(e.target.value)}
                    disabled={loadingPS || !location.isComplete}
                    className="input-base w-full"
                    required
                  >
                    <option value="">{loadingPS ? 'Loading…' : !location.isComplete ? 'Select HC + bench first' : 'Select Police Station'}</option>
                    {psOptions.map((ps) => (
                      <option key={ps.code} value={ps.code}>{ps.name}</option>
                    ))}
                  </select>
                </div>
                <div className="w-36">
                  <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Status</label>
                  <select value={firStatus} onChange={(e) => setFirStatus(e.target.value)} className="input-base w-full">
                    {STATUS_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                </div>
              </div>
              <div className="flex flex-col gap-4 sm:flex-row">
                <div className="flex-1">
                  <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">FIR Number (optional)</label>
                  <input type="text" value={firNo} onChange={(e) => setFirNo(e.target.value)} placeholder="e.g. 123" className="input-base w-full" />
                </div>
                <div className="w-32">
                  <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">FIR Year (optional)</label>
                  <input type="text" value={firYear} onChange={(e) => setFirYear(e.target.value)} placeholder="2024" maxLength={4} className="input-base w-full" />
                </div>
              </div>
            </>
          )}

          {error && (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary flex items-center justify-center gap-2 self-start px-8"
          >
            {loading ? (
              <span className="material-symbols-outlined animate-spin text-base">progress_activity</span>
            ) : (
              <span className="material-symbols-outlined text-base">search</span>
            )}
            {loading ? 'Searching…' : tab === 'cnr' ? 'Open Case' : 'Search'}
          </button>
        </form>
      </div>

      {/* Results */}
      {results !== null && (
        <div className="mt-6">
          <p className="mb-3 text-sm font-semibold text-slate-500">{statusText}</p>
          {results.length === 0 ? (
            <div className="rounded-[24px] border border-primary/10 bg-white p-6 text-center text-slate-500">
              No cases found matching your search.
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {results.map((item) => (
                <CaseCard key={item.cino} item={item} onOpen={(cino) => navigate(`/ecourts/hc/case/${encodeURIComponent(cino)}`)} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
