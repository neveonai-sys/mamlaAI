import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { getCauseListDates, getHighCourts, getReferenceSection, runCauseListSearch } from './api';

const SEARCH_TYPES = [
  { id: 'daily', label: 'Daily List', enabled: true },
  { id: 'advocate', label: 'Advocate Wise', enabled: false },
  { id: 'courtroom', label: 'Court No Wise', enabled: false },
];

export default function CauseListTerminal() {
  const navigate = useNavigate();
  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const [highCourts, setHighCourts] = useState([]);
  const [availableDates, setAvailableDates] = useState([]);
  const [reference, setReference] = useState(null);
  const [highCourtId, setHighCourtId] = useState('');
  const [benchCode, setBenchCode] = useState('');
  const [date, setDate] = useState(today);
  const [causelistType, setCauselistType] = useState('daily');
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [statusText, setStatusText] = useState('');

  const selectedHighCourt = useMemo(
    () => highCourts.find((item) => item.id === highCourtId) || null,
    [highCourtId, highCourts],
  );

  useEffect(() => {
    let active = true;

    async function loadMetadata() {
      try {
        const [highCourtResponse, referenceResponse] = await Promise.all([
          getHighCourts(),
          getReferenceSection('cause-list'),
        ]);
        if (!active) return;
        setHighCourts(highCourtResponse.data?.data || []);
        setReference(referenceResponse.data?.data || null);
      } catch (requestError) {
        if (!active) return;
        setError(requestError.response?.data?.error || 'Unable to load cause-list metadata.');
      }
    }

    loadMetadata();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!highCourtId || !benchCode) {
      setAvailableDates([]);
      return;
    }

    let active = true;

    async function loadDates() {
      try {
        const response = await getCauseListDates({ high_court_id: highCourtId, bench_code: benchCode });
        if (!active) return;
        setAvailableDates(response.data?.dates || []);
      } catch {
        if (!active) return;
        setAvailableDates([]);
      }
    }

    loadDates();
    return () => {
      active = false;
    };
  }, [benchCode, highCourtId]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!highCourtId || !benchCode) {
      setError('Select a high court and bench before running the cause list.');
      return;
    }

    setLoading(true);
    setError('');
    setStatusText('');

    try {
      const resolved = await runCauseListSearch({
        date,
        high_court_id: highCourtId,
        bench_code: benchCode,
        causelist_type: 'daily',
      });
      const nextEntries = resolved.data?.entries || [];
      setEntries(nextEntries);
      setStatusText(
        nextEntries.length > 0
          ? `${nextEntries.length} courtroom groups returned from the scraper cause-list flow.`
          : 'The cause-list scrape completed, but no rows were returned.',
      );
    } catch (requestError) {
      setEntries([]);
      setError(requestError.response?.data?.error || requestError.message || 'Unable to run the cause-list scrape.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-6xl">
      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="text-[11px] font-black uppercase tracking-[0.28em] text-primary">Cause List</p>
            <h1 className="mt-3 text-3xl font-black tracking-tight text-ink">High-court cause list terminal</h1>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              The live High Court scraper currently exposes the daily cause list flow. Advocate-wise and court-number-wise variants stay visible here as staged modes until their selectors are re-verified against the current eCourts page.
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate('/ecourts')}
            className="rounded-full border border-primary/15 px-4 py-2 text-xs font-black uppercase tracking-[0.18em] text-slate-500 transition-colors hover:border-primary/40 hover:text-primary"
          >
            Back to terminal
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">High Court</label>
              <select value={highCourtId} onChange={(event) => {
                setHighCourtId(event.target.value);
                setBenchCode('');
              }} className="input-base">
                <option value="">Select high court</option>
                {highCourts.map((item) => (
                  <option key={item.id} value={item.id}>{item.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Bench</label>
              <select value={benchCode} onChange={(event) => setBenchCode(event.target.value)} className="input-base" disabled={!selectedHighCourt}>
                <option value="">Select bench</option>
                {(selectedHighCourt?.benches || []).map((bench) => (
                  <option key={bench.code} value={bench.code}>{bench.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Date</label>
              <input type="date" value={date} onChange={(event) => setDate(event.target.value)} className="input-base" />
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {SEARCH_TYPES.map((option) => (
              <button
                key={option.id}
                type="button"
                onClick={() => {
                  if (option.enabled) {
                    setCauselistType(option.id);
                  }
                }}
                disabled={!option.enabled}
                className={`rounded-full border px-4 py-2 text-xs font-black uppercase tracking-[0.18em] transition-colors ${causelistType === option.id ? 'border-primary bg-primary text-white' : option.enabled ? 'border-primary/10 bg-background-light text-slate-500' : 'border-slate-200 bg-slate-100 text-slate-400'}`}
              >
                {option.label}
              </button>
            ))}
          </div>

          <p className="text-xs text-slate-500">
            Daily cause lists are live. The other stitched variants remain staged until the updated High Court selectors are validated.
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <button type="submit" className="btn-primary min-w-[180px]" disabled={loading}>
              {loading ? 'Running scraper...' : 'Load cause list'}
            </button>
            {availableDates.length > 0 ? (
              <p className="text-xs text-slate-500">Cached dates for this bench: {availableDates.slice(0, 4).join(', ')}</p>
            ) : null}
            {reference?.list_types?.length ? (
              <p className="text-xs text-slate-500">Reference list families in Mongo: {reference.list_types.map((item) => item.label).join(', ')}</p>
            ) : null}
          </div>
        </form>

        {error ? (
          <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        ) : null}
        {statusText ? (
          <div className="mt-5 rounded-2xl border border-primary/10 bg-background-light px-4 py-3 text-sm text-slate-600">{statusText}</div>
        ) : null}
      </div>

      <div className="mt-8 grid gap-4">
        {entries.map((entry, index) => (
          <div key={`${entry.court_no || 'bench'}-${index}`} className="rounded-[24px] border border-primary/10 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Court grouping</p>
                <h2 className="mt-2 text-xl font-black text-ink">{entry.court_no || 'Unlabelled bench'}</h2>
              </div>
              <span className="rounded-full border border-primary/10 bg-background-light px-3 py-1 text-[11px] font-black uppercase tracking-[0.18em] text-slate-500">
                {entry.items?.length || 0} items
              </span>
            </div>
            <div className="mt-4 space-y-3">
              {(entry.items || []).map((item, itemIndex) => (
                <div key={`${entry.court_no || 'item'}-${itemIndex}`} className="rounded-2xl border border-primary/10 bg-background-light px-4 py-4">
                  <div className="flex flex-wrap items-center gap-3 text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">
                    <span>{item.case_number || `Row ${itemIndex + 1}`}</span>
                    {item.sl_no ? <span>Sl. {item.sl_no}</span> : null}
                  </div>
                  <p className="mt-2 text-sm font-semibold text-ink">{item.parties || 'Parties unavailable'}</p>
                  <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500">
                    {item.advocate ? <span>Advocate: {item.advocate}</span> : null}
                    {item.purpose ? <span>Purpose: {item.purpose}</span> : null}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
        {entries.length === 0 ? (
          <div className="rounded-[24px] border border-dashed border-primary/15 bg-background-light px-4 py-6 text-sm text-slate-500">
            Run a cause-list scrape to populate the stitched list surface.
          </div>
        ) : null}
      </div>
    </div>
  );
}