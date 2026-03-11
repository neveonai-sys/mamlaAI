import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getCauseList,
  getCauseListDates,
  getComplexes,
  getCourts,
  getDistricts,
  getStates,
} from './common/ecourtsApi';

const SEARCH_MODES = [
  { key: 'q', label: 'All' },
  { key: 'advocate', label: 'Lawyer' },
  { key: 'litigant', label: 'Litigant' },
  { key: 'judge', label: 'Judge' },
];

function SelectorField({ label, value, options, onChange, disabled, placeholder, getOptionValue, getOptionLabel }) {
  return (
    <div>
      <label className="block text-xs font-semibold mb-1 text-slate-700">{label}</label>
      <select
        value={value}
        onChange={onChange}
        disabled={disabled}
        className="input-base"
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={getOptionValue(option)} value={getOptionValue(option)}>
            {getOptionLabel(option)}
          </option>
        ))}
      </select>
    </div>
  );
}

function formatDate(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('en-IN', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function buildCaseNumber(entry) {
  if (Array.isArray(entry.case_number) && entry.case_number.length > 0) {
    return entry.case_number.join(', ');
  }
  if (typeof entry.case_number === 'string' && entry.case_number.trim()) {
    return entry.case_number;
  }
  return 'Case number unavailable';
}

export default function CauseListBrowser() {
  const navigate = useNavigate();
  const today = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const [form, setForm] = useState({
    date: today,
    query: '',
    searchMode: 'q',
    listType: '',
  });
  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [complexes, setComplexes] = useState([]);
  const [courts, setCourts] = useState([]);
  const [selectedState, setSelectedState] = useState('');
  const [selectedDistrict, setSelectedDistrict] = useState('');
  const [selectedComplex, setSelectedComplex] = useState('');
  const [selectedCourt, setSelectedCourt] = useState('');
  const [availableDates, setAvailableDates] = useState([]);
  const [result, setResult] = useState(null);
  const [structureLoading, setStructureLoading] = useState(false);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    let active = true;

    async function loadStateOptions() {
      setStructureLoading(true);
      setError('');
      try {
        const response = await getStates();
        if (!active) return;
        setStates(response.data?.data || []);
      } catch (err) {
        if (!active) return;
        setError(err.response?.data?.error || 'Unable to load court hierarchy.');
      } finally {
        if (active) {
          setStructureLoading(false);
        }
      }
    }

    loadStateOptions();
    return () => {
      active = false;
    };
  }, []);

  const fetchAvailableDates = useCallback(async (params) => {
    try {
      const response = await getCauseListDates(params);
      setAvailableDates(response.data?.dates || []);
    } catch {
      setAvailableDates([]);
    }
  }, []);

  async function handleStateChange(e) {
    const nextState = e.target.value;
    setSelectedState(nextState);
    setSelectedDistrict('');
    setSelectedComplex('');
    setSelectedCourt('');
    setDistricts([]);
    setComplexes([]);
    setCourts([]);
    setAvailableDates([]);
    setResult(null);

    if (!nextState) return;

    setStructureLoading(true);
    setError('');
    try {
      const response = await getDistricts(nextState);
      setDistricts(response.data?.data || []);
    } catch (err) {
      setError(err.response?.data?.error || 'Unable to load districts for the selected state.');
    } finally {
      setStructureLoading(false);
    }
  }

  async function handleDistrictChange(e) {
    const nextDistrict = e.target.value;
    setSelectedDistrict(nextDistrict);
    setSelectedComplex('');
    setSelectedCourt('');
    setComplexes([]);
    setCourts([]);
    setAvailableDates([]);
    setResult(null);

    if (!nextDistrict || !selectedState) return;

    setStructureLoading(true);
    setError('');
    try {
      const response = await getComplexes(selectedState, nextDistrict);
      setComplexes(response.data?.data || []);
    } catch (err) {
      setError(err.response?.data?.error || 'Unable to load court complexes for the selected district.');
    } finally {
      setStructureLoading(false);
    }
  }

  async function handleComplexChange(e) {
    const nextComplex = e.target.value;
    setSelectedComplex(nextComplex);
    setSelectedCourt('');
    setCourts([]);
    setAvailableDates([]);
    setResult(null);

    if (!nextComplex || !selectedState || !selectedDistrict) return;

    setStructureLoading(true);
    setError('');
    try {
      const [courtsResponse] = await Promise.all([
        getCourts(selectedState, selectedDistrict, nextComplex),
        fetchAvailableDates({
          state: selectedState,
          districtCode: selectedDistrict,
          courtComplexCode: nextComplex,
        }),
      ]);
      setCourts(courtsResponse.data?.data || []);
    } catch (err) {
      setError(err.response?.data?.error || 'Unable to load courts for the selected complex.');
    } finally {
      setStructureLoading(false);
    }
  }

  async function handleCourtChange(e) {
    const nextCourt = e.target.value;
    setSelectedCourt(nextCourt);
    setResult(null);

    if (!selectedState || !selectedDistrict || !selectedComplex) return;

    await fetchAvailableDates({
      state: selectedState,
      districtCode: selectedDistrict,
      courtComplexCode: selectedComplex,
      ...(nextCourt ? { courtNo: nextCourt } : {}),
    });
  }

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSearch(e) {
    e?.preventDefault();
    setError('');
    setResultsLoading(true);
    setSearched(true);
    try {
      const params = {
        limit: 100,
        ...(form.date ? { date: form.date } : {}),
        ...(selectedState ? { state: selectedState } : {}),
        ...(selectedDistrict ? { districtCode: selectedDistrict } : {}),
        ...(selectedComplex ? { courtComplexCode: selectedComplex } : {}),
        ...(selectedCourt ? { courtNo: selectedCourt } : {}),
        ...(form.listType ? { listType: form.listType } : {}),
      };

      const trimmedQuery = form.query.trim();
      if (trimmedQuery) {
        params[form.searchMode] = trimmedQuery;
      }

      const response = await getCauseList(params);
      setResult(response.data?.data || null);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to fetch cause list. Please try again.');
      setResult(null);
    } finally {
      setResultsLoading(false);
    }
  }

  async function handleDateChip(date) {
    setForm((current) => ({ ...current, date }));
    await handleSearch();
  }

  function clearLocation() {
    setSelectedState('');
    setSelectedDistrict('');
    setSelectedComplex('');
    setSelectedCourt('');
    setDistricts([]);
    setComplexes([]);
    setCourts([]);
    setAvailableDates([]);
    setResult(null);
  }

  const items = result?.entries || [];
  const selectedStateLabel = states.find((item) => item.state_code === selectedState)?.name;
  const selectedDistrictLabel = districts.find((item) => item.district_code === selectedDistrict)?.name;
  const selectedComplexLabel = complexes.find((item) => item.complex_code === selectedComplex)?.name;
  const selectedCourtLabel = courts.find((item) => String(item.court_no) === String(selectedCourt))?.court_name;

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6">
        <h2 className="text-2xl font-black text-ink tracking-tight">Cause List Browser</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Browse daily cause lists with the live court hierarchy and current backend filters.
        </p>
        <button type="button" onClick={() => navigate('/ecourts')} className="mt-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400 transition-colors hover:text-primary">
          Back to eCourts Home
        </button>
      </div>

      <div className="card p-6 mb-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {SEARCH_MODES.map((mode) => (
              <button
                key={mode.key}
                type="button"
                onClick={() => setForm((current) => ({ ...current, searchMode: mode.key }))}
                className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition-colors ${
                  form.searchMode === mode.key
                    ? 'bg-primary text-ivory'
                    : 'border border-primary/10 text-slate-500 hover:border-primary/30 hover:text-primary'
                }`}
              >
                {mode.label}
              </button>
            ))}
          </div>

          <div>
            <label className="block text-xs font-semibold mb-1 text-slate-700">
              {form.searchMode === 'advocate'
                ? 'Advocate Name'
                : form.searchMode === 'litigant'
                  ? 'Litigant / Party Name'
                  : form.searchMode === 'judge'
                    ? 'Judge Name'
                    : 'Search Query'}
            </label>
            <input
              name="query"
              value={form.query}
              onChange={handleChange}
              className="input-base"
              placeholder={
                form.searchMode === 'advocate'
                  ? 'e.g., Ramesh Gupta'
                  : form.searchMode === 'litigant'
                    ? 'e.g., ABC Pvt. Ltd.'
                    : form.searchMode === 'judge'
                      ? 'e.g., Justice Sharma'
                      : 'Search cause list by party, bench, or general text'
              }
            />
            <p className="mt-1 text-[11px] text-slate-400">
              Leave this empty if you only want the cause list for a selected court and date.
            </p>
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <SelectorField
              label="State"
              value={selectedState}
              options={states}
              onChange={handleStateChange}
              disabled={structureLoading}
              placeholder={structureLoading ? 'Loading states…' : 'All states'}
              getOptionValue={(option) => option.state_code}
              getOptionLabel={(option) => option.name}
            />
            <SelectorField
              label="District"
              value={selectedDistrict}
              options={districts}
              onChange={handleDistrictChange}
              disabled={!selectedState || structureLoading}
              placeholder={!selectedState ? 'Select a state first' : 'All districts'}
              getOptionValue={(option) => option.district_code}
              getOptionLabel={(option) => option.name}
            />
            <SelectorField
              label="Court Complex"
              value={selectedComplex}
              options={complexes}
              onChange={handleComplexChange}
              disabled={!selectedDistrict || structureLoading}
              placeholder={!selectedDistrict ? 'Select a district first' : 'All complexes'}
              getOptionValue={(option) => option.complex_code}
              getOptionLabel={(option) => option.name}
            />
            <SelectorField
              label="Court No."
              value={selectedCourt}
              options={courts}
              onChange={handleCourtChange}
              disabled={!selectedComplex || structureLoading}
              placeholder={!selectedComplex ? 'Select a complex first' : 'All courts'}
              getOptionValue={(option) => String(option.court_no || option.court_id || '')}
              getOptionLabel={(option) => [option.court_no ? `Court ${option.court_no}` : null, option.court_name].filter(Boolean).join(' — ')}
            />
          </div>

          <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_220px]">
            <div>
              <label className="block text-xs font-semibold mb-1 text-slate-700">List Type</label>
              <select name="listType" value={form.listType} onChange={handleChange} className="input-base">
                <option value="">All list types</option>
                <option value="daily">Daily</option>
                <option value="supplementary">Supplementary</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1 text-slate-700">Date</label>
              <input
                type="date"
                name="date"
                value={form.date}
                onChange={handleChange}
                className="input-base"
              />
            </div>
          </div>

          {(selectedStateLabel || selectedDistrictLabel || selectedComplexLabel || selectedCourtLabel) ? (
            <div className="rounded-xl border border-primary/10 bg-background-light px-4 py-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">Selected Court Path</p>
                  <p className="mt-1 text-sm text-slate-600">
                    {[selectedStateLabel, selectedDistrictLabel, selectedComplexLabel, selectedCourtLabel].filter(Boolean).join(' / ')}
                  </p>
                </div>
                <button type="button" onClick={clearLocation} className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400 transition-colors hover:text-primary">
                  Clear Location
                </button>
              </div>
            </div>
          ) : null}

          {availableDates.length > 0 ? (
            <div>
              <p className="block text-xs font-semibold mb-2 text-slate-700">Available Dates</p>
              <div className="flex flex-wrap gap-2">
                {availableDates.slice(0, 12).map((date) => (
                  <button
                    key={date}
                    type="button"
                    onClick={() => handleDateChip(date)}
                    className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors ${
                      form.date === date
                        ? 'border-primary bg-primary text-ivory'
                        : 'border-primary/15 text-slate-500 hover:border-primary/40 hover:bg-primary/5 hover:text-primary'
                    }`}
                  >
                    {formatDate(date)}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {structureLoading ? (
            <div className="flex items-center gap-2 rounded-xl border border-primary/10 bg-primary/5 px-4 py-3 text-sm text-primary">
              <span className="material-symbols-outlined animate-spin text-base">progress_activity</span>
              Loading court hierarchy…
            </div>
          ) : null}

          <div className="flex flex-wrap gap-3">
            <button type="submit" disabled={resultsLoading || structureLoading} className="btn-primary flex items-center gap-2">
              {resultsLoading ? (
                <><span className="material-symbols-outlined animate-spin text-base">progress_activity</span> Loading…</>
              ) : (
                <><span className="material-symbols-outlined text-base">list_alt</span> Fetch Cause List</>
              )}
            </button>
            <button
              type="button"
              onClick={() => {
                setForm({ date: today, query: '', searchMode: 'q', listType: '' });
                clearLocation();
                setError('');
                setSearched(false);
              }}
              className="rounded-full border border-primary/10 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-primary/5 hover:text-primary"
            >
              Reset Filters
            </button>
          </div>
        </form>
      </div>

      {error ? (
        <div className="mb-6 flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          <span className="material-symbols-outlined text-base">error</span>
          {error}
        </div>
      ) : null}

      {searched && !resultsLoading ? (
        <div>
          <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h3 className="font-bold text-ink">Cause List Results</h3>
              <p className="text-xs text-slate-400 mt-1">
                {[selectedCourtLabel, selectedComplexLabel, selectedDistrictLabel, selectedStateLabel].filter(Boolean).join(' / ') || 'All selected locations'}
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Date</p>
              <p className="text-sm font-semibold text-primary">{formatDate(form.date) || form.date}</p>
            </div>
          </div>

          <p className="text-xs text-slate-400 uppercase tracking-wider mb-3">
            {items.length > 0 ? `${result?.returned_count || items.length} entr${(result?.returned_count || items.length) > 1 ? 'ies' : 'y'} found` : 'No cause list available for this selection'}
          </p>

          {items.length > 0 && (
            <div className="space-y-3">
              {items.map((item, index) => (
                <div key={item.id || `${buildCaseNumber(item)}-${index}`} className="card p-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        {item.list_type ? (
                          <span className="rounded-full bg-primary/10 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.15em] text-primary">
                            {item.list_type}
                          </span>
                        ) : null}
                        {item.status ? (
                          <span className="rounded-full bg-background-light px-2 py-1 text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">
                            {item.status}
                          </span>
                        ) : null}
                        {item.court_type ? (
                          <span className="rounded-full bg-background-light px-2 py-1 text-[10px] font-bold uppercase tracking-[0.15em] text-slate-500">
                            {item.court_type.replaceAll('_', ' ')}
                          </span>
                        ) : null}
                      </div>

                      <p className="text-sm font-black text-ink">{item.party || buildCaseNumber(item)}</p>
                      <p className="mt-1 text-xs font-semibold text-slate-500">{buildCaseNumber(item)}</p>

                      {item.advocates?.length > 0 ? (
                        <p className="mt-2 text-xs text-slate-500">
                          <span className="font-semibold text-slate-700">Advocates:</span> {item.advocates.join(', ')}
                        </p>
                      ) : null}
                      {item.judge?.length > 0 ? (
                        <p className="mt-1 text-xs text-slate-500">
                          <span className="font-semibold text-slate-700">Judges:</span> {item.judge.join(', ')}
                        </p>
                      ) : null}
                      {item.court_name ? (
                        <p className="mt-1 text-xs text-slate-500">
                          <span className="font-semibold text-slate-700">Court:</span> {item.court_name}
                        </p>
                      ) : null}
                      {(item.bench || item.court_no) ? (
                        <p className="mt-1 text-xs text-slate-500">
                          <span className="font-semibold text-slate-700">Bench:</span> {[item.bench, item.court_no ? `Court ${item.court_no}` : null].filter(Boolean).join(' • ')}
                        </p>
                      ) : null}
                    </div>

                    <div className="text-right flex-shrink-0">
                      {item.date ? <p className="text-xs font-semibold text-primary">{formatDate(item.date) || item.date}</p> : null}
                      {(item.district || item.state) ? <p className="mt-1 text-xs text-slate-400">{[item.district, item.state].filter(Boolean).join(', ')}</p> : null}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {!items.length && (
            <div className="card p-8 text-center">
              <span className="material-symbols-outlined text-slate-300 text-5xl block mb-3">event_busy</span>
              <p className="text-slate-500">No cause list entries matched this court and date selection.</p>
              <p className="text-xs text-slate-400 mt-2">Try another available date, broaden the search mode, or clear the location filter.</p>
            </div>
          )}
        </div>
      ) : null}

      {!searched && !resultsLoading ? (
        <div className="card p-8 text-center">
          <span className="material-symbols-outlined text-slate-300 text-5xl block mb-3">location_searching</span>
          <p className="text-slate-500">Select a court path or enter a query to fetch a live cause list.</p>
          <p className="text-xs text-slate-400 mt-2">The hierarchy selectors use the free court-structure API, then the cause-list search runs only when you request results.</p>
        </div>
      ) : null}

      {resultsLoading ? (
        <div className="card p-8 text-center">
          <span className="material-symbols-outlined text-primary text-4xl animate-spin">progress_activity</span>
          <p className="mt-3 text-sm text-slate-500">Fetching the latest cause list…</p>
        </div>
      ) : null}
    </div>
  );
}
