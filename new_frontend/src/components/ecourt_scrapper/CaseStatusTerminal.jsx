import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';

import LocationCascade from './LocationCascade';
import {
  cnrSearch,
  casestatusByParty,
  casestatusByFiling,
  casestatusByAdvocate,
  casestatusByFir,
  getPoliceStations,
} from './apiV2';

const MODES = [
  { id: 'cnr', label: 'CNR Lookup' },
  { id: 'party', label: 'Party Name' },
  { id: 'filing', label: 'Filing Number' },
  { id: 'advocate', label: 'Advocate' },
  { id: 'fir', label: 'FIR' },
];

export default function CaseStatusTerminal() {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const SESSION_KEY = 'caseStatusSearchState';

  // Read saved session once (lazy init) for LocationCascade's initialValues —
  // only on back_forward navigation to avoid stale cascade on hard refresh.
  const [locationInitialValues] = useState(() => {
    try {
      const navType = performance.getEntriesByType?.('navigation')?.[0]?.type;
      if (navType !== 'back_forward') return null;
      const s = sessionStorage.getItem(SESSION_KEY);
      return s ? JSON.parse(s).location || null : null;
    } catch { return null; }
  });

  const [activeMode, setActiveMode] = useState('party');
  const [location, setLocation] = useState({});

  // CNR
  const [cnr, setCnr] = useState('');

  // Party
  const [partyName, setPartyName] = useState('');
  const [registrationYear, setRegistrationYear] = useState('');
  const [caseStatus, setCaseStatus] = useState('Pending');

  // Filing
  const [filingNumber, setFilingNumber] = useState('');
  const [filingYear, setFilingYear] = useState('');

  // Advocate
  const [advocateSearchBy, setAdvocateSearchBy] = useState('name');
  const [advocateName, setAdvocateName] = useState('');
  const [advocateCode, setAdvocateCode] = useState('');
  const [advocateYear, setAdvocateYear] = useState('');
  const [caselistDate, setCaselistDate] = useState('');
  const [advCaseStatus, setAdvCaseStatus] = useState('Pending');

  // FIR
  const [policeStations, setPoliceStations] = useState([]);
  const [policeStationCode, setPoliceStationCode] = useState('');
  const [firNumber, setFirNumber] = useState('');
  const [firYear, setFirYear] = useState('');
  const [firCaseStatus, setFirCaseStatus] = useState('Both');
  const [loadingPS, setLoadingPS] = useState(false);

  // Results
  const [results, setResults] = useState([]);
  const [totalCases, setTotalCases] = useState(0);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [statusText, setStatusText] = useState('');

  // Load police stations when location is complete and FIR mode is active
  useEffect(() => {
    setPoliceStations([]);
    setPoliceStationCode('');
    if (activeMode !== 'fir' || !location.isComplete) return;

    let active = true;
    setLoadingPS(true);
    getPoliceStations(location.state_code, location.dist_code, location.court_complex_code, location.est_code)
      .then((res) => {
        if (!active) return;
        setPoliceStations(res.data || []);
      })
      .catch(() => {
        if (!active) return;
        setPoliceStations([]);
      })
      .finally(() => {
        if (active) setLoadingPS(false);
      });
    return () => { active = false; };
  }, [activeMode, location.isComplete, location.state_code, location.dist_code, location.court_complex_code, location.est_code]);

  // Restore form state + results from sessionStorage ONLY on browser Back navigation.
  // Hard refresh, direct URL open, and fresh navigation all start blank.
  useEffect(() => {
    try {
      const navType = performance.getEntriesByType?.('navigation')?.[0]?.type;
      if (navType !== 'back_forward') return;
      const saved = sessionStorage.getItem(SESSION_KEY);
      if (!saved) return;
      const s = JSON.parse(saved);
      if (s.activeMode) setActiveMode(s.activeMode);
      if (s.location) setLocation(s.location);
      if (s.cnr) setCnr(s.cnr);
      if (s.partyName) setPartyName(s.partyName);
      if (s.registrationYear) setRegistrationYear(s.registrationYear);
      if (s.caseStatus) setCaseStatus(s.caseStatus);
      if (s.filingNumber) setFilingNumber(s.filingNumber);
      if (s.filingYear) setFilingYear(s.filingYear);
      if (s.advocateSearchBy) setAdvocateSearchBy(s.advocateSearchBy);
      if (s.advocateName) setAdvocateName(s.advocateName);
      if (s.advocateCode) setAdvocateCode(s.advocateCode);
      if (s.advocateYear) setAdvocateYear(s.advocateYear);
      if (s.caselistDate) setCaselistDate(s.caselistDate);
      if (s.advCaseStatus) setAdvCaseStatus(s.advCaseStatus);
      if (s.policeStationCode) setPoliceStationCode(s.policeStationCode);
      if (s.firNumber) setFirNumber(s.firNumber);
      if (s.firYear) setFirYear(s.firYear);
      if (s.firCaseStatus) setFirCaseStatus(s.firCaseStatus);
      if (s.results?.length) setResults(s.results);
      if (s.totalCases) setTotalCases(s.totalCases);
      if (s.searched) setSearched(s.searched);
      if (s.statusText) setStatusText(s.statusText);
    } catch { /* ignore corrupt data */ }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setStatusText('');
    setSearched(true);
    setResults([]);
    sessionStorage.removeItem(SESSION_KEY); // clear stale state before new search

    // --- CNR mode: navigate directly ---
    if (activeMode === 'cnr') {
      const normalized = cnr.trim().toUpperCase();
      if (!normalized) {
        setError('Enter a CNR number.');
        return;
      }
      setLoading(true);
      dispatch(beginBlocking({ message: 'Looking up CNR on eCourts...' }));
      try {
        const res = await cnrSearch(normalized);
        const data = res.data;
        if (data?.case_details || data?.cnr_number) {
          navigate(`/ecourts/case/${encodeURIComponent(normalized)}`);
          return;
        }
        setResults(data?.case_list || (data ? [data] : []));
        setStatusText('CNR lookup completed.');
      } catch (err) {
        setError(err.response?.data?.error || err.message || 'CNR lookup failed.');
      } finally {
        setLoading(false);
        dispatch(stopBlocking());
      }
      return;
    }

    // --- All other modes require location ---
    if (!location.isComplete) {
      setError('Select state, district, complex, and establishment first.');
      return;
    }

    const base = {
      state_code: location.state_code,
      dist_code: location.dist_code,
      court_complex_code: location.court_complex_code,
      est_code: location.est_code,
    };

    setLoading(true);
    dispatch(beginBlocking({ message: 'Searching cases on eCourts...' }));

    try {
      let res;

      if (activeMode === 'party') {
        if (!partyName.trim()) { setError('Enter a party name.'); setLoading(false); dispatch(stopBlocking()); return; }
        res = await casestatusByParty({
          ...base,
          party_name: partyName.trim(),
          registration_year: registrationYear.trim(),
          case_status: caseStatus,
        });
      } else if (activeMode === 'filing') {
        if (!filingNumber.trim() || !filingYear.trim()) {
          setError('Enter both filing number and filing year.');
          setLoading(false); dispatch(stopBlocking());
          return;
        }
        res = await casestatusByFiling({
          ...base,
          filing_number: filingNumber.trim(),
          filing_year: filingYear.trim(),
        });
      } else if (activeMode === 'advocate') {
        if (advocateSearchBy === 'name' && !advocateName.trim()) {
          setError('Enter advocate name.');
          setLoading(false); dispatch(stopBlocking());
          return;
        }
        if (advocateSearchBy !== 'name' && !advocateCode.trim()) {
          setError('Enter advocate code.');
          setLoading(false); dispatch(stopBlocking());
          return;
        }
        res = await casestatusByAdvocate({
          ...base,
          search_by: advocateSearchBy,
          advocate_name: advocateName.trim(),
          advocate_code: advocateCode.trim(),
          advocate_year: advocateYear.trim(),
          caselist_date: caselistDate,
          case_status: advCaseStatus,
        });
      } else if (activeMode === 'fir') {
        if (!policeStationCode) {
          setError('Select a police station.');
          setLoading(false); dispatch(stopBlocking());
          return;
        }
        res = await casestatusByFir({
          ...base,
          police_station_code: policeStationCode,
          fir_number: firNumber.trim(),
          fir_year: firYear.trim(),
          case_status: firCaseStatus,
        });
      }

      const caseList = res?.data?.cases || res?.data?.case_list || [];
      const total = res?.data?.total_cases || caseList.length || 0;
      const finalResults = caseList.length > 0 ? caseList : (res?.data && !Array.isArray(res.data) ? [res.data] : []);
      const finalStatus = caseList.length > 0
        ? `${total} case(s) found.`
        : 'Search completed — no matching cases found.';

      // Persist for Back navigation
      try {
        sessionStorage.setItem(SESSION_KEY, JSON.stringify({
          activeMode, location,
          cnr, partyName, registrationYear, caseStatus,
          filingNumber, filingYear,
          advocateSearchBy, advocateName, advocateCode, advocateYear, caselistDate, advCaseStatus,
          policeStationCode, firNumber, firYear, firCaseStatus,
          results: finalResults, totalCases: total, searched: true, statusText: finalStatus,
        }));
      } catch { /* ignore */ }

      setResults(finalResults);
      setTotalCases(total);
      setStatusText(finalStatus);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Case status search failed.');
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
            <p className="text-[11px] font-black uppercase tracking-[0.28em] text-primary">Case Status</p>
            <h1 className="mt-3 text-3xl font-black tracking-tight text-ink">Case status search</h1>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              Search for cases by party name, filing number, advocate, or FIR — backed by the live eCourts scraper.
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

        {/* Mode tabs */}
        <div className="mt-6 flex flex-wrap gap-2">
          {MODES.map((mode) => (
            <button
              key={mode.id}
              type="button"
              onClick={() => setActiveMode(mode.id)}
              className={`rounded-full border px-4 py-2 text-xs font-black uppercase tracking-[0.18em] transition-colors ${
                activeMode === mode.id
                  ? 'border-primary bg-primary text-white'
                  : 'border-emerald-200 bg-emerald-50 text-emerald-700'
              }`}
            >
              {mode.label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          {/* Location cascade — shown for all modes except CNR */}
          {activeMode !== 'cnr' && (
            <LocationCascade onChange={setLocation} error={error} initialValues={locationInitialValues} />
          )}

          {/* CNR mode */}
          {activeMode === 'cnr' && (
            <div>
              <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">CNR Number</label>
              <input
                type="text"
                value={cnr}
                onChange={(e) => setCnr(e.target.value.toUpperCase())}
                placeholder="e.g. DLST010012342024"
                className="input-base font-mono uppercase"
              />
            </div>
          )}

          {/* Party mode fields */}
          {activeMode === 'party' && (
            <div className="grid gap-4 md:grid-cols-[minmax(0,2fr),160px,180px]">
              <div>
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Party Name</label>
                <input type="text" value={partyName} onChange={(e) => setPartyName(e.target.value)} placeholder="Petitioner or respondent name" className="input-base" />
              </div>
              <div>
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Reg. Year</label>
                <input type="text" value={registrationYear} onChange={(e) => setRegistrationYear(e.target.value.replace(/\D/g, '').slice(0, 4))} placeholder="2024" className="input-base font-mono" />
              </div>
              <div>
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Case Status</label>
                <select value={caseStatus} onChange={(e) => setCaseStatus(e.target.value)} className="input-base">
                  <option value="Pending">Pending</option>
                  <option value="Disposed">Disposed</option>
                  <option value="Both">Both</option>
                </select>
              </div>
            </div>
          )}

          {/* Filing mode fields */}
          {activeMode === 'filing' && (
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Filing Number</label>
                <input type="text" value={filingNumber} onChange={(e) => setFilingNumber(e.target.value)} placeholder="e.g. 12345" className="input-base font-mono" />
              </div>
              <div>
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Filing Year</label>
                <input type="text" value={filingYear} onChange={(e) => setFilingYear(e.target.value.replace(/\D/g, '').slice(0, 4))} placeholder="2024" className="input-base font-mono" />
              </div>
            </div>
          )}

          {/* Advocate mode fields */}
          {activeMode === 'advocate' && (
            <div className="space-y-4">
              <div className="flex gap-1 rounded-2xl bg-background-light p-1 w-fit">
                {[
                  { key: 'name', label: 'By Name' },
                  { key: 'code', label: 'By Code' },
                  { key: 'date_caselist', label: 'By Date' },
                ].map((opt) => (
                  <button
                    key={opt.key}
                    type="button"
                    onClick={() => setAdvocateSearchBy(opt.key)}
                    className={`rounded-xl px-4 py-2 text-xs font-black uppercase tracking-[0.16em] transition-colors ${
                      advocateSearchBy === opt.key ? 'bg-white text-primary shadow-sm' : 'text-slate-500'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                {advocateSearchBy === 'name' ? (
                  <div>
                    <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Advocate Name</label>
                    <input type="text" value={advocateName} onChange={(e) => setAdvocateName(e.target.value)} placeholder="Enter advocate name" className="input-base" />
                  </div>
                ) : (
                  <div>
                    <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Advocate Code</label>
                    <input type="text" value={advocateCode} onChange={(e) => setAdvocateCode(e.target.value)} placeholder="e.g. D/1234/2020" className="input-base font-mono" />
                  </div>
                )}
                {advocateSearchBy === 'date_caselist' && (
                  <div>
                    <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Case List Date</label>
                    <input type="date" value={caselistDate} onChange={(e) => setCaselistDate(e.target.value)} className="input-base" />
                  </div>
                )}
                <div>
                  <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Case Status</label>
                  <select value={advCaseStatus} onChange={(e) => setAdvCaseStatus(e.target.value)} className="input-base">
                    <option value="Pending">Pending</option>
                    <option value="Disposed">Disposed</option>
                    <option value="Both">Both</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* FIR mode fields */}
          {activeMode === 'fir' && (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">
                    Police Station {loadingPS && <span className="text-primary">loading…</span>}
                  </label>
                  <select
                    value={policeStationCode}
                    onChange={(e) => setPoliceStationCode(e.target.value)}
                    className="input-base"
                    disabled={!location.isComplete || loadingPS}
                  >
                    <option value="">Select police station</option>
                    {policeStations.map((ps) => (
                      <option key={ps.value || ps.code} value={ps.value || ps.code}>
                        {ps.label || ps.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">FIR Number</label>
                  <input type="text" value={firNumber} onChange={(e) => setFirNumber(e.target.value)} placeholder="e.g. 123" className="input-base font-mono" />
                </div>
                <div>
                  <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">FIR Year</label>
                  <input type="text" value={firYear} onChange={(e) => setFirYear(e.target.value.replace(/\D/g, '').slice(0, 4))} placeholder="2024" className="input-base font-mono" />
                </div>
              </div>
              <div className="w-48">
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Case Status</label>
                <select value={firCaseStatus} onChange={(e) => setFirCaseStatus(e.target.value)} className="input-base">
                  <option value="Both">Both</option>
                  <option value="Pending">Pending</option>
                  <option value="Disposed">Disposed</option>
                </select>
              </div>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <button type="submit" className="btn-primary min-w-[180px]" disabled={loading}>
              {loading ? 'Searching…' : activeMode === 'cnr' ? 'Lookup CNR' : 'Search cases'}
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

      {searched && results.length > 0 ? (
        <div className="mt-6 font-serif">
          {/* Total cases summary bar */}
          <div
            className="rounded-t-sm border-2 border-b-0 border-black py-2.5 px-4 text-center text-white font-semibold text-sm"
            style={{ backgroundColor: '#1f3753' }}
          >
            Total Cases Found: {totalCases || results.length}
          </div>

          {/* Registry table */}
          <div className="overflow-x-auto border-2 border-black shadow-sm">
            <table className="w-full border-collapse" style={{ backgroundColor: '#f6f5ee' }}>
              <thead>
                <tr>
                  {['Sr No', 'Case Type / Number / Year', 'Petitioner vs Respondent', 'View'].map((h) => (
                    <th
                      key={h}
                      className="border border-black px-4 py-3 text-sm text-white font-bold text-center"
                      style={{ backgroundColor: '#1f3753' }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.map((item, index) => {
                  const cino = item.cino || item.cnr_number || item.cnr || '';
                  const caseTypeLine = item['Case Type/Case Number/Case Year'] || item.case_number || '—';
                  const partyRaw = item['Petitioner Name versus Respondent Name'] || '';
                  // Split on "Vs" (eCourts packs without spaces around Vs)
                  const vsIdx = partyRaw.search(/\s*Vs/i);
                  const petitioner = vsIdx >= 0 ? partyRaw.slice(0, vsIdx).trim() : partyRaw.trim();
                  const respondent = vsIdx >= 0 ? partyRaw.slice(vsIdx).replace(/^\s*Vs\s*/i, '').trim() : '';

                  return (
                    <tr
                      key={`${cino || 'row'}-${index}`}
                      className="border-b border-black/20"
                      style={{ backgroundColor: index % 2 === 0 ? '#f6f5ee' : '#eeeade' }}
                    >
                      <td
                        className="border border-black px-3 py-3 text-center text-sm font-semibold"
                        style={{ color: '#19314c', width: '5%' }}
                      >
                        {item['Sr No'] || index + 1}
                      </td>
                      <td
                        className="border border-black px-4 py-3 text-sm"
                        style={{ color: '#19314c' }}
                      >
                        {caseTypeLine}
                      </td>
                      <td
                        className="border border-black px-4 py-3 text-sm"
                        style={{ color: '#19314c' }}
                      >
                        <span className="font-medium">{petitioner || '—'}</span>
                        {respondent ? (
                          <>
                            <br />
                            <span className="text-xs text-slate-500">vs</span>
                            <br />
                            <span>{respondent}</span>
                          </>
                        ) : null}
                      </td>
                      <td className="border border-black px-3 py-3 text-center" style={{ width: '10%' }}>
                        {cino ? (
                          <Link
                            to={`/ecourts/case/${encodeURIComponent(cino)}`}
                            className="text-sm underline hover:no-underline font-medium"
                            style={{ color: '#19314c' }}
                          >
                            View
                          </Link>
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : searched && !loading ? (
        <div className="mt-6 rounded-sm border-2 border-black bg-white px-4 py-6 text-center text-sm text-slate-500 font-sans">
          No results for this search.
        </div>
      ) : null}
    </div>
  );
}