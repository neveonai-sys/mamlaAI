import React, { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  downloadOrderPdf,
  getCaseByCnr,
  normalizeCaseData,
  unwrapEcourtsPayload,
} from './common/ecourtsApi';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(value) {
  if (!value || value === '-' || value === 'N/A') return '—';
  if (/^\d{2}-\d{2}-\d{4}$/.test(value)) {
    const [d, m, y] = value.split('-');
    const parsed = new Date(`${y}-${m}-${d}`);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
    }
  }
  const parsed = new Date(value);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  }
  return value;
}

// ─── Design tokens ────────────────────────────────────────────────────────────

const COURT_BLUE = '#0b3260';
const PAGE_BG = '#f7f3e8';

const TH = 'border border-black px-3 py-2 font-bold text-center text-xs bg-[#ddd8c9]';
const TD = 'border border-black px-3 py-2 text-center text-sm align-top';
const HEADER_ROW = 'text-white font-bold text-center py-2 px-4 text-xs tracking-widest uppercase';

// ─── Section wrapper ──────────────────────────────────────────────────────────

function Chevron({ open }) {
  return (
    <svg
      className={`w-4 h-4 transition-transform duration-200 ${open ? '' : 'rotate-180'}`}
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <polyline points="18 15 12 9 6 15" />
    </svg>
  );
}

