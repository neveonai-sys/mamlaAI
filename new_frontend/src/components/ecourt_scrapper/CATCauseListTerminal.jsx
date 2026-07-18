import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import { getCATBenches, getCATCauseList } from './apiCAT';

function todayDDMMYYYY() {
  const d = new Date();
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  return `${dd}-${mm}-${d.getFullYear()}`;
}

function CaseRow({ item }) {
  return (
    <div className="rounded-[18px] border border-primary/10 bg-background-light p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="truncate font-bold text-ink">{item.case_number}</p>
          <p className="mt-0.5 truncate text-xs text-slate-500">{item.parties}</p>
          {item.court && <p className="mt-1 text-[11px] text-slate-400">{item.court}</p>}
        </div>
        {item.sr_no && (
          <span className="shrink-0 rounded-full border border-primary/15 bg-white px-2 py-0.5 text-[11px] font-bold text-slate-600">
            #{item.sr_no}
          </span>
        )}
      </div>
      {(item.purpose || item.advocate) && (
        <p className="mt-2 text-[11px] text-slate-500">
          {item.purpose}{item.purpose && item.advocate ? ' · ' : ''}{item.advocate}
        </p>
      )}
    </div>
  );
}

export default function CATCauseListTerminal() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [benches, setBenches] = useState([]);
  const [loadingBenches, setLoadingBenches] = useState(true);

  const [bench, setBench] = useState('');
  const [date, setDate] = useState(todayDDMMYYYY());

  const [result, setResult] = useState(null);
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
    setResult(null);
    setError('');
    setLoading(true);
    dispatch(beginBlocking({ message: 'Fetching cause list...' }));

    try {
      const res = await getCATCauseList({ bench, date });
      setResult(res.data);
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
        <h1 className="text-2xl font-black text-ink">Cause List</h1>
      </div>

      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Bench</label>
            <select value={bench} onChange={(e) => setBench(e.target.value)} className="input-base w-full" disabled={loadingBenches} required>
              <option value="">{loadingBenches ? 'Loading…' : 'Select Bench'}</option>
              {benches.map((b) => (
                <option key={b.slug} value={b.slug}>{b.name}</option>
              ))}
            </select>
          </div>
          <div className="w-44">
            <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Date (dd-mm-yyyy)</label>
            <input type="text" value={date} onChange={(e) => setDate(e.target.value)}
              placeholder="04-04-2026" className="input-base w-full" required />
          </div>
          <button
            type="submit"
            disabled={loading || !bench}
            className="btn-primary flex items-center justify-center gap-2 px-8"
          >
            {loading ? (
              <span className="material-symbols-outlined animate-spin text-base">progress_activity</span>
            ) : (
              <span className="material-symbols-outlined text-base">search</span>
            )}
            {loading ? 'Fetching…' : 'Get Cause List'}
          </button>
        </form>

        {error && (
          <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}
      </div>

      {result && (
        <div className="mt-6">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-semibold text-slate-500">
              {result.total_cases || 0} case{result.total_cases !== 1 ? 's' : ''} · {result.bench} · {result.date}
            </p>
            {result.pdf_url && (
              <a href={result.pdf_url} target="_blank" rel="noreferrer" className="text-xs font-semibold text-primary hover:underline">
                View Full Cause List PDF →
              </a>
            )}
          </div>
          {(!result.cases || result.cases.length === 0) ? (
            <div className="rounded-[24px] border border-primary/10 bg-white p-6 text-center text-slate-500">
              {result.message || 'No cause list found for this bench and date.'}
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {result.cases.map((item, i) => (
                <CaseRow key={i} item={item} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
