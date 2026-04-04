import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';

import LocationCascade from './LocationCascade';
import { getCourts, causelistFetch } from './apiV2';

export default function CauseListTerminal() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);

  const SESSION_KEY = 'causeListSearchState';

  const [locationInitialValues] = useState(() => {
    try {
      const navType = performance.getEntriesByType?.('navigation')?.[0]?.type;
      if (navType !== 'back_forward') return null;
      const s = sessionStorage.getItem(SESSION_KEY);
      return s ? JSON.parse(s).location || null : null;
    } catch { return null; }
  });

  // Ref holding the court value to restore once the courts dropdown loads
  const savedCourtRef = useRef(null);

  const [location, setLocation] = useState({});

  // Courts dropdown
  const [courts, setCourts] = useState([]);
  const [selectedCourt, setSelectedCourt] = useState(''); // "court_no||court_name"
  const [loadingCourts, setLoadingCourts] = useState(false);

  // Params
  const [date, setDate] = useState(today);
  const [listType, setListType] = useState('civil');

  // Results
  const [entries, setEntries] = useState([]);
  const [totalCases, setTotalCases] = useState(0);
  const [heading, setHeading] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [statusText, setStatusText] = useState('');

  // Restore form + results from sessionStorage ONLY on browser Back navigation.
  // Hard refresh, direct URL open, and fresh navigation all start blank.
  useEffect(() => {
    try {
      const navType = performance.getEntriesByType?.('navigation')?.[0]?.type;
      if (navType !== 'back_forward') return;
      const saved = sessionStorage.getItem(SESSION_KEY);
      if (!saved) return;
      const s = JSON.parse(saved);
      if (s.location) setLocation(s.location);
      if (s.date) setDate(s.date);
      if (s.listType) setListType(s.listType);
      if (s.selectedCourt) savedCourtRef.current = s.selectedCourt;
      if (s.entries?.length) setEntries(s.entries);
      if (s.totalCases) setTotalCases(s.totalCases);
      if (s.heading) setHeading(s.heading);
      if (s.statusText) setStatusText(s.statusText);
    } catch { /* ignore */ }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Load courts when location is complete; restore saved court selection once loaded
  useEffect(() => {
    setCourts([]);
    setSelectedCourt('');
    if (!location.isComplete) return;

    let active = true;
    setLoadingCourts(true);
    getCourts(location.state_code, location.dist_code, location.court_complex_code, location.est_code)
      .then((res) => {
        if (!active) return;
        setCourts(res.data || []);
        if (savedCourtRef.current) {
          setSelectedCourt(savedCourtRef.current);
          savedCourtRef.current = null;
        }
      })
      .catch(() => {
        if (!active) return;
        setCourts([]);
      })
      .finally(() => {
        if (active) setLoadingCourts(false);
      });
    return () => { active = false; };
  }, [location.isComplete, location.state_code, location.dist_code, location.court_complex_code, location.est_code]);

  function parseCourtSelection() {
    if (!selectedCourt) return { court_no: '', court_name: '' };
    const [courtNo, ...rest] = selectedCourt.split('||');
    return { court_no: courtNo, court_name: rest.join('||') };
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setStatusText('');
    setEntries([]);
    setTotalCases(0);
    setHeading('');
    sessionStorage.removeItem(SESSION_KEY); // clear stale state before new search

    if (!location.isComplete) {
      setError('Select state, district, complex, and establishment first.');
      return;
    }

    const { court_no, court_name } = parseCourtSelection();
    if (!court_no) {
      setError('Select a court.');
      return;
    }

    setLoading(true);
    dispatch(beginBlocking({ message: 'Fetching cause list from eCourts...' }));

    try {
      const res = await causelistFetch({
        state_code: location.state_code,
        dist_code: location.dist_code,
        court_complex_code: location.court_complex_code,
        est_code: location.est_code,
        court_no,
        court_name,
        date,
        list_type: listType,
      });

      const data = res.data;
      const caseList = data?.cases || data?.case_list || data?.entries || [];
      const total = data?.total_cases ?? caseList.length;
      const finalHeading = data?.heading || '';
      const finalStatus = caseList.length > 0
        ? `${total} cause list entries returned.`
        : data?.message || 'Cause list fetch completed — no entries found.';

      // Persist for Back navigation
      try {
        sessionStorage.setItem(SESSION_KEY, JSON.stringify({
          location, date, listType, selectedCourt,
          entries: caseList, totalCases: total,
          heading: finalHeading, statusText: finalStatus,
        }));
      } catch { /* ignore */ }

      setEntries(caseList);
      setTotalCases(total);
      setHeading(finalHeading);
      setStatusText(finalStatus);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Cause list fetch failed.');
    } finally {
      setLoading(false);
      dispatch(stopBlocking());
    }
  }

  return (
    <div className="p-8 max-w-6xl">
      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="text-[11px] font-black uppercase tracking-[0.28em] text-primary">Cause List</p>
            <h1 className="mt-3 text-3xl font-black tracking-tight text-ink">Cause list terminal</h1>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              Fetch the daily cause list for any district court. Select the location cascade, pick a court, date, and list type.
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
          <LocationCascade onChange={setLocation} error={error} initialValues={locationInitialValues} />

          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">
                Court {loadingCourts && <span className="text-primary">loading…</span>}
              </label>
              <select
                value={selectedCourt}
                onChange={(e) => setSelectedCourt(e.target.value)}
                className="input-base"
                disabled={!location.isComplete || loadingCourts}
              >
                <option value="">Select court</option>
                {courts.map((c, i) => {
                  const no = c.court_no || c.value || c.code || '';
                  const name = c.court_name || c.label || c.name || `Court ${no}`;
                  return (
                    <option key={`${no}-${i}`} value={`${no}||${name}`}>
                      {name}
                    </option>
                  );
                })}
              </select>
            </div>
            <div>
              <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Date</label>
              <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="input-base" />
            </div>
            <div>
              <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">List Type</label>
              <div className="flex gap-1 rounded-2xl bg-background-light p-1 w-fit">
                {['civil', 'criminal'].map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setListType(t)}
                    className={`rounded-xl px-4 py-2 text-xs font-black uppercase tracking-[0.16em] transition-colors ${
                      listType === t ? 'bg-white text-primary shadow-sm' : 'text-slate-500'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button type="submit" className="btn-primary min-w-[180px]" disabled={loading}>
              {loading ? 'Fetching…' : 'Load cause list'}
            </button>
          </div>
        </form>

        {error && (
          <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
        )}
        {statusText && (
          <div className="mt-5 rounded-2xl border border-primary/10 bg-background-light px-4 py-3 text-sm text-slate-600">{statusText}</div>
        )}
      </div>

      <div className="mt-8 grid gap-4">
        {entries.length > 0 ? (
          <div style={{ fontFamily: 'Georgia, serif' }}>
            {/* Summary bar */}
            <div
              className="flex items-center justify-between px-4 py-2 text-white text-sm font-bold"
              style={{ backgroundColor: '#1f3753' }}
            >
              <span>{heading || 'Cause List'}</span>
              <span>Total Entries: {totalCases}</span>
            </div>

            {/* Registry table */}
            <table className="w-full border-collapse text-sm" style={{ backgroundColor: '#f6f5ee' }}>
              <thead>
                <tr style={{ backgroundColor: '#1f3753', color: '#fff' }}>
                  <th className="border border-black px-3 py-2 text-center font-bold text-xs w-12">Sr No</th>
                  <th className="border border-black px-3 py-2 text-center font-bold text-xs w-36">Section</th>
                  <th className="border border-black px-3 py-2 text-center font-bold text-xs">Case</th>
                  <th className="border border-black px-3 py-2 text-center font-bold text-xs">Party Name</th>
                  <th className="border border-black px-3 py-2 text-center font-bold text-xs">Advocate</th>
                  <th className="border border-black px-3 py-2 text-center font-bold text-xs w-16">View</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((item, idx) => {
                  const caseLabel = (item['Cases'] || item.case_number || '').replace(/^\s*View\s+/i, '');
                  const partyRaw = item['Party Name'] || item.parties || '';
                  const [petitioner, respondent] = partyRaw.split(/\s*versus\s*/i);
                  const advocate = item['Advocate Name'] || item.advocate || '';
                  const cino = item.cino || '';
                  const rowBg = idx % 2 === 0 ? '#f6f5ee' : '#eeeade';
                  return (
                    <tr key={idx} style={{ backgroundColor: rowBg }}>
                      <td className="border border-black px-3 py-2 text-center text-xs">{item['Sr No'] || idx + 1}</td>
                      <td className="border border-black px-3 py-2 text-xs text-center" style={{ color: '#19314c' }}>
                        {item.section || '—'}
                      </td>
                      <td className="border border-black px-3 py-2 text-xs font-semibold" style={{ color: '#19314c' }}>
                        {caseLabel || '—'}
                      </td>
                      <td className="border border-black px-3 py-2 text-xs">
                        {petitioner && <div className="font-semibold">{petitioner.trim()}</div>}
                        {respondent && <div className="text-slate-500 text-[11px]">vs. {respondent.trim()}</div>}
                        {!partyRaw && '—'}
                      </td>
                      <td className="border border-black px-3 py-2 text-xs">{advocate || '—'}</td>
                      <td className="border border-black px-3 py-2 text-center text-xs">
                        {cino ? (
                          <Link
                            to={`/ecourts/case/${encodeURIComponent(cino)}`}
                            className="underline font-semibold"
                            style={{ color: '#1f3753' }}
                          >
                            View
                          </Link>
                        ) : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-[24px] border border-dashed border-primary/15 bg-background-light px-4 py-6 text-sm text-slate-500">
            Run a cause list fetch to see entries here.
          </div>
        )}
      </div>
    </div>
  );
}