import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import HCCourtSelector from './HCCourtSelector';
import {
  searchHCOrdersByParty,
  searchHCOrdersByCourt,
  searchHCOrdersByDate,
  getHCCourtNumbers,
} from './apiHC';

const TABS = [
  { key: 'party', label: 'By Party' },
  { key: 'court', label: 'By Court / Judge' },
  { key: 'date',  label: 'By Date Range' },
];

const SESSION_KEY = 'hcCourtOrdersSearchState';

function saveSession(s) { try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(s)); } catch (_) {} }
function loadSession()  { try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null'); } catch (_) { return null; } }

// DD-MM-YYYY ↔ YYYY-MM-DD helpers ─────────────────────────────────────────────

function toIso(dmy) {
  // "04-04-2026" → "2026-04-04"
  if (!dmy || !dmy.includes('-')) return dmy;
  const [d, m, y] = dmy.split('-');
  return `${y}-${m}-${d}`;
}

function toDmy(iso) {
  // "2026-04-04" → "04-04-2026"
  if (!iso || !iso.includes('-')) return iso;
  const [y, m, d] = iso.split('-');
  return `${d}-${m}-${y}`;
}

// Date input that stores ISO (YYYY-MM-DD) internally for <input type="date"> ──

function DateField({ label, value, onChange }) {
  return (
    <div className="flex-1">
      <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">{label}</label>
      <input type="date" value={value} onChange={(e) => onChange(e.target.value)} className="input-base w-full" required />
    </div>
  );
}

// Order result card ─────────────────────────────────────────────────────────────

function OrderCard({ item, onOpen }) {
  // Build case number display: prefer reg_no/reg_year, fall back to fil_no/fil_year (on filing)
  const caseNum = (() => {
    const type = item.case_type_name || '';
    if (item.reg_no && item.reg_year) return `${type} / ${item.reg_no} / ${item.reg_year}`;
    if (item.fil_no && item.fil_year) return `${type} / ${item.fil_no} / ${item.fil_year} (on filing)`;
    if (item.case_no) return `${type} / ${item.case_no}`;
    return type || '—';
  })();

  return (
    <div className="rounded-[18px] border border-primary/10 bg-background-light p-4">
      <div className="min-w-0">
        <p className="font-mono text-xs text-slate-400">{item.cino}</p>
        <p className="mt-0.5 font-bold text-ink">{caseNum}</p>
        {item.order_date && <p className="mt-0.5 text-sm text-slate-500">Order date: {item.order_date}</p>}
        {item.document_name && <p className="text-xs text-slate-400">{item.document_name}</p>}
      </div>
      <button
        type="button"
        onClick={() => onOpen(item.cino)}
        className="mt-3 rounded-xl border border-primary/15 px-3 py-1.5 text-xs font-semibold text-slate-600 transition-colors hover:border-primary/40 hover:text-primary"
      >
        View Case →
      </button>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function HCCourtOrdersTerminal() {
  const navigate = useNavigate();

  const saved = loadSession();
  const [tab, setTab] = useState(saved?.tab || 'party');
  const [location, setLocation] = useState(saved?.location || { hc: '', bench: '', isComplete: false });

  // Party tab
  const [partyName, setPartyName] = useState(saved?.partyName || '');
  const [partyYear, setPartyYear] = useState(saved?.partyYear || '');

  // Court tab
  const [judgeCode, setJudgeCode]         = useState(saved?.judgeCode || '');
  const [courtOptions, setCourtOptions]   = useState([]);
  const [courtDateFrom, setCourtDateFrom] = useState(saved?.courtDateFrom || '');
  const [courtDateTo, setCourtDateTo]     = useState(saved?.courtDateTo || '');
  const [loadingCourt, setLoadingCourt]   = useState(false);

  function handleJudgeChange(code) {
    setJudgeCode(code);
    const match = courtOptions.find((c) => c.court_code === code);
    setCourtDateFrom(match?.date_from || '');
    const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
    setCourtDateTo(match?.date_to || today);
  }

  // Date tab — stored as ISO internally, converted to DD-MM-YYYY when sending
  const [dateFrom, setDateFrom] = useState(saved?.dateFrom || '');
  const [dateTo, setDateTo]     = useState(saved?.dateTo || '');

  const [results, setResults]     = useState(saved?.results || null);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');
  const [statusText, setStatusText] = useState('');

  useEffect(() => {
    saveSession({ tab, location, partyName, partyYear, judgeCode, courtDateFrom, courtDateTo, dateFrom, dateTo, results });
  }, [tab, location, partyName, partyYear, judgeCode, courtDateFrom, courtDateTo, dateFrom, dateTo, results]);

  // Load court numbers when HC+bench selected and court tab is active
  useEffect(() => {
    if (tab !== 'court' || !location.hc || !location.bench) return;
    let active = true;
    setLoadingCourt(true);
    getHCCourtNumbers(location.hc, location.bench)
      .then((res) => {
        if (!active) return;
        const options = res.data || [];
        setCourtOptions(options);
        // Re-populate dates if a judgeCode was already set (e.g. from session restore)
        if (judgeCode) {
          const match = options.find((c) => c.court_code === judgeCode);
          if (match) {
            setCourtDateFrom(match.date_from || '');
            const today = new Date().toISOString().slice(0, 10);
            setCourtDateTo(match.date_to || today);
          }
        }
      })
      .catch(() => { if (active) setCourtOptions([]); })
      .finally(() => { if (active) setLoadingCourt(false); });
    return () => { active = false; };
  }, [tab, location.hc, location.bench]);

  function clearResults() { setResults(null); setError(''); setStatusText(''); }

  async function handleSubmit(e) {
    e.preventDefault();
    clearResults();
    if (!location.isComplete) { setError('Select a High Court and Bench first.'); return; }
    if (tab === 'party') {
      if (!partyName.trim()) { setError('Party name is required.'); return; }
      if (!/^\d{4}$/.test(partyYear.trim())) { setError('Year is required and must be a 4-digit number.'); return; }
    }
    if (tab === 'court') {
      if (!judgeCode) { setError('Select a court / judge.'); return; }
      if (!courtDateFrom || !courtDateTo) { setError('Date range is required. Please re-select the judge.'); return; }
    }
    setLoading(true);

    try {
      let res;
      if (tab === 'party') {
        res = await searchHCOrdersByParty({ hc: location.hc, bench: location.bench, name: partyName, year: partyYear });
      } else if (tab === 'court') {
        res = await searchHCOrdersByCourt({
          hc: location.hc, bench: location.bench,
          judge_code: judgeCode,
          date_from: courtDateFrom,   // YYYY-MM-DD
          date_to: courtDateTo,
        });
      } else if (tab === 'date') {
        res = await searchHCOrdersByDate({
          hc: location.hc, bench: location.bench,
          date_from: toDmy(dateFrom),   // convert to DD-MM-YYYY
          date_to: toDmy(dateTo),
        });
      }

      const data = res.data;
      const list = data?.orders || [];
      setResults(list);
      setStatusText(
        data?.total != null
          ? `${data.total} order${data.total !== 1 ? 's' : ''} — ${data.high_court}${data.bench ? ', ' + data.bench : ''}`
          : `${list.length} order${list.length !== 1 ? 's' : ''}`
      );
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.detail || 'Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-4 flex items-center gap-3">
        <button type="button" onClick={() => navigate('/ecourts/hc')}
          className="rounded-xl border border-primary/15 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-primary">
          ← High Court
        </button>
        <h1 className="text-2xl font-black text-ink">Court Orders</h1>
      </div>

      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        {/* Tabs */}
        <div className="flex flex-wrap gap-2 border-b border-primary/10 pb-4">
          {TABS.map((t) => (
            <button key={t.key} type="button"
              onClick={() => { setTab(t.key); clearResults(); }}
              className={`rounded-xl px-4 py-2 text-sm font-semibold transition-colors ${
                tab === t.key ? 'bg-primary text-white' : 'border border-primary/15 text-slate-600 hover:border-primary/40 hover:text-primary'
              }`}>
              {t.label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <HCCourtSelector onChange={setLocation} initialValues={saved?.location} />

          {tab === 'party' && (
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Party Name</label>
                <input type="text" value={partyName} onChange={(e) => setPartyName(e.target.value)}
                  placeholder="Petitioner or respondent name" className="input-base w-full" required />
              </div>
              <div className="w-32">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Year</label>
                <input type="text" value={partyYear} onChange={(e) => setPartyYear(e.target.value)}
                  placeholder="2024" maxLength={4} className="input-base w-full" required />
              </div>
            </div>
          )}

          {tab === 'court' && (
            <div className="flex flex-col gap-4">
              <div>
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Court / Judge</label>
                <select value={judgeCode} onChange={(e) => handleJudgeChange(e.target.value)}
                  disabled={loadingCourt || !location.isComplete} className="input-base w-full" required>
                  <option value="">{loadingCourt ? 'Loading…' : !location.isComplete ? 'Select HC + bench first' : 'Select court / judge'}</option>
                  {courtOptions.map((c) => (
                    <option key={c.court_code} value={c.court_code}>{c.judge_name} ({c.court_code})</option>
                  ))}
                </select>
              </div>
              {courtDateFrom && (
                <div className="flex gap-4">
                  <div className="flex-1">
                    <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">From date</label>
                    <input type="text" value={courtDateFrom} readOnly
                      className="input-base w-full cursor-default bg-slate-50 text-slate-500" />
                  </div>
                  <div className="flex-1">
                    <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">To date</label>
                    <input type="text" value={courtDateTo} readOnly
                      className="input-base w-full cursor-default bg-slate-50 text-slate-500" />
                  </div>
                </div>
              )}
            </div>
          )}

          {tab === 'date' && (
            <div className="flex flex-col gap-4">
              <div className="flex gap-4">
                <DateField label="From date" value={dateFrom} onChange={setDateFrom} />
                <DateField label="To date" value={dateTo} onChange={setDateTo} />
              </div>
              <p className="text-xs text-slate-400">Retrieves all orders issued within this date range.</p>
            </div>
          )}

          {error && (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
          )}

          <button type="submit" disabled={loading}
            className="btn-primary flex items-center justify-center gap-2 self-start px-8">
            {loading
              ? <span className="material-symbols-outlined animate-spin text-base">progress_activity</span>
              : <span className="material-symbols-outlined text-base">search</span>}
            {loading ? 'Searching…' : 'Search Orders'}
          </button>
        </form>
      </div>

      {/* Results */}
      {results !== null && (
        <div className="mt-6">
          <p className="mb-3 text-sm font-semibold text-slate-500">{statusText}</p>
          {results.length === 0 ? (
            <div className="rounded-[24px] border border-primary/10 bg-white p-6 text-center text-slate-500">
              No orders found.
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {results.map((item, idx) => (
                <OrderCard
                  key={`${item.cino}-${item.order_no || idx}`}
                  item={item}
                  onOpen={(cino) => navigate(`/ecourts/hc/case/${encodeURIComponent(cino)}`)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
