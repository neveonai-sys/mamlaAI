import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import { searchSCICauseListFull, getSCIJudges } from './apiSCI';

const SESSION_KEY = 'sciCauseListSearchState';

function saveSession(state) {
  try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(state)); } catch (_) {}
}

function loadSession() {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null'); } catch (_) { return null; }
}

const SEARCH_BY_OPTIONS = [
  { value: 'all_courts', label: 'All Courts' },
  { value: 'court',      label: 'Court No' },
  { value: 'judge',      label: 'Judge Name' },
  { value: 'aor_code',   label: 'AOR' },
  { value: 'party_name', label: 'Party Name' },
];

// Confirmed live from /cause-list/'s <select id="court"> — Court No.1-17 + Registrar Court.
const COURT_NO_OPTIONS = [
  ...Array.from({ length: 17 }, (_, i) => ({ value: String(i + 1), label: `Hon'ble Court No.${i + 1}` })),
  { value: '21', label: 'Registrar Court' },
];

// Confirmed live — two different option sets depending on List Type.
const CAUSELIST_TYPE_OPTIONS = {
  daily: [
    { value: 'all', label: '--All--' },
    { value: 'Misc. Court', label: 'Miscellaneous List' },
    { value: 'Regular Court', label: 'Regular List' },
    { value: 'Single Judge Court', label: 'Single Judge List' },
    { value: 'Chamber Court', label: 'Chamber List' },
    { value: 'Review', label: 'Review/Curative' },
    { value: 'Registrar Court', label: 'Registrar' },
  ],
  other: [
    { value: 'all', label: '--All--' },
    { value: 'Misc. Advance List', label: 'Misc. Advance List' },
    { value: 'Advance Elimination List', label: 'Advance Elimination List' },
    { value: 'Final Elimination List', label: 'Final Elimination List' },
    { value: 'Weekly', label: 'Weekly' },
    { value: 'Terminal', label: 'Terminal' },
  ],
};

// DD-MM-YYYY ↔ YYYY-MM-DD helpers — the SCI portal's own forms take
// DD-MM-YYYY, but <input type="date"> (which gives users a real calendar
// picker) only speaks ISO, so we store ISO in state and convert at submit.
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

function DateField({ label, value, onChange, required }) {
  return (
    <div className="flex-1">
      <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">{label}</label>
      <input
        type="date"
        value={toIso(value)}
        onChange={(e) => onChange(toDmy(e.target.value))}
        className="input-base w-full"
        required={required}
      />
    </div>
  );
}

