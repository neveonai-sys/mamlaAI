import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import {
  getCATBenches,
  getCATCaseTypes,
  getCATJudges,
  getCATOrdersDailyByCase,
  getCATOrdersDailyByDiary,
  getCATOrdersDailyByParty,
  getCATOrdersDailyByDate,
  getCATOrdersDailyByJudge,
  getCATOrdersFinalByCase,
  getCATOrdersFinalByDiary,
  getCATOrdersFinalByDate,
  getCATOrdersFinalByJudge,
} from './apiCAT';

const LIST_TYPES = [
  { key: 'daily', label: 'Daily Orders' },
  { key: 'final', label: 'Final / Oral Orders' },
];

// Final Orders has no "by party" mode on the real portal.
const SEARCH_BY = {
  daily: [
    { key: 'case',  label: 'Case No.' },
    { key: 'diary', label: 'Diary No.' },
    { key: 'party', label: 'Party Name' },
    { key: 'date',  label: 'Date Range' },
    { key: 'judge', label: 'Judge' },
  ],
  final: [
    { key: 'case',  label: 'Case No.' },
    { key: 'diary', label: 'Diary No.' },
    { key: 'date',  label: 'Date Range' },
    { key: 'judge', label: 'Judge' },
  ],
};

// DD-MM-YYYY <-> YYYY-MM-DD, so date fields get a real calendar picker.
function toIso(dmy) {
  if (!dmy || !dmy.includes('-')) return dmy || '';
  const [d, m, y] = dmy.split('-');
  return `${y}-${m}-${d}`;
}
function toDmy(iso) {
  if (!iso || !iso.includes('-')) return iso || '';
  const [y, m, d] = iso.split('-');
  return `${d}-${m}-${y}`;
}
function DateField({ label, value, onChange }) {
  return (
    <div className="flex-1">
      <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">{label}</label>
      <input type="date" value={toIso(value)} onChange={(e) => onChange(toDmy(e.target.value))} className="input-base w-full" required />
    </div>
  );
}

function OrderRow({ item }) {
  const dateVal = item['Order Date'] || item.col_3 || '—';
  const caseNo = item['Case No.'] || item.col_1 || '';
  const party = item['Party Details'] || item.col_2 || '';
  return (
    <div className="rounded-[18px] border border-primary/10 bg-background-light p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="font-mono text-xs text-slate-400">{dateVal}</p>
          <p className="mt-1 truncate text-sm font-bold text-ink">{caseNo}</p>
          {party && <p className="mt-0.5 truncate text-xs text-slate-500">{party}</p>}
        </div>
        {item.pdf_url && (
          <a
            href={item.pdf_url}
            target="_blank"
            rel="noreferrer"
            className="shrink-0 rounded-xl border border-primary/15 px-3 py-1.5 text-xs font-semibold text-slate-600 hover:border-primary/40 hover:text-primary"
          >
            View PDF
          </a>
        )}
      </div>
    </div>
  );
}

