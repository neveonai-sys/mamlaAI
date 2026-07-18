import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import { getCATBenches, searchCATJudgments } from './apiCAT';

function JudgmentRow({ item }) {
  return (
    <div className="rounded-[18px] border border-primary/10 bg-background-light p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="truncate font-bold text-ink">{item.title || item.col_0 || 'Judgment'}</p>
          <p className="mt-1 text-xs text-slate-500">{item.col_1 || ''}</p>
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

export default function CATJudgmentsTerminal() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [benches, setBenches] = useState([]);
  const [loadingBenches, setLoadingBenches] = useState(true);

  const [bench, setBench] = useState('all');
  const [query, setQuery] = useState('');
  const [fromYear, setFromYear] = useState('2020');
  const [toYear, setToYear] = useState('');

  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setLoadingBenches(true);
    getCATBenches()
      .then((res) => { if (active) setBenches(res.data || []); })
      .catch(() => { if (active) setBenches([]); })
      .finally(() => { if (active) setLoadingBenches(false); });
    return () => { active = false; };
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setResults(null);
    setError('');
    setLoading(true);
    dispatch(beginBlocking({ message: 'Searching CAT judgments...' }));

    try {
      const res = await searchCATJudgments({ bench, query, from_year: fromYear, to_year: toYear });
      setResults(res.data?.judgments || []);
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
        <h1 className="text-2xl font-black text-ink">Judgments</h1>
      </div>

      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="w-56">
              <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Bench</label>
              <select value={bench} onChange={(e) => setBench(e.target.value)} className="input-base w-full" disabled={loadingBenches}>
                <option value="all">All Benches</option>
                {benches.map((b) => (
                  <option key={b.slug} value={b.slug}>{b.name}</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Keywords</label>
              <input type="text" value={query} onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. departmental promotion" className="input-base w-full" required />
            </div>
          </div>
          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="w-32">
              <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">From Year</label>
              <input type="text" value={fromYear} onChange={(e) => setFromYear(e.target.value)}
                placeholder="2020" maxLength={4} className="input-base w-full" />
            </div>
            <div className="w-32">
              <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">To Year</label>
              <input type="text" value={toYear} onChange={(e) => setToYear(e.target.value)}
                placeholder="2026" maxLength={4} className="input-base w-full" />
            </div>
          </div>

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
              No judgments found matching your search.
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {results.map((item, i) => (
                <JudgmentRow key={i} item={item} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
