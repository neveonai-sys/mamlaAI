import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import {
  getSCICaseTypes,
  searchSCIByNumber,
  searchSCIByDiary,
  searchSCIByParty,
  searchSCIByAor,
  searchSCIByCnr,
  getSCICaseStatusCourtStates,
  getSCICaseStatusCourtBenches,
  getSCICaseStatusCourtCaseTypes,
  searchSCIByCourt,
} from './apiSCI';

const TABS = [
  { key: 'number', label: 'Case Number' },
  { key: 'diary',  label: 'Diary Number' },
  { key: 'party',  label: 'Party Name' },
  { key: 'aor',    label: 'AOR Code' },
  { key: 'cnr',    label: 'CNR Number' },
  { key: 'court',  label: 'Court' },
];

// Static — confirmed live from /case-status-court/'s <select id="case_status_court">.
const COURT_OPTIONS = [
  { value: '4', label: 'Supreme Court' },
  { value: '1', label: 'High Court' },
  { value: '3', label: 'District Court' },
  { value: '5', label: 'State Agency' },
];

const SESSION_KEY = 'sciCaseStatusSearchState';

function saveSession(state) {
  try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(state)); } catch (_) {}
}

function loadSession() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null'); } catch (_) { return null; }
}

// error.response.data.detail/.error is usually a string, but a FastAPI
// validation failure (422) makes "detail" an array of {type, loc, msg,
// input} objects instead — rendering that directly as {error} crashes the
// whole tree ("Objects are not valid as a React child"), confirmed live.
function extractErrorMessage(err) {
  const raw = err.response?.data?.error || err.response?.data?.detail;
  if (typeof raw === 'string') return raw;
  if (Array.isArray(raw)) {
    const msgs = raw.map((d) => (typeof d === 'string' ? d : d?.msg)).filter(Boolean);
    if (msgs.length) return msgs.join('; ');
  }
  return 'Search failed. Please try again.';
}

function CaseCard({ item, onOpen }) {
  return (
    <div className="rounded-[18px] border border-primary/10 bg-background-light p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="truncate font-bold text-ink">{item.petitioner || item.party || 'Case'}</p>
          {item.respondent && <p className="mt-0.5 truncate text-xs text-slate-500">vs {item.respondent}</p>}
          <p className="mt-1 font-mono text-xs text-slate-400">
            {item.diary_no ? `Diary ${item.diary_no}/${item.diary_year}` : ''}
            {item.case_no ? ` · ${item.case_no}/${item.case_year}` : ''}
          </p>
        </div>
        {item.status && (
          <span className="shrink-0 rounded-full border border-primary/15 bg-white px-2 py-0.5 text-[11px] font-bold text-slate-600">
            {item.status}
          </span>
        )}
      </div>
      {item.next_hearing && (
        <p className="mt-2 text-[11px] text-slate-500">Next: {item.next_hearing}</p>
      )}
      {item.diary_no && (
        <button
          type="button"
          onClick={() => onOpen(`${item.diary_no}_${item.diary_year}`)}
          className="mt-3 rounded-xl border border-primary/15 px-3 py-1.5 text-xs font-semibold text-slate-600 transition-colors hover:border-primary/40 hover:text-primary"
        >
          View Details →
        </button>
      )}
    </div>
  );
}