export default function CATOrdersTerminal() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [listType, setListType] = useState('daily');
  const [searchBy, setSearchBy] = useState('case');

  const [benches, setBenches] = useState([]);
  const [caseTypes, setCaseTypes] = useState([]);
  const [judges, setJudges] = useState([]);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [loadingJudges, setLoadingJudges] = useState(false);

  const [bench, setBench] = useState('');

  const [caseType, setCaseType] = useState('');
  const [caseNo, setCaseNo] = useState('');
  const [caseYear, setCaseYear] = useState('');

  const [diaryNo, setDiaryNo] = useState('');
  const [diaryYear, setDiaryYear] = useState('');

  const [partyName, setPartyName] = useState('');
  const [partyType, setPartyType] = useState('Both');

  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  const [judgeCode, setJudgeCode] = useState('');

  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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
    if (searchBy !== 'judge' || judges.length || loadingJudges) return;
    setLoadingJudges(true);
    getCATJudges()
      .then((res) => setJudges(res.data || []))
      .catch(() => setJudges([]))
      .finally(() => setLoadingJudges(false));
  }, [searchBy]);

  function handleListTypeChange(value) {
    setListType(value);
    setSearchBy('case');
    setResults(null);
    setError('');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setResults(null);
    setError('');
    setLoading(true);
    dispatch(beginBlocking({ message: 'Fetching orders...' }));

    const byCase = listType === 'daily' ? getCATOrdersDailyByCase : getCATOrdersFinalByCase;
    const byDiary = listType === 'daily' ? getCATOrdersDailyByDiary : getCATOrdersFinalByDiary;
    const byDate = listType === 'daily' ? getCATOrdersDailyByDate : getCATOrdersFinalByDate;
    const byJudge = listType === 'daily' ? getCATOrdersDailyByJudge : getCATOrdersFinalByJudge;

    try {
      let res;
      if (searchBy === 'case') {
        res = await byCase({ bench, case_type: caseType, case_no: caseNo, year: caseYear });
      } else if (searchBy === 'diary') {
        res = await byDiary({ bench, diary_no: diaryNo, year: diaryYear });
      } else if (searchBy === 'party') {
        // Only reachable for Daily Orders — Final Orders has no party-name mode on the real portal.
        res = await getCATOrdersDailyByParty({ bench, party_name: partyName, party_type: partyType });
      } else if (searchBy === 'date') {
        res = await byDate({ bench, from_date: fromDate, to_date: toDate });
      } else {
        res = await byJudge({ bench, judge_code: judgeCode });
      }
      setResults(res.data?.orders || []);
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
        <h1 className="text-2xl font-black text-ink">Orders</h1>
      </div>

      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <div className="flex flex-wrap gap-2 border-b border-primary/10 pb-4">
          {LIST_TYPES.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => handleListTypeChange(t.key)}
              className={`rounded-xl px-4 py-2 text-sm font-semibold transition-colors ${
                listType === t.key
                  ? 'bg-primary text-white'
                  : 'border border-primary/15 text-slate-600 hover:border-primary/40 hover:text-primary'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="flex-1">
              <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Bench</label>
              <select value={bench} onChange={(e) => setBench(e.target.value)} className="input-base w-full" disabled={loadingMeta} required>
                <option value="">{loadingMeta ? 'Loading…' : 'Select Bench'}</option>
                {benches.map((b) => (
                  <option key={b.slug} value={b.slug}>{b.name}</option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Search By</label>
              <select value={searchBy} onChange={(e) => { setSearchBy(e.target.value); setResults(null); setError(''); }} className="input-base w-full">
                {SEARCH_BY[listType].map((s) => (
                  <option key={s.key} value={s.key}>{s.label}</option>
                ))}
              </select>
            </div>
          </div>

          {searchBy === 'case' && (
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

          {searchBy === 'diary' && (
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

          {searchBy === 'party' && (
            <div className="flex flex-col gap-4 sm:flex-row">
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Party Name</label>
                <input type="text" value={partyName} onChange={(e) => setPartyName(e.target.value)}
                  placeholder="e.g. Sharma" className="input-base w-full" required />
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

          {searchBy === 'date' && (
            <div className="flex flex-col gap-4 sm:flex-row">
              <DateField label="From Date" value={fromDate} onChange={setFromDate} />
              <DateField label="To Date" value={toDate} onChange={setToDate} />
            </div>
          )}

          {searchBy === 'judge' && (
            <div className="flex-1">
              <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Judge / Member</label>
              <select value={judgeCode} onChange={(e) => setJudgeCode(e.target.value)} className="input-base w-full" disabled={loadingJudges} required>
                <option value="">{loadingJudges ? 'Loading…' : 'Select Judge'}</option>
                {judges.map((j) => (
                  <option key={j.code} value={j.code}>{j.name}</option>
                ))}
              </select>
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
                <OrderRow key={i} item={item} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