function Section({ label, children, collapsible = false, open = true, onToggle }) {
  return (
    <div className="border-2 border-black rounded-sm overflow-hidden mb-4 shadow-sm">
      {collapsible ? (
        <button
          type="button"
          onClick={onToggle}
          className="w-full flex items-center justify-center relative border-b-2 border-black py-2 px-4 font-bold text-sm"
          style={{ backgroundColor: PAGE_BG }}
        >
          {label}
          <span className="absolute right-4 top-1/2 -translate-y-1/2">
            <Chevron open={open} />
          </span>
        </button>
      ) : (
        label
          ? <div className={HEADER_ROW} style={{ backgroundColor: COURT_BLUE }}>{label}</div>
          : null
      )}
      {(!collapsible || open) ? children : null}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function CaseDetail() {
  const navigate = useNavigate();
  const { cnr } = useParams();

  const [caseData, setCaseData]             = useState(null);
  const [orders, setOrders]                 = useState([]);
  const [loading, setLoading]               = useState(true);
  const [error, setError]                   = useState('');
  const [scrapeStatus, setScrapeStatus]     = useState('');
  const [refreshing, setRefreshing]         = useState(false);
  const [downloadError, setDownloadError]   = useState('');
  const [downloadingIndex, setDownloadingIndex] = useState(null);
  const [copied, setCopied]                 = useState(false);
  const [historyOpen, setHistoryOpen]       = useState(true);
  const [transfersOpen, setTransfersOpen]   = useState(false);

  // ─── Data fetching ─────────────────────────────────────────────────────────

  const fetchCase = useCallback(async () => {
    if (!cnr) return;
    setLoading(true);
    setError('');
    setScrapeStatus('Fetching case from eCourts…');
    try {
      const response = await getCaseByCnr(cnr);
      const raw = unwrapEcourtsPayload(response) || {};
      if (raw.success === false || raw.error) {
        throw new Error(raw.error || 'Case not found on eCourts.');
      }
      const nextCaseData = normalizeCaseData(raw);
      setCaseData(nextCaseData);
      setOrders(nextCaseData.orders || []);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Case not found or data unavailable.');
      setCaseData(null);
      setOrders([]);
    } finally {
      setLoading(false);
      setScrapeStatus('');
    }
  }, [cnr]);

  useEffect(() => { fetchCase(); }, [fetchCase]);

  // ─── Handlers ──────────────────────────────────────────────────────────────

  async function handleRefresh() {
    if (!cnr) return;
    setRefreshing(true);
    setError('');
    try { await fetchCase(); }
    catch (err) { setError(err.response?.data?.error || 'Refresh failed. Please try again.'); }
    finally { setRefreshing(false); }
  }

  /**
   * Download a court order PDF via the v2 backend.
   * order.pdf_params contains the params the FastAPI scraper needs to
   * fetch the actual PDF from eCourts (court_code, dist_code, etc.).
   */
  async function handleDownload(orderIndex) {
    const order = orders[orderIndex];
    if (!order?.pdf_params) {
      setDownloadError('PDF download not available for this order.');
      return;
    }
    setDownloadError('');
    setDownloadingIndex(orderIndex);
    try {
      const response = await downloadOrderPdf(order.pdf_params);
      const blob = new Blob([response.data], {
        type: response.headers['content-type'] || 'application/pdf',
      });
      const blobUrl = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      const disposition = response.headers['content-disposition'] || '';
      const filenameMatch = disposition.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
      anchor.href = blobUrl;
      const safeDate = (order.order_date || '').replace(/[/\\]/g, '-');
      anchor.download = filenameMatch?.[1] || `court-order-${orderIndex + 1}${safeDate ? '-' + safeDate : ''}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      let message = 'Download failed. Please try again.';
      try {
        if (err.response?.data instanceof Blob) {
          const text = await err.response.data.text();
          const payload = JSON.parse(text);
          message = payload.error || payload.message || message;
        } else if (err.response?.data?.error) {
          message = err.response.data.error;
        }
      } catch { message = err.message || message; }
      setDownloadError(message);
    } finally {
      setDownloadingIndex(null);
    }
  }

  function handleCopyLink() {
    navigator.clipboard?.writeText(window.location.href).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    }).catch(() => {});
  }

  // ─── Loading / error states ────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <span className="material-symbols-outlined text-primary text-4xl animate-spin">progress_activity</span>
        {scrapeStatus
          ? <p className="text-sm text-slate-500 text-center max-w-xs">{scrapeStatus}</p>
          : null}
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="p-8 max-w-3xl">
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <button type="button" onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-primary hover:underline">
            <span className="material-symbols-outlined text-sm">arrow_back</span> Back
          </button>
          <Link to="/ecourts/case-search" className="text-sm text-slate-500 hover:text-primary hover:underline">Case Search</Link>
          <Link to="/ecourts" className="text-sm text-slate-500 hover:text-primary hover:underline">eCourts Home</Link>
        </div>
        <div className="card p-8 text-center">
          <span className="material-symbols-outlined text-slate-300 text-5xl block mb-3">gavel</span>
          <p className="text-slate-500">{error || 'Case data not available.'}</p>
        </div>
      </div>
    );
  }

  const cd = caseData;
  const fir = cd.fir_details && Object.keys(cd.fir_details).length > 0 ? cd.fir_details : null;
  const courtAndJudge = [cd.court_no, cd.bench_name].filter(Boolean).join(' — ') || cd.court_name || '—';

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen font-serif" style={{ backgroundColor: PAGE_BG }}>

      {/* ── Top action bar ─────────────────────────────────────────────────── */}
      <div className="bg-white border-b border-black/10 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 font-sans">
        <nav className="flex items-center gap-2 text-sm">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="flex items-center gap-1 text-primary hover:underline"
          >
            <span className="material-symbols-outlined text-sm">arrow_back</span>
            Back
          </button>
          <span className="text-slate-300">·</span>
          <Link to="/ecourts/case-search" className="text-slate-500 hover:text-primary hover:underline">
            Case Search
          </Link>
          <span className="text-slate-300">·</span>
          <Link to="/ecourts" className="text-slate-500 hover:text-primary hover:underline">
            eCourts Home
          </Link>
        </nav>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopyLink}
            className="rounded-full border border-primary/15 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-primary font-sans"
          >
            {copied ? '✓ Copied' : 'Copy Link'}
          </button>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={refreshing}
            className="btn-primary flex items-center gap-1.5 disabled:opacity-60 text-xs font-sans"
          >
            <span className={`material-symbols-outlined text-sm ${refreshing ? 'animate-spin' : ''}`}>
              refresh
            </span>
            {refreshing ? 'Refreshing…' : 'Refresh Case'}
          </button>
        </div>
      </div>

      {/* ── Case title hero ────────────────────────────────────────────────── */}
      <header
        className="text-white py-5 px-6 text-center"
        style={{ backgroundColor: COURT_BLUE }}
      >
        <div className="flex flex-wrap items-center justify-center gap-3 mb-2 font-sans">
          {cd.case_status ? (
            <span className="text-[11px] px-2.5 py-0.5 rounded-full font-bold uppercase bg-white/20 border border-white/30">
              {cd.case_status}
            </span>
          ) : null}
          <span className="text-white/60 text-xs font-mono">{cd.cnr || cnr}</span>
          {cd.next_hearing_date ? (
            <span className="text-yellow-200 text-xs">
              Next Hearing: {fmt(cd.next_hearing_date)}
            </span>
          ) : null}
        </div>
        <h1 className="text-xl font-serif leading-snug max-w-4xl mx-auto">
          {cd.case_title || 'Case Record'}
        </h1>
        {cd.court_name ? (
          <p className="mt-1 text-white/70 text-sm font-sans">{cd.court_name}</p>
        ) : null}
      </header>

      {error ? (
        <div className="mx-4 mt-3 flex items-center gap-2 rounded border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600 font-sans">
          <span className="material-symbols-outlined text-base">error</span>
          {error}
        </div>
      ) : null}

      {/* ── Main content ───────────────────────────────────────────────────── */}
      <main className="container mx-auto px-4 py-5 max-w-5xl">

        {/* 1. Case Summary */}
        <Section label="Case Summary">
          <table className="w-full border-collapse">
            <tbody>
              <tr>
                <th className={TH}>Case Type</th>
                <th className={TH}>CNR Number</th>
                <th className={TH}>Filing Date</th>
                <th className={TH}>Registration Date</th>
              </tr>
              <tr>
                <td className={TD}>{cd.case_type || '—'}</td>
                <td className={`${TD} font-mono text-xs`}>{cd.cnr || cnr}</td>
                <td className={TD}>{fmt(cd.filing_date)}</td>
                <td className={TD}>{fmt(cd.registration_date)}</td>
              </tr>
              <tr>
                <th className={TH}>Filing Number</th>
                <th className={TH}>Registration Number</th>
                <th className={TH}>e-Filing Number</th>
                <th className={TH}>e-Filing Date</th>
              </tr>
              <tr>
                <td className={TD}>{cd.filing_number || '—'}</td>
                <td className={TD}>{cd.case_number || '—'}</td>
                <td className={TD}>{cd.e_filing_number || 'N/A'}</td>
                <td className={TD}>{fmt(cd.e_filing_date)}</td>
              </tr>
            </tbody>
          </table>
        </Section>

        {/* 2. Case Status */}
        <Section label="Case Status">
          <table className="w-full border-collapse">
            <tbody>
              <tr>
                <th className={TH}>First Hearing Date</th>
                <th className={TH}>Next Hearing Date</th>
                <th className={TH}>Case Stage</th>
                <th className={TH}>Court Number and Judge</th>
              </tr>
              <tr>
                <td className={TD}>{fmt(cd.first_hearing_date)}</td>
                <td className={`${TD} font-semibold`} style={{ color: COURT_BLUE }}>
                  {fmt(cd.next_hearing_date)}
                </td>
                <td className={TD}>{cd.case_status || '—'}</td>
                <td className={TD}>{courtAndJudge}</td>
              </tr>
            </tbody>
          </table>
        </Section>

        {/* 3. Parties */}
        <Section label="">
          <table className="w-full border-collapse">
            <tbody>
              <tr>
                <th
                  colSpan={2}
                  className={`${HEADER_ROW} border-r-2 border-black`}
                  style={{ backgroundColor: COURT_BLUE }}
                >
                  Petitioner &amp; Advocate
                </th>
                <th
                  colSpan={2}
                  className={HEADER_ROW}
                  style={{ backgroundColor: COURT_BLUE }}
                >
                  Respondent &amp; Advocate
                </th>
              </tr>
              <tr>
                <th className={`${TH} w-1/4`}>Petitioner</th>
                <th className={`${TH} w-1/4`}>Advocate</th>
                <th className={`${TH} w-1/4`}>Respondent</th>
                <th className={`${TH} w-1/4`}>Advocate</th>
              </tr>
              <tr>
                <td className={`${TD} text-left`}>
                  {cd.petitioners?.length > 0
                    ? cd.petitioners.map((p, i) => (
                        <div key={i} className="mb-1">{i + 1}. {p}</div>
                      ))
                    : '—'}
                </td>
                <td className={`${TD} text-left`}>
                  {cd.petitioner_advocates?.length > 0
                    ? cd.petitioner_advocates.map((a, i) => <div key={i} className="mb-1">{a}</div>)
                    : '—'}
                </td>
                <td className={`${TD} text-left`}>
                  {cd.respondents?.length > 0
                    ? cd.respondents.map((r, i) => (
                        <div key={i} className="mb-1">{i + 1}. {r}</div>
                      ))
                    : '—'}
                </td>
                <td className={`${TD} text-left`}>
                  {cd.respondent_advocates?.length > 0
                    ? cd.respondent_advocates.map((a, i) => <div key={i} className="mb-1">{a}</div>)
                    : 'N/A'}
                </td>
              </tr>
            </tbody>
          </table>
        </Section>

        {/* 4. Acts & FIR */}
        <Section label="Acts &amp; FIR">
          <table className="w-full border-collapse">
            <tbody>
              <tr>
                <th colSpan={2} className={TH}>Under Act(s)</th>
                <th colSpan={2} className={TH}>Under Section(s)</th>
              </tr>
              {cd.acts_and_sections?.length > 0
                ? cd.acts_and_sections.map((item, i) => {
                    const dashIdx = item.indexOf(' — ');
                    const act   = dashIdx >= 0 ? item.slice(0, dashIdx) : item;
                    const sects = dashIdx >= 0 ? item.slice(dashIdx + 3) : '';
                    return (
                      <tr key={i}>
                        <td colSpan={2} className={TD}>{act || '—'}</td>
                        <td colSpan={2} className={TD}>{sects || '—'}</td>
                      </tr>
                    );
                  })
                : (
                  <tr>
                    <td colSpan={4} className={TD}>—</td>
                  </tr>
                )}

              {fir ? (
                <>
                  <tr>
                    <td
                      colSpan={4}
                      className={`${HEADER_ROW} border-t-2 border-black`}
                      style={{ backgroundColor: COURT_BLUE }}
                    >
                      FIR Details
                    </td>
                  </tr>
                  <tr>
                    <th colSpan={2} className={TH}>Police Station</th>
                    <th className={TH}>FIR Number</th>
                    <th className={TH}>Year</th>
                  </tr>
                  <tr>
                    <td colSpan={2} className={TD}>
                      {fir['Police Station'] || fir['police_station'] || '—'}
                    </td>
                    <td className={TD}>
                      {fir['FIR Number'] || fir['fir_number'] || '—'}
                    </td>
                    <td className={TD}>
                      {fir['Year'] || fir['year'] || '—'}
                    </td>
                  </tr>
                </>
              ) : null}
            </tbody>
          </table>
        </Section>

        {/* 5. Orders & Judgments — visible only when the case has orders */}
        {orders.length > 0 ? (
          <Section label="Orders &amp; Judgments">
            {downloadError ? (
              <div className="flex items-center gap-2 border-b-2 border-black bg-red-50 px-4 py-2 text-xs text-red-600 font-sans">
                <span className="material-symbols-outlined text-sm">error</span>
                {downloadError}
              </div>
            ) : null}
            <table className="w-full border-collapse">
              <tbody>
                <tr>
                  <th className={`${TH} w-8`}>#</th>
                  <th className={TH}>Order Date</th>
                  <th className={TH}>Type</th>
                  <th className={TH}>Filename / Description</th>
                  <th className={`${TH} w-28`}>Download</th>
                </tr>
                {orders.map((order) => (
                  <tr key={order.index}>
                    <td className={TD}>{order.index + 1}</td>
                    <td className={TD}>{fmt(order.order_date)}</td>
                    <td className={TD}>{order.order_type || '—'}</td>
                    <td className={TD}>
                      {order.order_type || `Order ${order.index + 1}`}
                    </td>
                    <td className={TD}>
                      {/* pdf_params holds the POST body needed by /api/ecourts/v2/case/order-pdf/ */}
                      {order.pdf_params ? (
                        <button
                          type="button"
                          onClick={() => handleDownload(order.index)}
                          disabled={downloadingIndex === order.index}
                          className="text-xs font-sans underline disabled:opacity-50 hover:opacity-70"
                          style={{ color: COURT_BLUE }}
                        >
                          {downloadingIndex === order.index ? 'Downloading…' : '⬇ PDF'}
                        </button>
                      ) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        ) : null}

        {/* 6. Case History — collapsible */}
        {cd.hearing_history?.length > 0 ? (
          <Section
            label="Case History"
            collapsible
            open={historyOpen}
            onToggle={() => setHistoryOpen((v) => !v)}
          >
            <div className="p-2">
              <table className="w-full border-2 border-black border-collapse">
                <tbody>
                  <tr>
                    <th className={`${TH} w-2/5`}>Judge</th>
                    <th className={TH}>Business on Date</th>
                    <th className={TH}>Hearing Date</th>
                    <th className={TH}>Purpose of Hearing</th>
                  </tr>
                  {cd.hearing_history.map((h, i) => (
                    <tr
                      key={i}
                      className={i % 2 === 0 ? 'bg-white' : ''}
                      style={i % 2 !== 0 ? { backgroundColor: PAGE_BG } : {}}
                    >
                      <td className={`${TD} text-left`}>{h.judge || '—'}</td>
                      <td className={TD}>
                        {/* "Business on Date" — styled as a hyperlink.
                            To wire this to court orders: pass h.business_params
                            to navigateToCauseList or the CourtOrdersTerminal. */}
                        {h.business_date
                          ? (
                            <span
                              className="underline cursor-default font-medium"
                              style={{ color: COURT_BLUE }}
                            >
                              {h.business_date}
                            </span>
                          )
                          : '—'}
                      </td>
                      <td className={TD}>{h.hearing_date || '—'}</td>
                      <td className={TD}>{h.purpose || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        ) : null}

        {/* 7. Transfer Details — collapsible */}
        {cd.case_transfer_details?.length > 0 ? (
          <Section
            label="Transfer Details"
            collapsible
            open={transfersOpen}
            onToggle={() => setTransfersOpen((v) => !v)}
          >
            <div className="p-2">
              <table className="w-full border-2 border-black border-collapse">
                <tbody>
                  <tr>
                    <th className={`${TH} w-1/6`}>Reg. No.</th>
                    <th className={`${TH} w-1/6`}>Transfer Date</th>
                    <th className={TH}>From Court Number and Judge</th>
                    <th className={TH}>To Court Number and Judge</th>
                  </tr>
                  {cd.case_transfer_details.map((t, i) => (
                    <tr
                      key={i}
                      className={i % 2 === 0 ? 'bg-white' : ''}
                      style={i % 2 !== 0 ? { backgroundColor: PAGE_BG } : {}}
                    >
                      <td className={TD}>{t['Registration Number'] || '—'}</td>
                      <td className={TD}>{fmt(t['Transfer Date'])}</td>
                      <td className={`${TD} text-left`}>{t['From Court Number and Judge'] || '—'}</td>
                      <td className={`${TD} text-left font-medium`} style={{ color: COURT_BLUE }}>
                        {t['To Court Number and Judge'] || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        ) : null}
      </main>
    </div>
  );
}
