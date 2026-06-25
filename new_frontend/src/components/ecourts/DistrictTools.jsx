import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getDcCourtComplexes,
  getDcCourtsWithinComplex,
  getDcDistricts,
  getDcStates,
  getDistrictCauseList,
  searchDistrictCaseStatus,
  searchDistrictCaveat,
  searchDistrictCourtOrders,
  unwrapEcourtsPayload,
} from './common/ecourtsApi';
import { buildScopedCaseDetailPath } from './common/ecourtsScope';
import ResultCard from './common/ResultCard';

const TABS = [
  { id: 'case-status', label: 'Case Status' },
  { id: 'court-orders', label: 'Court Orders' },
  { id: 'cause-list', label: 'Cause List' },
  { id: 'caveat', label: 'Caveat' },
];

const CASE_STATUS_TYPES = [
  { value: 'party_name', label: 'Party Name' },
  { value: 'case_number', label: 'Case Number' },
  { value: 'filing_number', label: 'Filing Number' },
  { value: 'advocate', label: 'Advocate' },
  { value: 'fir_number', label: 'FIR Number' },
  { value: 'act', label: 'Act / Section' },
  { value: 'case_type', label: 'Case Type' },
];

const COURT_ORDER_TYPES = [
  { value: 'party_name', label: 'Party Name' },
  { value: 'case_number', label: 'Case Number' },
  { value: 'court_number', label: 'Court Number' },
  { value: 'order_date', label: 'Order Date Range' },
];

const STATUS_OPTIONS = [
  { value: 'both', label: 'Both' },
  { value: 'pending', label: 'Pending' },
  { value: 'disposed', label: 'Disposed' },
];

const ORDER_TYPE_OPTIONS = [
  { value: 'both', label: 'Both' },
  { value: 'interim', label: 'Interim' },
  { value: 'final', label: 'Final' },
];

const LIST_TYPE_OPTIONS = [
  { value: 'civil', label: 'Civil' },
  { value: 'criminal', label: 'Criminal' },
];

const CAVEAT_MODE_OPTIONS = [
  { value: 'anywhere', label: 'Anywhere' },
  { value: 'starting_with', label: 'Starting With' },
  { value: 'subordinate_court', label: 'Subordinate Court' },
  { value: 'caveat_number', label: 'Caveat Number' },
];