function CauseListRow({ item, onOpen }) {
  // Some cause-list shapes (e.g. Weekly/Terminal distribution lists) come
  // back as a single downloadable PDF per row rather than per-case data —
  // confirmed live via a "Serial Number"/"File" table. Render those as a
  // direct document link instead of a case card.
  if (item.file_url) {
    return (
      <a
        href={item.file_url}
        target="_blank"
        rel="noreferrer"
        className="flex items-center gap-3 rounded-[18px] border border-primary/10 bg-background-light p-4 transition-colors hover:border-primary/40"
      >
        <span className="material-symbols-outlined text-2xl text-primary">picture_as_pdf</span>
        <div className="min-w-0 flex-1">
          <p className="truncate font-bold text-ink">{item.file || item.label || 'Cause List Document'}</p>
          {item.serial_number && <p className="mt-0.5 text-xs text-slate-500">Serial No. {item.serial_number}</p>}
        </div>
        <span className="shrink-0 text-xs font-semibold text-primary">Open PDF ↗</span>
      </a>
    );
  }

  return (
    <div className="rounded-[18px] border border-primary/10 bg-background-light p-4">
      <p className="font-bold text-ink">{item.petitioner || item.case_title || 'Case'}</p>
      {item.respondent && <p className="mt-0.5 text-xs text-slate-500">vs {item.respondent}</p>}
      <p className="mt-1 font-mono text-xs text-slate-400">
        {item.diary_no ? `Diary ${item.diary_no}/${item.diary_year}` : ''}
        {item.case_no ? ` · ${item.case_no}${item.case_year ? `/${item.case_year}` : ''}` : ''}
      </p>
      {item.advocate && <p className="mt-1 text-[11px] text-slate-500">Advocate: {item.advocate}</p>}
      {item.court_no && <p className="mt-1 text-[11px] text-slate-500">Court No. {item.court_no}</p>}
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

export default function SCICauseListTerminal() {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const saved = loadSession();
  const [results, setResults] = useState(saved?.results ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [listType, setListType] = useState(saved?.listType || 'daily');
  const [searchBy, setSearchBy] = useState(saved?.searchBy || 'all_courts');
  const [searchCourt, setSearchCourt] = useState(saved?.searchCourt || '');
  const [searchJudge, setSearchJudge] = useState(saved?.searchJudge || '');
  const [searchAorCode, setSearchAorCode] = useState(saved?.searchAorCode || '');
  const [searchPartyName, setSearchPartyName] = useState(saved?.searchPartyName || '');
  const [causelistType, setCauselistType] = useState(saved?.causelistType || 'all');
  const [listingDate, setListingDate] = useState(saved?.listingDate || '');
  const [listingDateFrom, setListingDateFrom] = useState(saved?.listingDateFrom || '');
  const [listingDateTo, setListingDateTo] = useState(saved?.listingDateTo || '');
  const [msb, setMsb] = useState(saved?.msb || 'main');
  const [judges, setJudges] = useState([]);
  const [loadingJudges, setLoadingJudges] = useState(false);

  const isWeekly = listType === 'other' && causelistType === 'Weekly';
  const isReview = listType === 'daily' && causelistType === 'Review';

  useEffect(() => {
    if (judges.length || loadingJudges) return;
    setLoadingJudges(true);
    getSCIJudges()
      .then((res) => setJudges(res.data?.judges || res.data || []))
      .catch(() => setJudges([]))
      .finally(() => setLoadingJudges(false));
  }, []);

  useEffect(() => {
    saveSession({
      listType, searchBy, searchCourt, searchJudge, searchAorCode, searchPartyName,
      causelistType, listingDate, listingDateFrom, listingDateTo, msb, results,
    });
  }, [listType, searchBy, searchCourt, searchJudge, searchAorCode, searchPartyName,
      causelistType, listingDate, listingDateFrom, listingDateTo, msb, results]);

  function handleListTypeChange(value) {
    setListType(value);
    setCauselistType('all');
    setSearchBy('all_courts');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setResults(null);
    setError('');
    setLoading(true);
    dispatch(beginBlocking({ message: 'Fetching Supreme Court cause list...' }));

    try {
      const res = await searchSCICauseListFull({
        list_type: listType,
        search_by: searchBy,
        court: searchBy === 'court' ? searchCourt : undefined,
        judge: searchBy === 'judge' ? searchJudge : undefined,
        aor_code: searchBy === 'aor_code' ? searchAorCode : undefined,
        party_name: searchBy === 'party_name' ? searchPartyName : undefined,
        causelist_type: causelistType,
        listing_date: isWeekly ? undefined : listingDate,
        listing_date_from: isWeekly ? listingDateFrom : undefined,
        listing_date_to: isWeekly ? listingDateTo : undefined,
        msb: isReview ? 'main' : msb,
      });

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
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">List Type</label>
            <div className="flex gap-4">
              {['daily', 'other'].map((v) => (
                <label key={v} className="flex items-center gap-2 text-sm text-ink">
                  <input type="radio" name="listType" value={v} checked={listType === v} onChange={() => handleListTypeChange(v)} />
                  {v === 'daily' ? 'Daily Cause List' : 'Other Lists'}
                </label>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="flex-1">
              <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Search By</label>
              <select value={searchBy} onChange={(e) => setSearchBy(e.target.value)} className="input-base w-full">
                {SEARCH_BY_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            {searchBy === 'court' && (
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Court No.</label>
                <select value={searchCourt} onChange={(e) => setSearchCourt(e.target.value)} className="input-base w-full" required>
                  <option value="">--Select--</option>
                  {COURT_NO_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </div>
            )}

            {searchBy === 'judge' && (
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Judge</label>
                <select value={searchJudge} onChange={(e) => setSearchJudge(e.target.value)} className="input-base w-full" disabled={loadingJudges} required>
                  <option value="">{loadingJudges ? 'Loading…' : 'Select Judge'}</option>
                  {judges.map((j) => (
                    <option key={j.value} value={j.value}>{j.label}</option>
                  ))}
                </select>
              </div>
            )}

            {searchBy === 'aor_code' && (
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">AOR Code</label>
                <input type="text" value={searchAorCode} onChange={(e) => setSearchAorCode(e.target.value)}
                  placeholder="e.g. A-1234" className="input-base w-full" required />
              </div>
            )}

            {searchBy === 'party_name' && (
              <div className="flex-1">
                <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Party Name</label>
                <input type="text" value={searchPartyName} onChange={(e) => setSearchPartyName(e.target.value)}
                  placeholder="Min. 3 characters" className="input-base w-full" required />
              </div>
            )}

            <div className="flex-1">
              <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Causelist Type</label>
              <select value={causelistType} onChange={(e) => setCauselistType(e.target.value)} className="input-base w-full">
                {CAUSELIST_TYPE_OPTIONS[listType === 'daily' ? 'daily' : 'other'].map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-col gap-4 sm:flex-row">
            {isWeekly ? (
              <>
                <DateField label="Listing Date From" value={listingDateFrom} onChange={setListingDateFrom} required />
                <DateField label="Listing Date To" value={listingDateTo} onChange={setListingDateTo} required />
              </>
            ) : (
              <div className="w-48">
                <DateField label="Listing Date" value={listingDate} onChange={setListingDate} required />
              </div>
            )}

            <div>
              <label className="mb-1 block text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">Main / Supplementary / Both</label>
              <div className="flex gap-4 pt-2">
                {[['main', 'Main'], ['suppli', 'Supplementary'], ['both', 'Both']].map(([v, label]) => (
                  <label key={v} className={`flex items-center gap-2 text-sm text-ink ${isReview && v !== 'main' ? 'opacity-40' : ''}`}>
                    <input type="radio" name="msb" value={v} checked={msb === v} disabled={isReview && v !== 'main'}
                      onChange={() => setMsb(v)} />
                    {label}
                  </label>
                ))}
              </div>
            </div>
          </div>

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
              {results.map((item, i) => (
                <CauseListRow
                  key={i}
                  item={item}
                  onOpen={(id) => navigate(`/ecourts/sci/case/${encodeURIComponent(id)}`)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
