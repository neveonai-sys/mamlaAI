import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import LocationCascade from './LocationCascade';
import {
  courtorderByParty,
  courtorderByCaseNumber,
  courtorderByCourtNumber,
  courtorderByOrderDate,
  getOrderCaseTypes,
  getOrderCourtNumbers,
  orderPdf,
} from './apiV2';

const SESSION_KEY = 'courtOrderSearchState';

const MODES = [
  { id: 'party', label: 'By Party' },
  { id: 'case-number', label: 'By Case Number' },
  { id: 'court-number', label: 'By Court Number' },
  { id: 'order-date', label: 'By Order Date' },
];

export default function CourtOrdersTerminal() {
  const navigate = useNavigate();

  const [locationInitialValues] = useState(() => {
    try {
      const navType = performance.getEntriesByType?.('navigation')?.[0]?.type;
      if (navType !== 'back_forward') return null;
      const s = JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null');
      return s?.location || null;
    } catch { return null; }
  });

  const [activeMode, setActiveMode] = useState(() => {
    try {
      const navType = performance.getEntriesByType?.('navigation')?.[0]?.type;
      if (navType !== 'back_forward') return 'party';
      return JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null')?.activeMode || 'party';
    }
    catch { return 'party'; }
  });
  const [location, setLocation] = useState({});

  // Dropdown data for specific modes
  const [caseTypes, setCaseTypes] = useState([]);
  const [courtNumbers, setCourtNumbers] = useState([]);
  const [loadingDropdown, setLoadingDropdown] = useState('');

  // Party mode
  const [partyName, setPartyName] = useState('');
  const [partyYear, setPartyYear] = useState('');

  // Case number mode
  const [caseType, setCaseType] = useState('');
  const [caseNumber, setCaseNumber] = useState('');
  const [caseYear, setCaseYear] = useState('');

  // Court number mode
  const [courtNumber, setCourtNumber] = useState('');

  // Order date mode
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  // Shared
  const [orderType, setOrderType] = useState('Both');

  // Results
  const [orders, setOrders] = useState([]);
  const [totalOrders, setTotalOrders] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [statusText, setStatusText] = useState('');
  const [searched, setSearched] = useState(false);

  // Restore form fields from session ONLY on browser Back navigation.
  // Hard refresh, direct URL open, and fresh navigation all start blank.
  useEffect(() => {
    try {
      const navType = performance.getEntriesByType?.('navigation')?.[0]?.type;
      if (navType !== 'back_forward') return;
      const raw = sessionStorage.getItem(SESSION_KEY);
      if (!raw) return;
      const s = JSON.parse(raw);
      if (s.location) setLocation(s.location);
      if (s.partyName !== undefined) setPartyName(s.partyName);
      if (s.partyYear !== undefined) setPartyYear(s.partyYear);
      if (s.caseType !== undefined) setCaseType(s.caseType);
      if (s.caseNumber !== undefined) setCaseNumber(s.caseNumber);
      if (s.caseYear !== undefined) setCaseYear(s.caseYear);
      if (s.courtNumber !== undefined) setCourtNumber(s.courtNumber);
      if (s.fromDate !== undefined) setFromDate(s.fromDate);
      if (s.toDate !== undefined) setToDate(s.toDate);
      if (s.orderType !== undefined) setOrderType(s.orderType);
      if (s.orders?.length) { setOrders(s.orders); setSearched(true); }
      if (s.totalOrders !== undefined) setTotalOrders(s.totalOrders);
      if (s.statusText) setStatusText(s.statusText);
    } catch { /* ignore */ }
  }, []);

  // Load case types when location is complete and case-number mode is active
  useEffect(() => {
    setCaseTypes([]);
    setCaseType('');
    if (activeMode !== 'case-number' || !location.isComplete) return;

    let active = true;
    setLoadingDropdown('case-types');
    getOrderCaseTypes(location.state_code, location.dist_code, location.court_complex_code, location.est_code)
      .then((res) => { if (active) setCaseTypes(res.data || []); })
      .catch(() => { if (active) setCaseTypes([]); })
      .finally(() => { if (active) setLoadingDropdown(''); });
    return () => { active = false; };
  }, [activeMode, location.isComplete, location.state_code, location.dist_code, location.court_complex_code, location.est_code]);

  // Load court numbers when complex is selected and court-number mode is active
  // (court-number tab doesn't need establishment — complex is enough)
  useEffect(() => {
    setCourtNumbers([]);
    setCourtNumber('');
    if (activeMode !== 'court-number' || !location.isComplexComplete) return;

    let active = true;
    setLoadingDropdown('court-numbers');
    getOrderCourtNumbers(location.state_code, location.dist_code, location.court_complex_code, '')
      .then((res) => { if (active) setCourtNumbers(res.data || []); })
      .catch(() => { if (active) setCourtNumbers([]); })
      .finally(() => { if (active) setLoadingDropdown(''); });
    return () => { active = false; };
  }, [activeMode, location.isComplexComplete, location.state_code, location.dist_code, location.court_complex_code]);

  async function handleDownloadPdf(pdfParams, label) {
    try {
      const res = await orderPdf(pdfParams);
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = label ? `${label}.pdf` : `court-order-${Date.now()}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      setError('Failed to download PDF.');
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setStatusText('');
    setOrders([]);
    sessionStorage.removeItem(SESSION_KEY); // clear stale state before new search

    // court-number and order-date modes only need state+district+complex
    const needsEst = activeMode === 'party' || activeMode === 'case-number';
    const locationReady = needsEst ? location.isComplete : location.isComplexComplete;
    if (!locationReady) {
      setError(needsEst
        ? 'Select state, district, complex, and establishment first.'
        : 'Select state, district, and court complex first.');
      return;
    }

    const base = {
      state_code: location.state_code,
      dist_code: location.dist_code,
      court_complex_code: location.court_complex_code,
      est_code: location.est_code,
    };

    setLoading(true);

    try {
      let res;

      if (activeMode === 'party') {
        if (!partyName.trim() || !partyYear.trim()) {
          setError('Enter party name and year.');
          setLoading(false);
          return;
        }
        res = await courtorderByParty({ ...base, party_name: partyName.trim(), year: partyYear.trim(), order_type: orderType });
      } else if (activeMode === 'case-number') {
        if (!caseType || !caseNumber.trim() || !caseYear.trim()) {
          setError('Select case type and enter case number and year.');
          setLoading(false);
          return;
        }
        res = await courtorderByCaseNumber({ ...base, case_type: caseType, case_number: caseNumber.trim(), year: caseYear.trim(), order_type: orderType });
      } else if (activeMode === 'court-number') {
        if (!courtNumber) {
          setError('Select a court number.');
          setLoading(false);
          return;
        }
        res = await courtorderByCourtNumber({ ...base, court_number: courtNumber, order_type: orderType });
      } else if (activeMode === 'order-date') {
        if (!fromDate || !toDate) {
          setError('Select both from and to dates.');
          setLoading(false);
          return;
        }
        res = await courtorderByOrderDate({ ...base, from_date: fromDate, to_date: toDate, order_type: orderType });
      }

      const orderList = res?.data?.orders || res?.data?.case_list || [];
      const total = res?.data?.total_orders ?? orderList.length;
      setOrders(orderList);
      setTotalOrders(total);
      setSearched(true);
      const txt = orderList.length > 0
        ? `${total} order(s) found.`
        : 'Search completed — no orders found.';
      setStatusText(txt);

      // Persist state for back-navigation restore
      try {
        sessionStorage.setItem(SESSION_KEY, JSON.stringify({
          activeMode,
          location,
          partyName, partyYear,
          caseType, caseNumber, caseYear,
          courtNumber,
          fromDate, toDate,
          orderType,
          orders: orderList,
          totalOrders: total,
          statusText: txt,
        }));
      } catch { /* quota exceeded — ignore */ }
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Court order search failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-6xl">
      <div className="rounded-[28px] border border-primary/10 bg-white p-8 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <p className="text-[11px] font-black uppercase tracking-[0.28em] text-primary">Court Orders</p>
            <h1 className="mt-3 text-3xl font-black tracking-tight text-ink">Court orders search</h1>
            <p className="mt-3 text-sm leading-7 text-slate-600">
              Search court orders by party name, case number, court number, or order date — backed by the live eCourts scraper.
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
          <LocationCascade
            onChange={setLocation}
            error={error}
            initialValues={locationInitialValues}
            hideEstablishment={activeMode === 'court-number' || activeMode === 'order-date'}
          />

          {/* Party mode */}
          {activeMode === 'party' && (
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Party Name</label>
                <input type="text" value={partyName} onChange={(e) => setPartyName(e.target.value)} placeholder="Enter party name" className="input-base" />
              </div>
              <div>
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Year</label>
                <input type="text" value={partyYear} onChange={(e) => setPartyYear(e.target.value.replace(/\D/g, '').slice(0, 4))} placeholder="2024" className="input-base font-mono" />
              </div>
            </div>
          )}

          {/* Case number mode */}
          {activeMode === 'case-number' && (
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">
                  Case Type {loadingDropdown === 'case-types' && <span className="text-primary">loading…</span>}
                </label>
                <select value={caseType} onChange={(e) => setCaseType(e.target.value)} className="input-base" disabled={!location.isComplete}>
                  <option value="">Select case type</option>
                  {caseTypes.map((ct, i) => (
                    <option key={`${ct.value || ct.code || i}`} value={ct.value || ct.code}>{ct.label || ct.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Case Number</label>
                <input type="text" value={caseNumber} onChange={(e) => setCaseNumber(e.target.value)} placeholder="e.g. 12345" className="input-base font-mono" />
              </div>
              <div>
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Year</label>
                <input type="text" value={caseYear} onChange={(e) => setCaseYear(e.target.value.replace(/\D/g, '').slice(0, 4))} placeholder="2024" className="input-base font-mono" />
              </div>
            </div>
          )}

          {/* Court number mode */}
          {activeMode === 'court-number' && (
            <div className="w-64">
              <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">
                Court Number {loadingDropdown === 'court-numbers' && <span className="text-primary">loading…</span>}
              </label>
              <select value={courtNumber} onChange={(e) => setCourtNumber(e.target.value)} className="input-base" disabled={!location.isComplete}>
                <option value="">Select court number</option>
                {courtNumbers.map((cn, i) => (
                  <option key={`${cn.value || cn.code || i}`} value={cn.value || cn.code}>{cn.label || cn.name || cn.value}</option>
                ))}
              </select>
            </div>
          )}

          {/* Order date mode */}
          {activeMode === 'order-date' && (
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">From Date</label>
                <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="input-base" />
              </div>
              <div>
                <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">To Date</label>
                <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="input-base" />
              </div>
            </div>
          )}

          {/* Order type — shared across all modes */}
          <div className="w-48">
            <label className="mb-2 block text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">Order Type</label>
            <select value={orderType} onChange={(e) => setOrderType(e.target.value)} className="input-base">
              <option value="Both">Both</option>
              <option value="Final">Final</option>
              <option value="Interim">Interim</option>
            </select>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button type="submit" className="btn-primary min-w-[180px]" disabled={loading}>
              {loading ? 'Searching…' : 'Search orders'}
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

      {/* Registry table */}
      {searched && (
        <div className="mt-8 overflow-hidden rounded-[16px] border border-primary/10 shadow-sm">
          {/* Header bar */}
          <div
            className="flex items-center justify-between px-5 py-3"
            style={{ backgroundColor: '#1f3753' }}
          >
            <span className="text-xs font-black uppercase tracking-[0.22em] text-white/80">
              Court Orders
            </span>
            <span className="text-xs font-black text-white">
              Total Orders: {totalOrders}
            </span>
          </div>

          {orders.length === 0 ? (
            <div className="px-5 py-8 text-center text-sm text-slate-500">
              No orders found for this search.
            </div>
          ) : (
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr style={{ backgroundColor: '#1f3753' }}>
                  {['#', 'Case', 'Petitioner / Respondent', 'Order Date', 'Order', 'View'].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-2 text-left text-[10px] font-black uppercase tracking-[0.18em] text-white/70"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {orders.map((item, idx) => {
                  const rowBg = idx % 2 === 0 ? '#f6f5ee' : '#eeeade';
                  const srNo = item.sr_no || String(idx + 1);
                  const caseRef = item.case_type_case_number_case_year || '—';
                  const parties = item.petitioner_name_versus_respondent_name || '';
                  const [pet = '', res = ''] = parties.split(/\s+[Vv][Ss]\.?\s+/);
                  const orderDate = item.order_date || '—';
                  const orderText = item.orders || '';
                  const pdfParams = item.pdf_params;
                  const pdfLabel = pdfParams?.label || `court-order-${srNo}-${orderDate.replace(/[/\\]/g, '-')}`;
                  const cino = item.cino;

                  return (
                    <tr key={idx} style={{ backgroundColor: rowBg }}>
                      <td className="px-4 py-3 text-xs font-mono text-slate-500 align-top">{srNo}</td>
                      <td className="px-4 py-3 align-top">
                        <span className="text-xs font-semibold" style={{ color: '#19314c' }}>{caseRef}</span>
                      </td>
                      <td className="px-4 py-3 align-top max-w-[220px]">
                        {pet && <div className="text-xs" style={{ color: '#19314c' }}>{pet.trim()}</div>}
                        {res && <div className="text-[11px] text-slate-500 mt-0.5">vs {res.trim()}</div>}
                        {!pet && !res && parties && (
                          <div className="text-xs" style={{ color: '#19314c' }}>{parties}</div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs font-mono align-top whitespace-nowrap" style={{ color: '#19314c' }}>
                        {orderDate}
                      </td>
                      <td className="px-4 py-3 align-top">
                        {pdfParams ? (
                          <button
                            type="button"
                            onClick={() => handleDownloadPdf(pdfParams, pdfLabel)}
                            className="rounded-full border border-primary/20 px-3 py-1 text-[11px] font-black uppercase tracking-[0.15em] text-primary transition-colors hover:bg-primary hover:text-white"
                          >
                            PDF
                          </button>
                        ) : orderText ? (
                          <span className="text-xs text-slate-500">{orderText.slice(0, 60)}{orderText.length > 60 ? '…' : ''}</span>
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 align-top">
                        {cino ? (
                          <Link
                            to={`/ecourts/case/${cino}`}
                            className="text-[11px] font-black uppercase tracking-[0.15em] text-primary underline-offset-2 hover:underline"
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
          )}
        </div>
      )}

      {!searched && (
        <div className="mt-8 rounded-[16px] border border-dashed border-primary/15 bg-background-light px-4 py-8 text-center text-sm text-slate-500">
          Run a court order search to see results here.
        </div>
      )}
    </div>
  );
}