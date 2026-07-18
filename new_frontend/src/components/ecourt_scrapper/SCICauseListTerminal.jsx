import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import { getSCICauseListToday, getSCICauseListTomorrow, getSCICauseListByDate } from './apiSCI';

const MODES = [
  { key: 'today',    label: 'Today' },
  { key: 'tomorrow', label: 'Tomorrow' },
  { key: 'by-date',  label: 'Specific Date' },
];

function CauseListRow({ item }) {
  return (
    <div className="rounded-[18px] border border-primary/10 bg-background-light p-4">
      <p className="font-bold text-ink">{item.petitioner || item.case_title || 'Case'}</p>
      {item.respondent && <p className="mt-0.5 text-xs text-slate-500">vs {item.respondent}</p>}
      <p className="mt-1 font-mono text-xs text-slate-400">
        {item.diary_no ? `Diary ${item.diary_no}/${item.diary_year}` : ''}
        {item.case_no ? ` · ${item.case_no}/${item.case_year}` : ''}
      </p>
      {item.court_no && <p className="mt-1 text-[11px] text-slate-500">Court No. {item.court_no}</p>}
    </div>
  );
}

export default function SCICauseListTerminal() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [mode, setMode] = useState('today');
  const [date, setDate] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e) {
    e.preventDefault();
    setResults(null);
    setError('');
    setLoading(true);
    dispatch(beginBlocking({ message: 'Fetching Supreme Court cause list...' }));

    try {
      let res;
      if (mode === 'today') res = await getSCICauseListToday();
      else if (mode === 'tomorrow') res = await getSCICauseListTomorrow();
      else res = await getSCICauseListByDate(date);

      const data = res.data;
      const list = data?.cases || data?.items || (Array.isArray(data) ? data : []);
      setResults(list);
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.detail || 'Failed to fetch cause list.');
    } finally {
      setLoading(false);
      dispatch(stopBlocking());
    }
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-4 flex items-center gap-3">
        <button type="button" onClick={() => navigate('/ecourts/sci')}
          className="rounded-xl border border-primary/15 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-primary">
          ← Supreme Court
        </button>
        <h1 className="text-2xl font-black text-ink">Cause List</h1>
      </div>

      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <div className="flex flex-wrap gap-2 border-b border-primary/10 pb-4">
          {MODES.map((m) => (
            <button
              key={m.key}
              type="button"
              onClick={() => { setMode(m.key); setResults(null); setError(''); }}
              className={`rounded-xl px-4 py-2 text-sm font-semibold transition-colors ${
                mode === m.key
                  ? 'bg-primary text-white'
                  : 'border border-primary/15 text-slate-600 hover:border-primary/40 hover:text-primary'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          {mode === 'by-date' && (
            <div className="w-48">
              <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Date (DD-MM-YYYY)</label>
              <input type="text" value={date} onChange={(e) => setDate(e.target.value)}
                placeholder="e.g. 25-12-2024" className="input-base w-full" required />
            </div>
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
              <span className="material-symbols-outlined text-base">calendar_month</span>
            )}
            {loading ? 'Fetching…' : 'Fetch Cause List'}
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
              No entries found for this cause list.
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {results.map((item, i) => <CauseListRow key={i} item={item} />)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
