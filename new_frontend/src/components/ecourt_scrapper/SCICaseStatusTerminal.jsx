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
} from './apiSCI';

const TABS = [
  { key: 'number', label: 'Case Number' },
  { key: 'diary',  label: 'Diary Number' },
  { key: 'party',  label: 'Party Name' },
  { key: 'aor',    label: 'AOR Code' },
];

const SESSION_KEY = 'sciCaseStatusSearchState';

function saveSession(state) {
  try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(state)); } catch (_) {}
}

function loadSession() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null'); } catch (_) { return null; }
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

  // AOR Code tab
  const [aorCode, setAorCode] = useState(saved?.aorCode || '');
  const [aorYear, setAorYear] = useState(saved?.aorYear || '');

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
    saveSession({ tab, caseType, caseNo, caseYear, diaryNo, diaryYear, partyName, partyYear, aorCode, aorYear, results });
  }, [tab, caseType, caseNo, caseYear, diaryNo, diaryYear, partyName, partyYear, aorCode, aorYear, results]);

  function clearResults() {
    setResults(null);
    setError('');
    setStatusText('');
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
        res = await searchSCIByParty({ party_name: partyName, year: partyYear });
      } else if (tab === 'aor') {
        res = await searchSCIByAor({ aor_code: aorCode, year: aorYear });
      }

      const data = res.data;
      const caseList = data?.cases || (Array.isArray(data) ? data : data ? [data] : []);
      setResults(caseList);
      setStatusText(`${caseList.length} result${caseList.length !== 1 ? 's' : ''}`);
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
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Year (optional)</label>
                <input type="text" value={partyYear} onChange={(e) => setPartyYear(e.target.value)}
                  placeholder="2024" maxLength={4} className="input-base w-full" />
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