export default function SCICaseStatusTerminal() {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const saved = loadSession();
  const [tab, setTab] = useState(saved?.tab || 'number');
  const [caseTypes, setCaseTypes] = useState([]);
  const [loadingTypes, setLoadingTypes] = useState(true);

  // Case Number tab
  const [caseType, setCaseType] = useState(saved?.caseType || '');
  const [caseNo, setCaseNo]     = useState(saved?.caseNo || '');
  const [caseYear, setCaseYear] = useState(saved?.caseYear || '');

  // Diary Number tab
  const [diaryNo, setDiaryNo]     = useState(saved?.diaryNo || '');
  const [diaryYear, setDiaryYear] = useState(saved?.diaryYear || '');

  // Party Name tab
  const [partyName, setPartyName] = useState(saved?.partyName || '');
  const [partyYear, setPartyYear] = useState(saved?.partyYear || '');
  const [partyType, setPartyType] = useState(saved?.partyType || 'any');
  const [partyStatus, setPartyStatus] = useState(saved?.partyStatus || '');

  // AOR Code tab
  const [aorCode, setAorCode] = useState(saved?.aorCode || '');
  const [aorYear, setAorYear] = useState(saved?.aorYear || '');

  // CNR Number tab
  const [cnrNo, setCnrNo] = useState(saved?.cnrNo || '');

  // Court tab (cascading Court → State → Bench → Case Type)
  const [courtCourt, setCourtCourt]       = useState(saved?.courtCourt || '');
  const [courtState, setCourtState]       = useState(saved?.courtState || '');
  const [courtBench, setCourtBench]       = useState(saved?.courtBench || '');
  const [courtCaseType, setCourtCaseType] = useState(saved?.courtCaseType || '');
  const [courtCaseNo, setCourtCaseNo]     = useState(saved?.courtCaseNo || '');
  const [courtYear, setCourtYear]         = useState(saved?.courtYear || '');
  const [courtListingDate, setCourtListingDate] = useState(saved?.courtListingDate || '');
  const [courtStates, setCourtStates]         = useState([]);
  const [courtBenches, setCourtBenches]       = useState([]);
  const [courtCaseTypes, setCourtCaseTypes]   = useState([]);
  const [loadingCourtStates, setLoadingCourtStates]     = useState(false);
  const [loadingCourtBenches, setLoadingCourtBenches]   = useState(false);
  const [loadingCourtCaseTypes, setLoadingCourtCaseTypes] = useState(false);

  const [results, setResults]       = useState(saved?.results || null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');
  const [statusText, setStatusText] = useState('');

  useEffect(() => {
    let active = true;
    setLoadingTypes(true);
    getSCICaseTypes()
      .then((res) => { if (active) setCaseTypes(res.data?.case_types || res.data || []); })
      .catch(() => { if (active) setCaseTypes([]); })
      .finally(() => { if (active) setLoadingTypes(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    saveSession({
      tab, caseType, caseNo, caseYear, diaryNo, diaryYear, partyName, partyYear, partyType, partyStatus,
      aorCode, aorYear, cnrNo, courtCourt, courtState, courtBench, courtCaseType, courtCaseNo, courtYear,
      courtListingDate, results,
    });
  }, [tab, caseType, caseNo, caseYear, diaryNo, diaryYear, partyName, partyYear, partyType, partyStatus,
      aorCode, aorYear, cnrNo, courtCourt, courtState, courtBench, courtCaseType, courtCaseNo, courtYear,
      courtListingDate, results]);

  function clearResults() {
    setResults(null);
    setError('');
    setStatusText('');
  }

  function handleCourtChange(court) {
    setCourtCourt(court);
    setCourtState(''); setCourtBench(''); setCourtCaseType('');
    setCourtStates([]); setCourtBenches([]); setCourtCaseTypes([]);
    if (!court) return;
    setLoadingCourtStates(true);
    getSCICaseStatusCourtStates(court)
      .then((res) => setCourtStates(res.data?.states || []))
      .catch(() => setCourtStates([]))
      .finally(() => setLoadingCourtStates(false));
  }

  function handleCourtStateChange(state) {
    setCourtState(state);
    setCourtBench(''); setCourtCaseType('');
    setCourtBenches([]); setCourtCaseTypes([]);
    if (!state) return;
    setLoadingCourtBenches(true);
    getSCICaseStatusCourtBenches(courtCourt, state)
      .then((res) => setCourtBenches(res.data?.benches || []))
      .catch(() => setCourtBenches([]))
      .finally(() => setLoadingCourtBenches(false));
  }

  function handleCourtBenchChange(bench) {
    setCourtBench(bench);
    setCourtCaseType('');
    setCourtCaseTypes([]);
    if (!bench) return;
    setLoadingCourtCaseTypes(true);
    getSCICaseStatusCourtCaseTypes(courtCourt, courtState, bench)
      .then((res) => setCourtCaseTypes(res.data?.case_types || []))
      .catch(() => setCourtCaseTypes([]))
      .finally(() => setLoadingCourtCaseTypes(false));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    clearResults();
    setLoading(true);
    dispatch(beginBlocking({ message: 'Searching Supreme Court cases...' }));

    try {
      let res;
      if (tab === 'number') {
        res = await searchSCIByNumber({ case_type: caseType, case_no: caseNo, case_year: caseYear });
      } else if (tab === 'diary') {
        res = await searchSCIByDiary({ diary_no: diaryNo, diary_year: diaryYear });
      } else if (tab === 'party') {
        res = await searchSCIByParty({ party_name: partyName, year: partyYear, party_type: partyType, party_status: partyStatus });
      } else if (tab === 'aor') {
        res = await searchSCIByAor({ aor_code: aorCode, year: aorYear });
      } else if (tab === 'cnr') {
        res = await searchSCIByCnr({ cnr_no: cnrNo });
      } else if (tab === 'court') {
        res = await searchSCIByCourt({
          court: courtCourt, state: courtState, bench: courtBench, case_type: courtCaseType,
          case_no: courtCaseNo, year: courtYear, listing_date: courtListingDate,
        });
      }

      const data = res.data;
      const caseList = data?.cases || (Array.isArray(data) ? data : data ? [data] : []);
      setResults(caseList);
      setStatusText(`${caseList.length} result${caseList.length !== 1 ? 's' : ''}`);
    } catch (err) {
      setError(extractErrorMessage(err));
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
        <h1 className="text-2xl font-black text-ink">Case Status</h1>
      </div>

      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <div className="flex flex-wrap gap-2 border-b border-primary/10 pb-4">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => { setTab(t.key); clearResults(); }}
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
          {tab === 'number' && (
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Case Type</label>
                <select value={caseType} onChange={(e) => setCaseType(e.target.value)} className="input-base w-full" disabled={loadingTypes} required>
                  <option value="">{loadingTypes ? 'Loading…' : 'Select Case Type'}</option>
                  {caseTypes.map((ct) => (
                    <option key={ct.code || ct.value} value={ct.code || ct.value}>{ct.label || ct.name}</option>
                  ))}
                </select>
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

          {tab === 'party' && (
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Party Name</label>
                <input type="text" value={partyName} onChange={(e) => setPartyName(e.target.value)}
                  placeholder="Min. 3 characters" className="input-base w-full" required />
              </div>
              <div className="w-28">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Year</label>
                <input type="text" value={partyYear} onChange={(e) => setPartyYear(e.target.value)}
                  placeholder="2024" maxLength={4} className="input-base w-full" required />
              </div>
              <div className="w-40">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Party Type</label>
                <select value={partyType} onChange={(e) => setPartyType(e.target.value)} className="input-base w-full" required>
                  <option value="any">Any</option>
                  <option value="P">Petitioner</option>
                  <option value="R">Respondent</option>
                </select>
              </div>
              <div className="w-40">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Case Status</label>
                <select value={partyStatus} onChange={(e) => setPartyStatus(e.target.value)} className="input-base w-full" required>
                  <option value="">--Select--</option>
                  <option value="P">Pending</option>
                  <option value="D">Disposed</option>
                </select>
              </div>
            </div>
          )}

          {tab === 'aor' && (
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">AOR Code</label>
                <input type="text" value={aorCode} onChange={(e) => setAorCode(e.target.value)}
                  placeholder="e.g. A-1234" className="input-base w-full" required />
              </div>
              <div className="w-28">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Year (optional)</label>
                <input type="text" value={aorYear} onChange={(e) => setAorYear(e.target.value)}
                  placeholder="2024" maxLength={4} className="input-base w-full" />
              </div>
            </div>
          )}

          {tab === 'cnr' && (
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">CNR Number</label>
                <input type="text" value={cnrNo} onChange={(e) => setCnrNo(e.target.value)}
                  placeholder="e.g. DLHC010012345678" className="input-base w-full" required />
              </div>
            </div>
          )}

          {tab === 'court' && (
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-4 sm:flex-row">
                <div className="flex-1">
                  <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Court</label>
                  <select value={courtCourt} onChange={(e) => handleCourtChange(e.target.value)} className="input-base w-full" required>
                    <option value="">--Select--</option>
                    {COURT_OPTIONS.map((c) => (
                      <option key={c.value} value={c.value}>{c.label}</option>
                    ))}
                  </select>
                </div>
                <div className="flex-1">
                  <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">State</label>
                  <select value={courtState} onChange={(e) => handleCourtStateChange(e.target.value)} className="input-base w-full"
                    disabled={!courtCourt || loadingCourtStates} required>
                    <option value="">{loadingCourtStates ? 'Loading…' : '--Select--'}</option>
                    {courtStates.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>
                <div className="flex-1">
                  <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Bench</label>
                  <select value={courtBench} onChange={(e) => handleCourtBenchChange(e.target.value)} className="input-base w-full"
                    disabled={!courtState || loadingCourtBenches} required>
                    <option value="">{loadingCourtBenches ? 'Loading…' : '--Select--'}</option>
                    {courtBenches.map((b) => (
                      <option key={b.value} value={b.value}>{b.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex flex-col gap-4 sm:flex-row">
                <div className="flex-1">
                  <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Case Type</label>
                  <select value={courtCaseType} onChange={(e) => setCourtCaseType(e.target.value)} className="input-base w-full"
                    disabled={!courtBench || loadingCourtCaseTypes} required>
                    <option value="">{loadingCourtCaseTypes ? 'Loading…' : '--Select--'}</option>
                    {courtCaseTypes.map((ct) => (
                      <option key={ct.value} value={ct.value}>{ct.label}</option>
                    ))}
                  </select>
                </div>
                <div className="w-32">
                  <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Case No.</label>
                  <input type="text" value={courtCaseNo} onChange={(e) => setCourtCaseNo(e.target.value)}
                    placeholder="e.g. 1234" className="input-base w-full" required />
                </div>
                <div className="w-28">
                  <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Year</label>
                  <input type="text" value={courtYear} onChange={(e) => setCourtYear(e.target.value)}
                    placeholder="2026" maxLength={4} className="input-base w-full" required />
                </div>
                <div className="w-36">
                  <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Order Date (optional)</label>
                  <input type="text" value={courtListingDate} onChange={(e) => setCourtListingDate(e.target.value)}
                    placeholder="dd-mm-yyyy" className="input-base w-full" />
                </div>
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
          <p className="mb-3 text-sm font-semibold text-slate-500">{statusText}</p>
          {results.length === 0 ? (
            <div className="rounded-[24px] border border-primary/10 bg-white p-6 text-center text-slate-500">
              No cases found matching your search.
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              {results.map((item, i) => (
                <CaseCard key={item.diary_no || item.case_no || i} item={item} onOpen={(id) => navigate(`/ecourts/sci/case/${encodeURIComponent(id)}`)} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