function TabButton({ active, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition-colors ${
        active
          ? 'bg-primary text-ivory'
          : 'border border-primary/10 text-slate-500 hover:border-primary/30 hover:text-primary'
      }`}
    >
      {children}
    </button>
  );
}

function Field({ label, children, hint }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-semibold text-slate-700">{label}</label>
      {children}
      {hint ? <p className="mt-1 text-[11px] text-slate-400">{hint}</p> : null}
    </div>
  );
}

function SelectField({ label, value, onChange, options, placeholder, disabled = false, hint }) {
  return (
    <Field label={label} hint={hint}>
      <select value={value} onChange={onChange} disabled={disabled} className="input-base">
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </Field>
  );
}

function TextField({ label, value, onChange, placeholder, type = 'text', disabled = false, hint }) {
  return (
    <Field label={label} hint={hint}>
      <input type={type} value={value} onChange={onChange} placeholder={placeholder} disabled={disabled} className="input-base" />
    </Field>
  );
}

function SummaryStat({ label, value, tone = 'primary' }) {
  const toneClass = tone === 'amber' ? 'text-amber-700 bg-amber-50 border-amber-100' : 'text-primary bg-primary/5 border-primary/10';

  return (
    <div className={`rounded-2xl border px-4 py-4 ${toneClass}`}>
      <p className="text-[10px] font-black uppercase tracking-[0.18em] opacity-70">{label}</p>
      <p className="mt-2 text-2xl font-black">{value}</p>
    </div>
  );
}

function renderEntryLines(entry) {
  if (!entry || typeof entry !== 'object') {
    return [];
  }

  if (Array.isArray(entry.data)) {
    return entry.data.filter(Boolean).map((value, index) => ({ key: `row-${index}`, label: `Column ${index + 1}`, value }));
  }

  return Object.entries(entry)
    .filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== '')
    .map(([key, value]) => ({
      key,
      label: key.replace(/_/g, ' '),
      value: String(value),
    }));
}

export default function DistrictTools() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('case-status');
  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [complexes, setComplexes] = useState([]);
  const [courtsWithinComplex, setCourtsWithinComplex] = useState([]);
  const [selection, setSelection] = useState({
    stateId: '',
    districtId: '',
    courtComplexId: '',
  });
  const [caseStatusForm, setCaseStatusForm] = useState({
    searchType: 'party_name',
    partyName: '',
    registrationYear: '',
    caseType: '',
    caseNumber: '',
    year: '',
    filingNumber: '',
    advocateName: '',
    policeStation: '',
    firNumber: '',
    actType: '',
    section: '',
    status: 'both',
  });
  const [courtOrdersForm, setCourtOrdersForm] = useState({
    searchType: 'party_name',
    partyName: '',
    year: '',
    caseType: '',
    caseNumber: '',
    courtNumberId: '',
    fromDate: '',
    toDate: '',
    orderType: 'both',
  });
  const [causeListForm, setCauseListForm] = useState({
    courtNameId: '',
    date: new Date().toISOString().slice(0, 10),
    listType: 'civil',
  });
  const [caveatForm, setCaveatForm] = useState({
    searchMode: 'anywhere',
    caveatorName: '',
    caveateeName: '',
  });
  const [bootLoading, setBootLoading] = useState(true);
  const [selectorLoading, setSelectorLoading] = useState(false);
  const [resultLoading, setResultLoading] = useState(false);
  const [error, setError] = useState('');
  const [resultTitle, setResultTitle] = useState('');
  const [resultPayload, setResultPayload] = useState(null);

  const selectedState = useMemo(
    () => states.find((item) => String(item.id) === String(selection.stateId)) || null,
    [selection.stateId, states]
  );
  const selectedDistrict = useMemo(
    () => districts.find((item) => String(item.id) === String(selection.districtId)) || null,
    [districts, selection.districtId]
  );
  const selectedComplex = useMemo(
    () => complexes.find((item) => String(item.id) === String(selection.courtComplexId)) || null,
    [complexes, selection.courtComplexId]
  );

  const districtScope = useMemo(() => ({
    courtType: 'district_court',
    stateName: selectedState?.name || '',
    districtName: selectedDistrict?.name || '',
    courtId: selectedComplex?.id || '',
  }), [selectedComplex?.id, selectedDistrict?.name, selectedState?.name]);

  const resultCount = useMemo(() => {
    if (Array.isArray(resultPayload?.case_list)) {
      return resultPayload.case_list.length;
    }
    if (Array.isArray(resultPayload?.entries)) {
      return resultPayload.entries.length;
    }
    return 0;
  }, [resultPayload]);

  useEffect(() => {
    let active = true;

    async function bootstrap() {
      setBootLoading(true);
      try {
        const response = await getDcStates();
        if (!active) {
          return;
        }
        setStates(response.data?.data || []);
      } catch (requestError) {
        if (!active) {
          return;
        }
        setError(requestError.response?.data?.error || 'Unable to load District Court states.');
      } finally {
        if (active) {
          setBootLoading(false);
        }
      }
    }

    bootstrap();
    return () => {
      active = false;
    };
  }, []);

  async function handleStateChange(event) {
    const nextStateId = event.target.value;
    setSelection({ stateId: nextStateId, districtId: '', courtComplexId: '' });
    setDistricts([]);
    setComplexes([]);
    setCourtsWithinComplex([]);
    setCauseListForm((current) => ({ ...current, courtNameId: '' }));
    setCourtOrdersForm((current) => ({ ...current, courtNumberId: '' }));
    setResultPayload(null);
    setError('');

    if (!nextStateId) {
      return;
    }

    setSelectorLoading(true);
    try {
      const response = await getDcDistricts(nextStateId);
      setDistricts(response.data?.data || []);
    } catch (requestError) {
      setError(requestError.response?.data?.error || 'Unable to load districts for the selected state.');
    } finally {
      setSelectorLoading(false);
    }
  }

  async function handleDistrictChange(event) {
    const nextDistrictId = event.target.value;
    setSelection((current) => ({ ...current, districtId: nextDistrictId, courtComplexId: '' }));
    setComplexes([]);
    setCourtsWithinComplex([]);
    setCauseListForm((current) => ({ ...current, courtNameId: '' }));
    setCourtOrdersForm((current) => ({ ...current, courtNumberId: '' }));
    setResultPayload(null);
    setError('');

    if (!selection.stateId || !nextDistrictId) {
      return;
    }

    setSelectorLoading(true);
    try {
      const response = await getDcCourtComplexes(selection.stateId, nextDistrictId);
      setComplexes(response.data?.data || []);
    } catch (requestError) {
      setError(requestError.response?.data?.error || 'Unable to load court complexes for the selected district.');
    } finally {
      setSelectorLoading(false);
    }
  }

  async function handleComplexChange(event) {
    const nextComplexId = event.target.value;
    setSelection((current) => ({ ...current, courtComplexId: nextComplexId }));
    setCourtsWithinComplex([]);
    setCauseListForm((current) => ({ ...current, courtNameId: '' }));
    setCourtOrdersForm((current) => ({ ...current, courtNumberId: '' }));
    setResultPayload(null);
    setError('');

    if (!nextComplexId) {
      return;
    }

    setSelectorLoading(true);
    try {
      const response = await getDcCourtsWithinComplex(nextComplexId);
      setCourtsWithinComplex(response.data?.data || []);
    } catch (requestError) {
      setError(requestError.response?.data?.error || 'Unable to load courts within the selected complex.');
    } finally {
      setSelectorLoading(false);
    }
  }

  function ensureBaseSelection() {
    if (!selection.stateId || !selection.districtId || !selection.courtComplexId) {
      setError('Select a state, district, and court complex before running a District Court workflow.');
      return false;
    }
    return true;
  }

  function buildBasePayload() {
    return {
      state_id: selection.stateId,
      district_id: selection.districtId,
      court_complex_id: selection.courtComplexId,
      state_name: selectedState?.name || '',
      district_name: selectedDistrict?.name || '',
      court_name: selectedComplex?.name || '',
    };
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');

    if (!ensureBaseSelection()) {
      return;
    }

    const basePayload = buildBasePayload();

    let request;
    let nextTitle = '';

    if (activeTab === 'case-status') {
      const payload = { ...basePayload, search_type: caseStatusForm.searchType };

      if (caseStatusForm.searchType === 'party_name') {
        if (!caseStatusForm.partyName.trim() || !/^\d{4}$/.test(caseStatusForm.registrationYear.trim())) {
          setError('Party-name case status search requires a party name and 4-digit registration year.');
          return;
        }
        payload.party_name = caseStatusForm.partyName.trim();
        payload.registration_year = caseStatusForm.registrationYear.trim();
        payload.status = caseStatusForm.status;
      } else if (caseStatusForm.searchType === 'case_number') {
        if (!caseStatusForm.caseType.trim() || !caseStatusForm.caseNumber.trim() || !/^\d{4}$/.test(caseStatusForm.year.trim())) {
          setError('Case-number search requires case type, case number, and 4-digit year.');
          return;
        }
        payload.case_type = caseStatusForm.caseType.trim();
        payload.case_number = caseStatusForm.caseNumber.trim();
        payload.year = caseStatusForm.year.trim();
      } else if (caseStatusForm.searchType === 'filing_number') {
        if (!caseStatusForm.filingNumber.trim() || !/^\d{4}$/.test(caseStatusForm.year.trim())) {
          setError('Filing-number search requires filing number and 4-digit year.');
          return;
        }
        payload.filing_number = caseStatusForm.filingNumber.trim();
        payload.year = caseStatusForm.year.trim();
      } else if (caseStatusForm.searchType === 'advocate') {
        if (!caseStatusForm.advocateName.trim()) {
          setError('Advocate search requires an advocate name.');
          return;
        }
        payload.advocate_name = caseStatusForm.advocateName.trim();
        payload.status = caseStatusForm.status;
      } else if (caseStatusForm.searchType === 'fir_number') {
        if (!caseStatusForm.policeStation.trim() || !caseStatusForm.firNumber.trim() || !/^\d{4}$/.test(caseStatusForm.year.trim())) {
          setError('FIR search requires police station, FIR number, and 4-digit year.');
          return;
        }
        payload.police_station = caseStatusForm.policeStation.trim();
        payload.fir_number = caseStatusForm.firNumber.trim();
        payload.year = caseStatusForm.year.trim();
        payload.status = caseStatusForm.status;
      } else if (caseStatusForm.searchType === 'act') {
        if (!caseStatusForm.actType.trim() || !caseStatusForm.section.trim()) {
          setError('Act search requires act type and section.');
          return;
        }
        payload.act_type = caseStatusForm.actType.trim();
        payload.section = caseStatusForm.section.trim();
        payload.status = caseStatusForm.status;
      } else if (caseStatusForm.searchType === 'case_type') {
        if (!caseStatusForm.caseType.trim() || !/^\d{4}$/.test(caseStatusForm.year.trim())) {
          setError('Case-type search requires case type and 4-digit year.');
          return;
        }
        payload.case_type = caseStatusForm.caseType.trim();
        payload.year = caseStatusForm.year.trim();
        payload.status = caseStatusForm.status;
      }

      request = searchDistrictCaseStatus(payload);
      nextTitle = `District Case Status • ${CASE_STATUS_TYPES.find((item) => item.value === caseStatusForm.searchType)?.label || 'Search'}`;
    } else if (activeTab === 'court-orders') {
      const payload = { ...basePayload, search_type: courtOrdersForm.searchType, order_type: courtOrdersForm.orderType };

      if (courtOrdersForm.searchType === 'party_name') {
        if (!courtOrdersForm.partyName.trim() || !/^\d{4}$/.test(courtOrdersForm.year.trim())) {
          setError('Court-order party search requires a party name and 4-digit year.');
          return;
        }
        payload.party_name = courtOrdersForm.partyName.trim();
        payload.year = courtOrdersForm.year.trim();
      } else if (courtOrdersForm.searchType === 'case_number') {
        if (!courtOrdersForm.caseType.trim() || !courtOrdersForm.caseNumber.trim() || !/^\d{4}$/.test(courtOrdersForm.year.trim())) {
          setError('Court-order case-number search requires case type, case number, and 4-digit year.');
          return;
        }
        payload.case_type = courtOrdersForm.caseType.trim();
        payload.case_number = courtOrdersForm.caseNumber.trim();
        payload.year = courtOrdersForm.year.trim();
      } else if (courtOrdersForm.searchType === 'court_number') {
        if (!courtOrdersForm.courtNumberId) {
          setError('Select a court number or court within the chosen complex.');
          return;
        }
        payload.court_number_id = courtOrdersForm.courtNumberId;
      } else if (courtOrdersForm.searchType === 'order_date') {
        if (!courtOrdersForm.fromDate || !courtOrdersForm.toDate) {
          setError('Order-date search requires both from and to dates.');
          return;
        }
        payload.from_date = courtOrdersForm.fromDate;
        payload.to_date = courtOrdersForm.toDate;
      }

      request = searchDistrictCourtOrders(payload);
      nextTitle = `District Court Orders • ${COURT_ORDER_TYPES.find((item) => item.value === courtOrdersForm.searchType)?.label || 'Search'}`;
    } else if (activeTab === 'cause-list') {
      if (!causeListForm.courtNameId || !causeListForm.date) {
        setError('Cause list requires a court and date.');
        return;
      }

      request = getDistrictCauseList({
        ...basePayload,
        court_name_id: causeListForm.courtNameId,
        date: causeListForm.date,
        list_type: causeListForm.listType,
      });
      nextTitle = 'District Cause List';
    } else {
      if (!caveatForm.caveatorName.trim()) {
        setError('Caveat search requires a caveator name.');
        return;
      }

      request = searchDistrictCaveat({
        ...basePayload,
        search_mode: caveatForm.searchMode,
        caveator_name: caveatForm.caveatorName.trim(),
        caveatee_name: caveatForm.caveateeName.trim(),
      });
      nextTitle = 'District Caveat Search';
    }

    setResultLoading(true);
    try {
      const response = await request;
      setResultPayload(unwrapEcourtsPayload(response) || null);
      setResultTitle(nextTitle);
    } catch (requestError) {
      setResultPayload(null);
      setResultTitle('');
      setError(requestError.response?.data?.error || 'District Court request failed.');
    } finally {
      setResultLoading(false);
    }
  }

  const stateOptions = states.map((item) => ({ value: item.id, label: item.name }));
  const districtOptions = districts.map((item) => ({ value: item.id, label: item.name }));
  const complexOptions = complexes.map((item) => ({ value: item.id, label: item.name }));
  const courtWithinComplexOptions = courtsWithinComplex.map((item) => ({ value: item.id, label: item.name }));

  return (
    <div className="p-8 max-w-6xl">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-black tracking-tight text-ink">District Court Tools</h2>
          <p className="mt-1 text-sm text-slate-500">
            Live District Court workflows wired to the additive scraper APIs for case status, court orders, cause list, and caveat search.
          </p>
          <button
            type="button"
            onClick={() => navigate('/ecourts')}
            className="mt-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400 transition-colors hover:text-primary"
          >
            Back to eCourts Home
          </button>
        </div>
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700 max-w-md">
          Capsolver support stays on the backend path. This screen focuses on the district workflow and the richer `dc/*` API surface already exposed by the scraper.
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-3 mb-6">
        <SummaryStat label="States" value={states.length || '—'} />
        <SummaryStat label="Loaded Courts" value={complexes.length || '—'} />
        <SummaryStat label="Latest Results" value={resultCount || '—'} tone="amber" />
      </div>

      <div className="card p-6 mb-6">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400 mb-4">District Context</p>
        <div className="grid gap-4 md:grid-cols-3">
          <SelectField
            label="State"
            value={selection.stateId}
            onChange={handleStateChange}
            options={stateOptions}
            placeholder={bootLoading ? 'Loading states...' : 'Select a state'}
            disabled={bootLoading || resultLoading}
          />
          <SelectField
            label="District"
            value={selection.districtId}
            onChange={handleDistrictChange}
            options={districtOptions}
            placeholder={selection.stateId ? 'Select a district' : 'Choose state first'}
            disabled={!selection.stateId || selectorLoading || resultLoading}
          />
          <SelectField
            label="Court Complex"
            value={selection.courtComplexId}
            onChange={handleComplexChange}
            options={complexOptions}
            placeholder={selection.districtId ? 'Select a court complex' : 'Choose district first'}
            disabled={!selection.districtId || selectorLoading || resultLoading}
          />
        </div>
      </div>

      <div className="card p-6 mb-6">
        <div className="mb-5 flex flex-wrap gap-2">
          {TABS.map((tab) => (
            <TabButton
              key={tab.id}
              active={activeTab === tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                setError('');
                setResultPayload(null);
                setResultTitle('');
              }}
            >
              {tab.label}
            </TabButton>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {activeTab === 'case-status' ? (
            <>
              <div className="grid gap-4 md:grid-cols-3">
                <SelectField
                  label="Search Type"
                  value={caseStatusForm.searchType}
                  onChange={(event) => setCaseStatusForm((current) => ({ ...current, searchType: event.target.value }))}
                  options={CASE_STATUS_TYPES}
                  placeholder="Select search type"
                  disabled={resultLoading}
                />
                {(caseStatusForm.searchType === 'party_name' || caseStatusForm.searchType === 'advocate' || caseStatusForm.searchType === 'fir_number' || caseStatusForm.searchType === 'act' || caseStatusForm.searchType === 'case_type') ? (
                  <SelectField
                    label="Status"
                    value={caseStatusForm.status}
                    onChange={(event) => setCaseStatusForm((current) => ({ ...current, status: event.target.value }))}
                    options={STATUS_OPTIONS}
                    placeholder="Select status"
                    disabled={resultLoading}
                  />
                ) : <div />}
              </div>

              {caseStatusForm.searchType === 'party_name' ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <TextField label="Party Name" value={caseStatusForm.partyName} onChange={(event) => setCaseStatusForm((current) => ({ ...current, partyName: event.target.value }))} placeholder="Petitioner / Respondent name" disabled={resultLoading} />
                  <TextField label="Registration Year" value={caseStatusForm.registrationYear} onChange={(event) => setCaseStatusForm((current) => ({ ...current, registrationYear: event.target.value }))} placeholder="2026" disabled={resultLoading} hint="District party search follows the live eCourts registration-year requirement." />
                </div>
              ) : null}

              {caseStatusForm.searchType === 'case_number' ? (
                <div className="grid gap-4 md:grid-cols-3">
                  <TextField label="Case Type" value={caseStatusForm.caseType} onChange={(event) => setCaseStatusForm((current) => ({ ...current, caseType: event.target.value }))} placeholder="CC" disabled={resultLoading} />
                  <TextField label="Case Number" value={caseStatusForm.caseNumber} onChange={(event) => setCaseStatusForm((current) => ({ ...current, caseNumber: event.target.value }))} placeholder="123" disabled={resultLoading} />
                  <TextField label="Year" value={caseStatusForm.year} onChange={(event) => setCaseStatusForm((current) => ({ ...current, year: event.target.value }))} placeholder="2026" disabled={resultLoading} />
                </div>
              ) : null}

              {caseStatusForm.searchType === 'filing_number' ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <TextField label="Filing Number" value={caseStatusForm.filingNumber} onChange={(event) => setCaseStatusForm((current) => ({ ...current, filingNumber: event.target.value }))} placeholder="Enter filing number" disabled={resultLoading} />
                  <TextField label="Year" value={caseStatusForm.year} onChange={(event) => setCaseStatusForm((current) => ({ ...current, year: event.target.value }))} placeholder="2026" disabled={resultLoading} />
                </div>
              ) : null}

              {caseStatusForm.searchType === 'advocate' ? (
                <TextField label="Advocate Name" value={caseStatusForm.advocateName} onChange={(event) => setCaseStatusForm((current) => ({ ...current, advocateName: event.target.value }))} placeholder="Enter advocate name" disabled={resultLoading} />
              ) : null}

              {caseStatusForm.searchType === 'fir_number' ? (
                <div className="grid gap-4 md:grid-cols-3">
                  <TextField label="Police Station" value={caseStatusForm.policeStation} onChange={(event) => setCaseStatusForm((current) => ({ ...current, policeStation: event.target.value }))} placeholder="Station name" disabled={resultLoading} />
                  <TextField label="FIR Number" value={caseStatusForm.firNumber} onChange={(event) => setCaseStatusForm((current) => ({ ...current, firNumber: event.target.value }))} placeholder="FIR number" disabled={resultLoading} />
                  <TextField label="Year" value={caseStatusForm.year} onChange={(event) => setCaseStatusForm((current) => ({ ...current, year: event.target.value }))} placeholder="2026" disabled={resultLoading} />
                </div>
              ) : null}

              {caseStatusForm.searchType === 'act' ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <TextField label="Act Type" value={caseStatusForm.actType} onChange={(event) => setCaseStatusForm((current) => ({ ...current, actType: event.target.value }))} placeholder="Act type" disabled={resultLoading} />
                  <TextField label="Section" value={caseStatusForm.section} onChange={(event) => setCaseStatusForm((current) => ({ ...current, section: event.target.value }))} placeholder="Section" disabled={resultLoading} />
                </div>
              ) : null}

              {caseStatusForm.searchType === 'case_type' ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <TextField label="Case Type" value={caseStatusForm.caseType} onChange={(event) => setCaseStatusForm((current) => ({ ...current, caseType: event.target.value }))} placeholder="Case type" disabled={resultLoading} />
                  <TextField label="Year" value={caseStatusForm.year} onChange={(event) => setCaseStatusForm((current) => ({ ...current, year: event.target.value }))} placeholder="2026" disabled={resultLoading} />
                </div>
              ) : null}
            </>
          ) : null}

          {activeTab === 'court-orders' ? (
            <>
              <div className="grid gap-4 md:grid-cols-2">
                <SelectField
                  label="Search Type"
                  value={courtOrdersForm.searchType}
                  onChange={(event) => setCourtOrdersForm((current) => ({ ...current, searchType: event.target.value }))}
                  options={COURT_ORDER_TYPES}
                  placeholder="Select search type"
                  disabled={resultLoading}
                />
                <SelectField
                  label="Order Type"
                  value={courtOrdersForm.orderType}
                  onChange={(event) => setCourtOrdersForm((current) => ({ ...current, orderType: event.target.value }))}
                  options={ORDER_TYPE_OPTIONS}
                  placeholder="Select order type"
                  disabled={resultLoading}
                />
              </div>

              {courtOrdersForm.searchType === 'party_name' ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <TextField label="Party Name" value={courtOrdersForm.partyName} onChange={(event) => setCourtOrdersForm((current) => ({ ...current, partyName: event.target.value }))} placeholder="Enter party name" disabled={resultLoading} />
                  <TextField label="Year" value={courtOrdersForm.year} onChange={(event) => setCourtOrdersForm((current) => ({ ...current, year: event.target.value }))} placeholder="2026" disabled={resultLoading} />
                </div>
              ) : null}

              {courtOrdersForm.searchType === 'case_number' ? (
                <div className="grid gap-4 md:grid-cols-3">
                  <TextField label="Case Type" value={courtOrdersForm.caseType} onChange={(event) => setCourtOrdersForm((current) => ({ ...current, caseType: event.target.value }))} placeholder="CC" disabled={resultLoading} />
                  <TextField label="Case Number" value={courtOrdersForm.caseNumber} onChange={(event) => setCourtOrdersForm((current) => ({ ...current, caseNumber: event.target.value }))} placeholder="123" disabled={resultLoading} />
                  <TextField label="Year" value={courtOrdersForm.year} onChange={(event) => setCourtOrdersForm((current) => ({ ...current, year: event.target.value }))} placeholder="2026" disabled={resultLoading} />
                </div>
              ) : null}

              {courtOrdersForm.searchType === 'court_number' ? (
                <SelectField
                  label="Court Number"
                  value={courtOrdersForm.courtNumberId}
                  onChange={(event) => setCourtOrdersForm((current) => ({ ...current, courtNumberId: event.target.value }))}
                  options={courtWithinComplexOptions}
                  placeholder={selection.courtComplexId ? 'Select court number' : 'Choose court complex first'}
                  disabled={!selection.courtComplexId || resultLoading}
                  hint="These values come from the courts exposed within the selected court complex."
                />
              ) : null}

              {courtOrdersForm.searchType === 'order_date' ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <TextField label="From Date" type="date" value={courtOrdersForm.fromDate} onChange={(event) => setCourtOrdersForm((current) => ({ ...current, fromDate: event.target.value }))} disabled={resultLoading} />
                  <TextField label="To Date" type="date" value={courtOrdersForm.toDate} onChange={(event) => setCourtOrdersForm((current) => ({ ...current, toDate: event.target.value }))} disabled={resultLoading} />
                </div>
              ) : null}
            </>
          ) : null}

          {activeTab === 'cause-list' ? (
            <div className="grid gap-4 md:grid-cols-3">
              <SelectField
                label="Court"
                value={causeListForm.courtNameId}
                onChange={(event) => setCauseListForm((current) => ({ ...current, courtNameId: event.target.value }))}
                options={courtWithinComplexOptions}
                placeholder={selection.courtComplexId ? 'Select a court' : 'Choose court complex first'}
                disabled={!selection.courtComplexId || resultLoading}
              />
              <TextField label="Date" type="date" value={causeListForm.date} onChange={(event) => setCauseListForm((current) => ({ ...current, date: event.target.value }))} disabled={resultLoading} />
              <SelectField
                label="List Type"
                value={causeListForm.listType}
                onChange={(event) => setCauseListForm((current) => ({ ...current, listType: event.target.value }))}
                options={LIST_TYPE_OPTIONS}
                placeholder="Select list type"
                disabled={resultLoading}
              />
            </div>
          ) : null}

          {activeTab === 'caveat' ? (
            <div className="grid gap-4 md:grid-cols-3">
              <SelectField
                label="Search Mode"
                value={caveatForm.searchMode}
                onChange={(event) => setCaveatForm((current) => ({ ...current, searchMode: event.target.value }))}
                options={CAVEAT_MODE_OPTIONS}
                placeholder="Select search mode"
                disabled={resultLoading}
              />
              <TextField label="Caveator Name" value={caveatForm.caveatorName} onChange={(event) => setCaveatForm((current) => ({ ...current, caveatorName: event.target.value }))} placeholder="Required" disabled={resultLoading} />
              <TextField label="Caveatee Name" value={caveatForm.caveateeName} onChange={(event) => setCaveatForm((current) => ({ ...current, caveateeName: event.target.value }))} placeholder="Optional" disabled={resultLoading} />
            </div>
          ) : null}

          {error ? (
            <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
              {error}
            </div>
          ) : null}

          <div className="flex items-center justify-between gap-4 pt-2">
            <p className="text-xs text-slate-400">
              {selectorLoading ? 'Loading district selectors...' : 'The selected district context is reused across all four workflows.'}
            </p>
            <button type="submit" className="btn-primary flex items-center gap-2" disabled={bootLoading || selectorLoading || resultLoading}>
              <span className="material-symbols-outlined text-base">search</span>
              {resultLoading ? 'Running…' : 'Run Workflow'}
            </button>
          </div>
        </form>
      </div>

      <div className="card p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-400">Results</p>
            <h3 className="mt-1 text-lg font-black text-ink">{resultTitle || 'No district workflow run yet'}</h3>
          </div>
          {resultPayload ? (
            <div className="rounded-full border border-primary/10 bg-primary/5 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-primary">
              {resultCount} row{resultCount === 1 ? '' : 's'}
            </div>
          ) : null}
        </div>

        {resultLoading ? (
          <div className="rounded-2xl border border-primary/10 bg-background-light px-4 py-10 text-center text-sm text-slate-500">
            The District Court scraper job is running. This screen waits on the same async job surface used by the rest of eCourts.
          </div>
        ) : null}

        {!resultLoading && resultPayload && Array.isArray(resultPayload.case_list) ? (
          resultPayload.case_list.length > 0 ? (
            <div className="grid gap-4">
              {resultPayload.case_list.map((item, index) => {
                const cnr = item.cnr || item.cnr_number || '';
                return (
                  <ResultCard
                    key={`${cnr || item.case_number || 'district-result'}-${index}`}
                    item={item}
                    detailPath={cnr ? buildScopedCaseDetailPath(cnr, districtScope) : ''}
                  />
                );
              })}
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-background-light px-4 py-8 text-center text-sm text-slate-500">
              No records were returned for this district workflow.
            </div>
          )
        ) : null}

        {!resultLoading && resultPayload && Array.isArray(resultPayload.entries) ? (
          resultPayload.entries.length > 0 ? (
            <div className="space-y-4">
              {resultPayload.entries.map((entry, index) => {
                const lines = renderEntryLines(entry);
                return (
                  <div key={`cause-entry-${index}`} className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
                    <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">Entry {index + 1}</p>
                    <div className="mt-3 grid gap-2 md:grid-cols-2">
                      {lines.length > 0 ? lines.map((line) => (
                        <div key={line.key} className="rounded-xl border border-slate-100 bg-background-light px-3 py-2">
                          <p className="text-[10px] font-black uppercase tracking-[0.16em] text-slate-400">{line.label}</p>
                          <p className="mt-1 text-sm text-ink">{line.value}</p>
                        </div>
                      )) : (
                        <p className="text-sm text-slate-500">No structured fields available for this row.</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="rounded-2xl border border-slate-200 bg-background-light px-4 py-8 text-center text-sm text-slate-500">
              No cause-list rows were returned for the selected court and date.
            </div>
          )
        ) : null}

        {!resultLoading && !resultPayload ? (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-background-light px-4 py-10 text-center text-sm text-slate-500">
            Select a district context, choose a workflow tab, and run the search to see live district data here.
          </div>
        ) : null}
      </div>
    </div>
  );
}