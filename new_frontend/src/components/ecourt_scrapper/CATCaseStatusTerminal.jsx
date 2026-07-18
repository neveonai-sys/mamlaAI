import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import {
  getCATBenches,
  getCATCaseTypes,
  searchCATByNumber,
  searchCATByDiary,
  searchCATByParty,
  searchCATByAdvocate,
} from './apiCAT';

const TABS = [
  { key: 'number',   label: 'Case Number' },
  { key: 'diary',    label: 'Diary Number' },
  { key: 'party',    label: 'Party Name' },
  { key: 'advocate', label: 'Advocate Name' },
];

const SESSION_KEY = 'catCaseStatusSearchState';

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
          <p className="truncate font-bold text-ink">{item.Applicant || item.party || 'Case'}</p>
          {item.Respondent && <p className="mt-0.5 truncate text-xs text-slate-500">vs {item.Respondent}</p>}
          <p className="mt-1 font-mono text-xs text-slate-400">{item['Case No'] || ''}</p>
        </div>
        {item.Status && (
          <span className="shrink-0 rounded-full border border-primary/15 bg-white px-2 py-0.5 text-[11px] font-bold text-slate-600">
            {item.Status}
          </span>
        )}
      </div>
      {item['Next Date'] && (
        <p className="mt-2 text-[11px] text-slate-500">Next: {item['Next Date']}</p>
      )}
      <button
        type="button"
        onClick={onOpen}
        className="mt-3 rounded-xl border border-primary/15 px-3 py-1.5 text-xs font-semibold text-slate-600 transition-colors hover:border-primary/40 hover:text-primary"
      >
        View Details →
      </button>
    </div>
  );
}

export default function CATCaseStatusTerminal() {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const saved = loadSession();
  const [tab, setTab] = useState(saved?.tab || 'number');
  const [benches, setBenches] = useState([]);
  const [caseTypes, setCaseTypes] = useState([]);
  const [loadingMeta, setLoadingMeta] = useState(true);

  const [bench, setBench] = useState(saved?.bench || '');

  // Case Number tab
  const [caseType, setCaseType] = useState(saved?.caseType || '');
  const [caseNo, setCaseNo]     = useState(saved?.caseNo || '');
  const [caseYear, setCaseYear] = useState(saved?.caseYear || '');

  // Diary Number tab
  const [diaryNo, setDiaryNo]     = useState(saved?.diaryNo || '');
  const [diaryYear, setDiaryYear] = useState(saved?.diaryYear || '');

  // Party Name tab
  const [partyName, setPartyName] = useState(saved?.partyName || '');
  const [partyType, setPartyType] = useState(saved?.partyType || 'Both');

  // Advocate Name tab
  const [advocateName, setAdvocateName] = useState(saved?.advocateName || '');
  const [advocateType, setAdvocateType] = useState(saved?.advocateType || 'Petitioner');

  const [results, setResults]       = useState(saved?.results || null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');
  const [statusText, setStatusText] = useState('');

  useEffect(() => {
    let active = true;
    setLoadingMeta(true);
    Promise.all([getCATBenches(), getCATCaseTypes()])
      .then(([benchesRes, typesRes]) => {
        if (!active) return;
        setBenches(benchesRes.data || []);
        setCaseTypes(typesRes.data || []);
      })
      .catch(() => { if (active) { setBenches([]); setCaseTypes([]); } })
      .finally(() => { if (active) setLoadingMeta(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    saveSession({
      tab, bench, caseType, caseNo, caseYear, diaryNo, diaryYear,
      partyName, partyType, advocateName, advocateType, results,
    });
  }, [tab, bench, caseType, caseNo, caseYear, diaryNo, diaryYear, partyName, partyType, advocateName, advocateType, results]);

  function clearResults() {
    setResults(null);
    setError('');
    setStatusText('');
  }

  function buildDetailId() {
    return `${bench}_${caseType}_${caseNo}_${caseYear}`;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    clearResults();
    setLoading(true);
    dispatch(beginBlocking({ message: 'Searching CAT cases...' }));

    try {
      let res;
      if (tab === 'number') {
        res = await searchCATByNumber({ bench, case_type: caseType, case_no: caseNo, year: caseYear });
      } else if (tab === 'diary') {
        res = await searchCATByDiary({ bench, diary_no: diaryNo, year: diaryYear });
      } else if (tab === 'party') {
        res = await searchCATByParty({ bench, party_name: partyName, party_type: partyType });
      } else if (tab === 'advocate') {
        res = await searchCATByAdvocate({ bench, advocate_name: advocateName, advocate_type: advocateType });
      }

      const data = res.data;
      const caseList = data?.case_details ? [data.case_details] : (Array.isArray(data?.cases) ? data.cases : []);
      setResults(caseList);
      setStatusText(data?.error || `${caseList.length} result${caseList.length !== 1 ? 's' : ''}`);
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
        <h1 className="text-2xl font-black text-ink">Case Status</h1>
      </div>

      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <div className="mb-6">
          <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Bench</label>
          <select value={bench} onChange={(e) => setBench(e.target.value)} className="input-base w-full sm:w-72" disabled={loadingMeta} required>
            <option value="">{loadingMeta ? 'Loading…' : 'Select Bench'}</option>
            {benches.map((b) => (
              <option key={b.slug} value={b.slug}>{b.name}</option>
            ))}
          </select>
        </div>

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
                <select value={caseType} onChange={(e) => setCaseType(e.target.value)} className="input-base w-full" disabled={loadingMeta} required>
                  <option value="">{loadingMeta ? 'Loading…' : 'Select Case Type'}</option>
                  {caseTypes.map((ct) => (
                    <option key={ct.code} value={ct.code}>{ct.name}</option>
                  ))}
                </select>
              </div>
              <div className="w-32">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Case No.</label>
                <input type="text" value={caseNo} onChange={(e) => setCaseNo(e.target.value)}
                  placeholder="e.g. 1265" className="input-base w-full" required />
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
                  placeholder="e.g. 123456" className="input-base w-full" required />
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
              <div className="w-40">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Party Type</label>
                <select value={partyType} onChange={(e) => setPartyType(e.target.value)} className="input-base w-full">
                  <option value="Both">Both</option>
                  <option value="Petitioner">Petitioner</option>
                  <option value="Respondent">Respondent</option>
                </select>
              </div>
            </div>
          )}

          {tab === 'advocate' && (
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Advocate Name</label>
                <input type="text" value={advocateName} onChange={(e) => setAdvocateName(e.target.value)}
                  placeholder="e.g. Sharma" className="input-base w-full" required />
              </div>
              <div className="w-40">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Advocate Type</label>
                <select value={advocateType} onChange={(e) => setAdvocateType(e.target.value)} className="input-base w-full">
                  <option value="Petitioner">Petitioner</option>
                  <option value="Respondent">Respondent</option>
                </select>
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
          )}

          <button
            type="submit"
            disabled={loading || !bench}
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
                <CaseCard key={i} item={item} onOpen={() => navigate(`/ecourts/cat/case/${encodeURIComponent(buildDetailId())}`)} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
