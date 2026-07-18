import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import { searchSCIOrdersByCase, searchSCIOrdersByDiary, downloadSCIPdf } from './apiSCI';

const TABS = [
  { key: 'case',  label: 'Case Number' },
  { key: 'diary', label: 'Diary Number' },
];

function OrderRow({ item, onDownload, downloading }) {
  return (
    <div className="rounded-[18px] border border-primary/10 bg-background-light p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="font-bold text-ink">{item.order_title || 'Order'}</p>
          <p className="mt-1 font-mono text-xs text-slate-400">{item.order_date || '—'}</p>
        </div>
        {item.doc_url && (
          <button
            type="button"
            onClick={() => onDownload(item.doc_url)}
            disabled={downloading}
            className="shrink-0 rounded-xl border border-primary/15 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:border-primary/40 hover:text-primary disabled:opacity-60"
          >
            {downloading ? '…' : 'View PDF'}
          </button>
        )}
      </div>
    </div>
  );
}

export default function SCIDailyOrdersTerminal() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [tab, setTab] = useState('case');

  const [caseNo, setCaseNo] = useState('');
  const [caseYear, setCaseYear] = useState('');
  const [caseType, setCaseType] = useState('');

  const [diaryNo, setDiaryNo] = useState('');
  const [diaryYear, setDiaryYear] = useState('');

  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [downloadingUrl, setDownloadingUrl] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setResults(null);
    setError('');
    setLoading(true);
    dispatch(beginBlocking({ message: 'Searching daily orders...' }));

    try {
      let res;
      if (tab === 'case') {
        res = await searchSCIOrdersByCase({ case_type: caseType, case_no: caseNo, case_year: caseYear });
      } else {
        res = await searchSCIOrdersByDiary({ diary_no: diaryNo, diary_year: diaryYear });
      }
      const data = res.data;
      const list = data?.orders || (Array.isArray(data) ? data : []);
      setResults(list);
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.detail || 'Search failed. Please try again.');
    } finally {
      setLoading(false);
      dispatch(stopBlocking());
    }
  }

  async function handleDownload(docUrl) {
    setDownloadingUrl(docUrl);
    try {
      const resp = await downloadSCIPdf(docUrl);
      const blob = new Blob([resp.data], { type: 'application/pdf' });
      const objUrl = URL.createObjectURL(blob);
      window.open(objUrl, '_blank');
      setTimeout(() => URL.revokeObjectURL(objUrl), 60000);
    } catch (err) {
      setError('PDF download failed. Please try again.');
    } finally {
      setDownloadingUrl(null);
    }
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-4 flex items-center gap-3">
        <button type="button" onClick={() => navigate('/ecourts/sci')}
          className="rounded-xl border border-primary/15 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-primary">
          ← Supreme Court
        </button>
        <h1 className="text-2xl font-black text-ink">Daily Orders</h1>
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
          {tab === 'case' && (
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Case Type</label>
                <input type="text" value={caseType} onChange={(e) => setCaseType(e.target.value)}
                  placeholder="e.g. SLP(C)" className="input-base w-full" required />
              </div>
              <div className="w-32">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Case No.</label>
                <input type="text" value={caseNo} onChange={(e) => setCaseNo(e.target.value)}
                  placeholder="e.g. 12345" className="input-base w-full" required />
              </div>
              <div className="w-28">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Year</label>
                <input type="text" value={caseYear} onChange={(e) => setCaseYear(e.target.value)}
                  placeholder="2024" maxLength={4} className="input-base w-full" required />
              </div>
            </div>
          )}

          {tab === 'diary' && (
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Diary No.</label>
                <input type="text" value={diaryNo} onChange={(e) => setDiaryNo(e.target.value)}
                  placeholder="e.g. 5678" className="input-base w-full" required />
              </div>
              <div className="w-28">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Year</label>
                <input type="text" value={diaryYear} onChange={(e) => setDiaryYear(e.target.value)}
                  placeholder="2024" maxLength={4} className="input-base w-full" required />
              </div>
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
                <OrderRow key={i} item={item} onDownload={handleDownload} downloading={downloadingUrl === item.doc_url} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
