import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import { getCATBenches, getCATCaseTypes, getCATOrdersDaily, getCATOrdersFinal } from './apiCAT';

const TABS = [
  { key: 'daily', label: 'Daily Orders' },
  { key: 'final', label: 'Final Orders' },
];

function OrderRow({ item }) {
  const dateVal = item['Order Date'] || item.col_0 || '—';
  return (
    <div className="rounded-[18px] border border-primary/10 bg-background-light p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="font-mono text-xs text-slate-400">{dateVal}</p>
          <p className="mt-1 truncate text-sm text-ink">{item['Order Type'] || item.col_1 || ''}</p>
        </div>
        {item.pdf_url && (
          <a
            href={item.pdf_url}
            target="_blank"
            rel="noreferrer"
            className="shrink-0 rounded-xl border border-primary/15 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:border-primary/40 hover:text-primary"
          >
            View PDF
          </a>
        )}
      </div>
    </div>
  );
}

export default function CATOrdersTerminal() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [tab, setTab] = useState('daily');

  const [benches, setBenches] = useState([]);
  const [caseTypes, setCaseTypes] = useState([]);
  const [loadingMeta, setLoadingMeta] = useState(true);

  const [bench, setBench] = useState('');
  const [date, setDate] = useState('');

  const [caseType, setCaseType] = useState('');
  const [caseNo, setCaseNo] = useState('');
  const [caseYear, setCaseYear] = useState('');

  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setLoadingMeta(true);
    Promise.all([getCATBenches(), getCATCaseTypes()])
      .then(([benchesRes, typesRes]) => {
        if (!active) return;
        setBenches(benchesRes.data || []);
        setCaseTypes(typesRes.data || []);
      })
      .catch(() => { if (active) { setBenches([]); setCaseTypes([]); } })
      .finally(() => { if (active) setLoadingMeta(false); });
    return () => { active = false; };
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setResults(null);
    setError('');
    setLoading(true);
    dispatch(beginBlocking({ message: 'Fetching orders...' }));

    try {
      let res;
      if (tab === 'daily') {
        res = await getCATOrdersDaily({ bench, date });
      } else {
        res = await getCATOrdersFinal({ bench, case_type: caseType, case_no: caseNo, year: caseYear });
      }
      setResults(res.data?.orders || []);
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.detail || 'Search failed. Please try again.');
    } finally {
      setLoading(false);
      dispatch(stopBlocking());
    }
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-4 flex items-center gap-3">
        <button type="button" onClick={() => navigate('/ecourts/cat')}
          className="rounded-xl border border-primary/15 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-primary">
          ← CAT
        </button>
        <h1 className="text-2xl font-black text-ink">Orders</h1>
      </div>

      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <div className="flex flex-wrap gap-2 border-b border-primary/10 pb-4">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => { setTab(t.key); setResults(null); setError(''); }}
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

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <div className="flex-1">
            <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Bench</label>
            <select value={bench} onChange={(e) => setBench(e.target.value)} className="input-base w-full sm:w-72" disabled={loadingMeta} required>
              <option value="">{loadingMeta ? 'Loading…' : 'Select Bench'}</option>
              {benches.map((b) => (
                <option key={b.slug} value={b.slug}>{b.name}</option>
              ))}
            </select>
          </div>

          {tab === 'daily' && (
            <div className="w-44">
              <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Date (dd-mm-yyyy)</label>
              <input type="text" value={date} onChange={(e) => setDate(e.target.value)}
                placeholder="04-04-2026" className="input-base w-full" required />
            </div>
          )}

          {tab === 'final' && (
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Case Type</label>
                <select value={caseType} onChange={(e) => setCaseType(e.target.value)} className="input-base w-full" disabled={loadingMeta} required>
                  <option value="">{loadingMeta ? 'Loading…' : 'Select Case Type'}</option>
                  {caseTypes.map((ct) => (
                    <option key={ct.code} value={ct.code}>{ct.name}</option>
                  ))}
                </select>
              </div>
              <div className="w-32">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Case No.</label>
                <input type="text" value={caseNo} onChange={(e) => setCaseNo(e.target.value)}
                  placeholder="e.g. 1265" className="input-base w-full" required />
              </div>
              <div className="w-28">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Year</label>
                <input type="text" value={caseYear} onChange={(e) => setCaseYear(e.target.value)}
                  placeholder="2024" maxLength={4} className="input-base w-full" required />
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
          )}

          <button
            type="submit"
            disabled={loading || !bench}
            className="btn-primary flex items-center justify-center gap-2 self-start px-8"
          >
            {loading ? (
              <span className="material-symbols-outlined animate-spin text-base">progress_activity</span>
            ) : (
              <span className="material-symbols-outlined text-base">search</span>
            )}
            {loading ? 'Searching…' : 'Search'}
          </button>
        </form>
      </div>

      {results !== null && (
        <div className="mt-6">
          <p className="mb-3 text-sm font-semibold text-slate-500">
            {results.length} result{results.length !== 1 ? 's' : ''}
          </p>
          {results.length === 0 ? (
            <div className="rounded-[24px] border border-primary/10 bg-white p-6 text-center text-slate-500">
              No orders found matching your search.
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {results.map((item, i) => (
                <OrderRow key={i} item={item} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
