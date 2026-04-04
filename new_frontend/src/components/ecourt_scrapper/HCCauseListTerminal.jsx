import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import HCCourtSelector from './HCCourtSelector';
import { fetchHCCauseList, downloadHCCauseListPdf } from './apiHC';

const SESSION_KEY = 'hcCauseListSearchState';

function saveSession(s) { try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(s)); } catch (_) {} }
function loadSession()  { try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null'); } catch (_) { return null; } }

// Returns today as DD-MM-YYYY
function todayDMY() {
  const d = new Date();
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const yyyy = d.getFullYear();
  return `${dd}-${mm}-${yyyy}`;
}

// Returns today as YYYY-MM-DD (for <input type="date">)
function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

// Converts YYYY-MM-DD to DD-MM-YYYY
function toDmy(iso) {
  if (!iso || !iso.includes('-')) return iso;
  const [y, m, d] = iso.split('-');
  return `${d}-${m}-${y}`;
}

function CauseListCard({ item }) {
  const [downloading, setDownloading] = React.useState(false);
  const [dlError, setDlError] = React.useState('');

  async function handlePdf() {
    setDlError('');
    setDownloading(true);
    try {
      const resp = await downloadHCCauseListPdf(item.pdf_url);
      const blob = new Blob([resp.data], { type: 'application/pdf' });
      const objUrl = URL.createObjectURL(blob);
      window.open(objUrl, '_blank');
      setTimeout(() => URL.revokeObjectURL(objUrl), 60000);
    } catch (err) {
      let msg = 'PDF download failed.';
      if (err.response?.data instanceof Blob) {
        try { const t = await err.response.data.text(); msg = JSON.parse(t).detail || JSON.parse(t).error || msg; } catch { /* ignore */ }
      } else {
        msg = err.response?.data?.detail || err.response?.data?.error || msg;
      }
      setDlError(msg);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="rounded-[18px] border border-primary/10 bg-white p-4 flex items-center justify-between gap-4">
      <div className="min-w-0">
        <span className="mr-3 inline-block rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-bold text-primary">
          #{item.serial}
        </span>
        <span className="font-semibold text-ink">{item.bench}</span>
        {item.list_type && (
          <span className="ml-2 text-xs text-slate-400">({item.list_type})</span>
        )}
        {dlError && <p className="mt-1 text-xs text-red-600">{dlError}</p>}
      </div>
      {item.pdf_url && (
        <button
          type="button"
          onClick={handlePdf}
          disabled={downloading}
          className="shrink-0 rounded-xl border border-primary/15 px-4 py-2 text-sm font-semibold text-primary hover:bg-primary/5 disabled:opacity-50"
        >
          {downloading ? '…' : 'View PDF'}
        </button>
      )}
    </div>
  );
}

export default function HCCauseListTerminal() {
  const navigate = useNavigate();
  const saved = loadSession();

  const [location, setLocation] = useState(saved?.location || { hc: '', bench: '', isComplete: false });
  const [dateIso, setDateIso]   = useState(saved?.dateIso || todayISO());

  const [results, setResults]     = useState(saved?.results || null);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');
  const [statusText, setStatusText] = useState('');

  useEffect(() => {
    saveSession({ location, dateIso, results });
  }, [location, dateIso, results]);

  async function handleSubmit(e) {
    e.preventDefault();
    setResults(null);
    setError('');
    setStatusText('');
    if (!location.isComplete) { setError('Select a High Court and Bench first.'); return; }
    setLoading(true);

    try {
      const res = await fetchHCCauseList({
        hc: location.hc,
        bench: location.bench,
        list_date: toDmy(dateIso),
      });
      const data = res.data;
      const items = data?.items || [];
      setResults(items);
      setStatusText(
        `${data?.total_items ?? items.length} item${(data?.total_items ?? items.length) !== 1 ? 's' : ''} — ${data?.high_court || location.hc}, ${data?.bench || location.bench} — ${data?.date || toDmy(dateIso)}`
      );
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.detail || 'Failed to fetch cause list. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-4xl">
      <div className="mb-4 flex items-center gap-3">
        <button type="button" onClick={() => navigate('/ecourts/hc')}
          className="rounded-xl border border-primary/15 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-primary">
          ← High Court
        </button>
        <h1 className="text-2xl font-black text-ink">Cause List</h1>
      </div>

      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <HCCourtSelector onChange={setLocation} initialValues={saved?.location} />

          <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
            <div>
              <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Date</label>
              <input
                type="date"
                value={dateIso}
                onChange={(e) => setDateIso(e.target.value)}
                className="input-base"
              />
              <p className="mt-1 text-xs text-slate-400">Defaults to today ({todayDMY()}) if left as-is.</p>
            </div>

            <button type="submit" disabled={loading}
              className="btn-primary flex items-center justify-center gap-2 sm:self-end px-8 py-3">
              {loading
                ? <span className="material-symbols-outlined animate-spin text-base">progress_activity</span>
                : <span className="material-symbols-outlined text-base">list_alt</span>}
              {loading ? 'Loading…' : 'Get Cause List'}
            </button>
          </div>

          {error && (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
          )}
        </form>
      </div>

      {/* Results */}
      {results !== null && (
        <div className="mt-6">
          <p className="mb-3 text-sm font-semibold text-slate-500">{statusText}</p>
          {results.length === 0 ? (
            <div className="rounded-[24px] border border-primary/10 bg-white p-6 text-center text-slate-500">
              No cause list entries for this date.
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {results.map((item, idx) => (
                <CauseListCard key={idx} item={item} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
