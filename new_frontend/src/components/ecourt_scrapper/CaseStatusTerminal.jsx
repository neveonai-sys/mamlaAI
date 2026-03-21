import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import ResultCard from '../ecourts/common/ResultCard';
import {
  getComplexes,
  getDistrictStates,
  getDistricts,
  getHighCourts,
  getReferenceSection,
  runCaseSearch,
} from './api';

const UNIVERSAL_LIVE_MODE_KEYS = new Set(['cnr', 'advocate']);
const HIGH_COURT_ONLY_MODE_KEYS = new Set(['party-name']);

function isModeLive(modeId, courtType) {
  if (UNIVERSAL_LIVE_MODE_KEYS.has(modeId)) {
    return true;
  }
  if (courtType === 'high_court' && HIGH_COURT_ONLY_MODE_KEYS.has(modeId)) {
    return true;
  }
  return false;
}

function modeTone(isLive) {
  return isLive
    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
    : 'border-slate-200 bg-slate-100 text-slate-500';
}

function getCaseDetailPath(item) {
  const cnr = item?.cnr || item?.cnr_number || '';
  if (!cnr) return '/ecourts/case/';
  return `/ecourts/case/${encodeURIComponent(cnr)}`;
}

export default function CaseStatusTerminal() {
  const navigate = useNavigate();
  const [reference, setReference] = useState(null);
  const [highCourts, setHighCourts] = useState([]);
  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [complexes, setComplexes] = useState([]);
  const [courtType, setCourtType] = useState('high_court');
  const [activeMode, setActiveMode] = useState('advocate');
  const [benchCode, setBenchCode] = useState('');
  const [highCourtId, setHighCourtId] = useState('');
  const [stateId, setStateId] = useState('');
  const [districtId, setDistrictId] = useState('');
  const [complexId, setComplexId] = useState('');
  const [query, setQuery] = useState('');
  const [cnr, setCnr] = useState('');
  const [registrationYear, setRegistrationYear] = useState('');
  const [caseStatus, setCaseStatus] = useState('both');
  const [results, setResults] = useState([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [statusText, setStatusText] = useState('');

  const selectedHighCourt = useMemo(
    () => highCourts.find((item) => item.id === highCourtId) || null,
    [highCourtId, highCourts],
  );
  const selectedState = useMemo(
    () => states.find((item) => item.id === stateId) || null,
    [stateId, states],
  );
  const selectedDistrict = useMemo(
    () => districts.find((item) => item.id === districtId) || null,
    [districtId, districts],
  );

  const availableModes = useMemo(() => {
    const tabs = reference?.tabs || [];
    return [
      { id: 'cnr', label: 'CNR', enabled: true },
      ...tabs.map((tab) => ({
        id: tab.id,
        label: tab.label,
        enabled: isModeLive(tab.id, courtType),
      })),
    ];
  }, [courtType, reference]);

  const benchOptions = selectedHighCourt?.benches || [];
  const isLiveMode = isModeLive(activeMode, courtType);

  useEffect(() => {
    let active = true;

    async function loadReference() {
      try {
        const [referenceResponse, highCourtResponse, stateResponse] = await Promise.all([
          getReferenceSection('case-status'),
          getHighCourts(),
          getDistrictStates(),
        ]);

        if (!active) return;
        setReference(referenceResponse.data?.data || null);
        setHighCourts(highCourtResponse.data?.data || []);
        setStates(stateResponse.data?.data || []);
      } catch (requestError) {
        if (!active) return;
        setError(requestError.response?.data?.error || 'Unable to load case-status metadata.');
      }
    }

    loadReference();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedState) {
      setDistricts([]);
      setDistrictId('');
      return;
    }

    let active = true;

    async function loadDistricts() {
      try {
        const response = await getDistricts(selectedState.name);
        if (!active) return;
        setDistricts(response.data?.data || []);
      } catch (requestError) {
        if (!active) return;
        setError(requestError.response?.data?.error || 'Unable to load districts.');
      }
    }

    setDistrictId('');
    setComplexId('');
    setComplexes([]);
    loadDistricts();
    return () => {
      active = false;
    };
  }, [selectedState]);

  useEffect(() => {
    if (!selectedState || !selectedDistrict) {
      setComplexes([]);
      setComplexId('');
      return;
    }

    let active = true;

    async function loadComplexes() {
      try {
        const response = await getComplexes(selectedState.name, selectedDistrict.name);
        if (!active) return;
        setComplexes(response.data?.data || []);
      } catch (requestError) {
        if (!active) return;
        setError(requestError.response?.data?.error || 'Unable to load court complexes.');
      }
    }

    setComplexId('');
    loadComplexes();
    return () => {
      active = false;
    };
  }, [selectedDistrict, selectedState]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setStatusText('');
    setSearched(true);

    if (activeMode === 'cnr') {
      const normalized = cnr.trim().toUpperCase();
      if (!normalized) {
        setError('Enter a CNR to open the case.');
        return;
      }
      navigate(`/ecourts/case/${encodeURIComponent(normalized)}`);
      return;
    }

    if (!isLiveMode) {
      setResults([]);
      setStatusText('This stitched mode is mapped in the terminal but the scraper has not exposed that search path yet.');
      return;
    }

    if (!query.trim()) {
      setError(activeMode === 'party-name' ? 'Enter a petitioner or respondent name to search.' : 'Enter an advocate name to search.');
      return;
    }

    const payload = {
      search_type: activeMode === 'party-name' ? 'party' : 'advocate',
      query: query.trim(),
      court_type: courtType,
    };

    if (activeMode === 'party-name') {
      if (!registrationYear.trim()) {
        setError('Enter the case registration year for party-name search.');
        return;
      }
      payload.registration_year = registrationYear.trim();
      payload.case_status = caseStatus;
    }

    if (courtType === 'high_court') {
      if (!highCourtId || !benchCode) {
        setError('Select a high court and bench.');
        return;
      }
      payload.high_court_id = highCourtId;
      payload.bench_code = benchCode;
    } else {
      if (!stateId || !districtId || !complexId) {
        setError('Select district court state, district, and complex.');
        return;
      }
      payload.state_id = stateId;
      payload.district_id = districtId;
      payload.court_complex_id = complexId;
    }

    setLoading(true);

    try {
      const resolved = await runCaseSearch(payload);
      const caseList = resolved.data?.case_list || [];
      setResults(caseList);
      setStatusText(
        caseList.length > 0
          ? `${caseList.length} case matches returned from the scraper runtime.`
          : 'The scraper completed, but no matching cases were returned.',
      );
    } catch (requestError) {
      setResults([]);
      setError(requestError.response?.data?.error || requestError.message || 'Unable to complete the case-status search.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-6xl">
      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="text-[11px] font-black uppercase tracking-[0.28em] text-primary">Case Status</p>
            <h1 className="mt-3 text-3xl font-black tracking-tight text-ink">Scraper-backed case status terminal</h1>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              This screen follows the stitched case-status information architecture, but it only lights up the search modes the scraper actually supports today.
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

        <div className="mt-6 flex flex-wrap gap-2">
          {availableModes.map((mode) => {
            const live = mode.enabled;
            const active = activeMode === mode.id;
            return (
              <button
                key={mode.id}
                type="button"
                onClick={() => setActiveMode(mode.id)}
                className={`rounded-full border px-4 py-2 text-xs font-black uppercase tracking-[0.18em] transition-colors ${active ? 'border-primary bg-primary text-white' : modeTone(live)}`}
              >
                {mode.label}
              </button>
            );
          })}
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          <div className="flex gap-1 rounded-2xl bg-background-light p-1 w-fit">
            {[
              { key: 'high_court', label: 'High Court' },
              { key: 'district_court', label: 'District Court' },
            ].map((option) => (
              <button
                key={option.key}
                type="button"
                onClick={() => setCourtType(option.key)}
                className={`rounded-xl px-4 py-2 text-xs font-black uppercase tracking-[0.16em] transition-colors ${courtType === option.key ? 'bg-white text-primary shadow-sm' : 'text-slate-500'}`}
              >
                {option.label}
              </button>
            ))}
          </div>

          {courtType === 'high_court' ? (
            <div className="grid gap-4 md:grid-cols-2">
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
                  {benchOptions.map((bench) => (
                    <option key={bench.code} value={bench.code}>{bench.name}</option>
                  ))}
                </select>
              </div>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">State</label>
                <select value={stateId} onChange={(event) => setStateId(event.target.value)} className="input-base">
                  <option value="">Select state</option>
                  {states.map((item) => (
                    <option key={item.id} value={item.id}>{item.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">District</label>
                <select value={districtId} onChange={(event) => setDistrictId(event.target.value)} className="input-base" disabled={!selectedState}>
                  <option value="">Select district</option>
                  {districts.map((item) => (
                    <option key={item.id} value={item.id}>{item.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Complex</label>
                <select value={complexId} onChange={(event) => setComplexId(event.target.value)} className="input-base" disabled={!selectedDistrict}>
                  <option value="">Select complex</option>
                  {complexes.map((item) => (
                    <option key={item.id} value={item.id}>{item.name}</option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {activeMode === 'cnr' ? (
            <div>
              <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">CNR</label>
              <input
                type="text"
                value={cnr}
                onChange={(event) => setCnr(event.target.value.toUpperCase())}
                placeholder="Enter CNR"
                className="input-base font-mono uppercase"
              />
            </div>
          ) : (
            <div className={`grid gap-4 ${activeMode === 'party-name' ? 'md:grid-cols-[minmax(0,2fr),180px,220px]' : ''}`}>
              <div>
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Search Query</label>
                <input
                  type="text"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={activeMode === 'party-name' ? 'Enter petitioner or respondent name' : activeMode === 'advocate' ? 'Enter advocate name' : 'This mode is staged for a later scraper pass'}
                  className="input-base"
                  disabled={!isLiveMode}
                />
              </div>
              {activeMode === 'party-name' ? (
                <div>
                  <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Registration Year</label>
                  <input
                    type="text"
                    value={registrationYear}
                    onChange={(event) => setRegistrationYear(event.target.value.replace(/\D/g, '').slice(0, 4))}
                    placeholder="2024"
                    className="input-base font-mono"
                    disabled={!isLiveMode}
                  />
                </div>
              ) : null}
              {activeMode === 'party-name' ? (
                <div>
                  <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Case Status</label>
                  <select value={caseStatus} onChange={(event) => setCaseStatus(event.target.value)} className="input-base" disabled={!isLiveMode}>
                    <option value="both">Both</option>
                    <option value="pending">Pending</option>
                    <option value="disposed">Disposed</option>
                  </select>
                </div>
              ) : null}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <button type="submit" className="btn-primary min-w-[180px]" disabled={loading}>
              {loading ? 'Running scraper...' : activeMode === 'cnr' ? 'Open case' : 'Run case-status search'}
            </button>
            {!isLiveMode ? (
              <p className="text-xs font-medium text-slate-500">
                {activeMode === 'party-name' && courtType === 'district_court'
                  ? 'Party-name search is live on High Court only for now; district-court party selectors still need verification.'
                  : 'This stitched search mode is mapped, but not yet backed by scraper selectors.'}
              </p>
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

      {searched ? (
        <div className="mt-8 rounded-[24px] border border-primary/10 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <p className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Results</p>
              <h2 className="mt-2 text-xl font-black text-ink">{results.length} case matches</h2>
            </div>
          </div>
          {results.length > 0 ? (
            <div className="grid gap-4 lg:grid-cols-2">
              {results.map((item, index) => (
                <ResultCard key={`${item.cnr || item.cnr_number || 'row'}-${index}`} item={item} detailPath={getCaseDetailPath(item)} />
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-primary/15 bg-background-light px-4 py-6 text-sm text-slate-500">
              No results are showing yet for this search.
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}