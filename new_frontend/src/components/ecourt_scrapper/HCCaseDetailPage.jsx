import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import { searchHCCnr, downloadHCOrderPdf } from './apiHC';

// ── Design tokens (matches CaseDetail.jsx) ───────────────────────────────────
const COURT_BLUE = '#0b3260';
const PAGE_BG    = '#f7f3e8';
const TH = 'border border-black px-3 py-2 font-bold text-center text-xs bg-[#ddd8c9]';
const TD = 'border border-black px-3 py-2 text-sm align-top';
const HDR = 'text-white font-bold text-center py-2 px-4 text-xs tracking-widest uppercase';

// ── Section wrapper ───────────────────────────────────────────────────────────
function Section({ label, children }) {
  return (
    <div className="border-2 border-black overflow-hidden mb-4 shadow-sm">
      {label && (
        <div className={HDR} style={{ backgroundColor: COURT_BLUE }}>{label}</div>
      )}
      {children}
    </div>
  );
}

// Format 16-char CNR: WBCHCO0000862020 → WBCHCO-000086-2020
function formatCino(cino) {
  if (!cino) return '';
  const c = cino.replace(/-/g, '');
  if (c.length === 16) return `${c.slice(0, 6)}-${c.slice(6, 12)}-${c.slice(12)}`;
  return cino;
}

// Parse "Act Name — Section" string
function parseAct(act) {
  const idx = act.indexOf(' — ');
  if (idx === -1) return { name: act.trim(), section: 'NA' };
  return { name: act.slice(0, idx).trim(), section: act.slice(idx + 3).trim() || 'NA' };
}

// ── Main component ────────────────────────────────────────────────────────────
export default function HCCaseDetailPage() {
  const { cino } = useParams();
  const navigate = useNavigate();  const dispatch  = useDispatch();
  const [caseData, setCaseData]             = useState(null);
  const [loading, setLoading]               = useState(true);
  const [error, setError]                   = useState('');
  const [downloadingIdx, setDownloadingIdx] = useState(null);
  const [downloadError, setDownloadError]   = useState('');

  useEffect(() => {
    if (!cino) return;
    let active = true;
    setLoading(true);
    dispatch(beginBlocking({ message: 'Loading case details...' }));
    setError('');
    searchHCCnr(cino)
      .then((res) => { if (active) setCaseData(res.data); })
      .catch((err) => {
        if (!active) return;
        setError(
          err.response?.data?.detail ||
          err.response?.data?.error ||
          `Unable to fetch case details for CNR: ${cino}`
        );
      })
      .finally(() => { if (active) { setLoading(false); dispatch(stopBlocking()); } });
    return () => { active = false; };
  }, [cino]);

  async function handlePdfDownload(docUrl, idx) {
    setDownloadingIdx(idx);
    setDownloadError('');
    try {
      const resp = await downloadHCOrderPdf(docUrl);
      const blob = new Blob([resp.data], { type: 'application/pdf' });
      const objUrl = URL.createObjectURL(blob);
      window.open(objUrl, '_blank');
      setTimeout(() => URL.revokeObjectURL(objUrl), 60000);
    } catch (err) {
      let msg = 'PDF download failed. Please try again.';
      if (err.response?.data instanceof Blob) {
        try { const t = await err.response.data.text(); msg = JSON.parse(t).detail || JSON.parse(t).error || msg; }
        catch { /* ignore */ }
      } else {
        msg = err.response?.data?.detail || err.response?.data?.error || msg;
      }
      setDownloadError(msg);
    } finally {
      setDownloadingIdx(null);
    }
  }

  // ── Loading ──────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <span className="material-symbols-outlined text-primary text-4xl animate-spin">progress_activity</span>
        <p className="text-sm text-slate-500">Fetching case details from High Court portal…</p>
        <p className="text-xs text-slate-400">This may take 10–30 seconds (CAPTCHA solve required).</p>
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────────
  if (error || !caseData) {
    return (
      <div className="p-8 max-w-3xl">
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <button type="button" onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-primary hover:underline">
            <span className="material-symbols-outlined text-sm">arrow_back</span> Back
          </button>
          <button type="button" onClick={() => navigate('/ecourts/hc')} className="text-sm text-slate-500 hover:text-primary hover:underline">HC Home</button>
        </div>
        <div className="card p-8 text-center">
          <span className="material-symbols-outlined text-slate-300 text-5xl block mb-3">gavel</span>
          <p className="text-slate-500">{error || 'Case data not available.'}</p>
        </div>
      </div>
    );
  }

  const d = caseData;
  const fCino = formatCino(d.cino);

  return (
    <div className="min-h-screen font-serif" style={{ backgroundColor: PAGE_BG }}>

      {/* ── Top bar ─────────────────────────────────────────────────────── */}
      <div className="bg-white border-b border-black/10 px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 font-sans">
        <nav className="flex items-center gap-2 text-sm">
          <button type="button" onClick={() => navigate(-1)} className="flex items-center gap-1 text-primary hover:underline">
            <span className="material-symbols-outlined text-sm">arrow_back</span> Back
          </button>
          <span className="text-slate-300">·</span>
          <button type="button" onClick={() => navigate('/ecourts/hc/case-status')} className="text-slate-500 hover:text-primary hover:underline">Case Search</button>
          <span className="text-slate-300">·</span>
          <button type="button" onClick={() => navigate('/ecourts/hc')} className="text-slate-500 hover:text-primary hover:underline">HC Home</button>
        </nav>
        <span className={`text-[11px] px-2.5 py-0.5 rounded-full font-bold uppercase ${
          d.status === 'Pending'
            ? 'bg-amber-100 text-amber-700 border border-amber-300'
            : 'bg-emerald-100 text-emerald-700 border border-emerald-300'
        } font-sans`}>
          {d.status || 'Unknown'}
        </span>
      </div>

      {/* ── Case title hero ──────────────────────────────────────────────── */}
      <header className="text-white py-5 px-6 text-center" style={{ backgroundColor: COURT_BLUE }}>
        <p className="font-mono text-white/60 text-xs mb-1">{fCino}</p>
        <h1 className="text-xl font-serif leading-snug max-w-4xl mx-auto">
          {d.case_type_name} {d.case_no}
        </h1>
        <p className="mt-1 text-white/70 text-sm font-sans">{d.high_court}{d.bench ? ` — ${d.bench}` : ''}</p>
        {d.next_hearing && (
          <p className="mt-1 text-yellow-200 text-xs font-sans">Next Hearing: {d.next_hearing}</p>
        )}
      </header>

      <main className="container mx-auto px-4 py-5 max-w-5xl">

        {/* ══ CASE DETAILS ════════════════════════════════════════════════ */}
        <Section label="Case Details">
          <table className="w-full border-collapse">
            <tbody>
              <tr>
                <th className={TH}>Filing Number</th>
                <td className={TD}>{d.case_no || '—'}</td>
                <th className={TH}>Filing Date</th>
                <td className={TD}>{d.filing_date || '—'}</td>
              </tr>
              <tr>
                <th className={TH}>Registration Number</th>
                <td className={TD}>{d.case_no || '—'}</td>
                <th className={TH}>Registration Date</th>
                <td className={TD}>{d.registration_date || '—'}</td>
              </tr>
              <tr>
                <th className={TH}>CNR Number</th>
                <td className="border border-black px-3 py-2 text-sm font-mono" style={{ color: COURT_BLUE }} colSpan={3}>
                  {fCino}
                </td>
              </tr>
            </tbody>
          </table>
        </Section>

        {/* ══ CASE STATUS ═════════════════════════════════════════════════ */}
        <Section label="Case Status">
          <table className="w-full border-collapse">
            <tbody>
              {d.next_hearing && (
                <tr>
                  <th className={`${TH} w-1/3`}>Next Hearing Date</th>
                  <td className={`${TD} font-semibold`} style={{ color: COURT_BLUE }} colSpan={3}>{d.next_hearing}</td>
                </tr>
              )}
              {d.stage_of_case && (
                <tr>
                  <th className={`${TH} w-1/3`}>Stage of Case</th>
                  <td className={`${TD} font-bold uppercase`} colSpan={3}>{d.stage_of_case}</td>
                </tr>
              )}
              {d.coram && (
                <tr>
                  <th className={`${TH} w-1/3`}>Coram</th>
                  <td className={TD} colSpan={3}>{d.coram}</td>
                </tr>
              )}
              {d.bench_type && (
                <tr>
                  <th className={`${TH} w-1/3`}>Bench Type</th>
                  <td className={TD} colSpan={3}>{d.bench_type}</td>
                </tr>
              )}
              {d.judicial_branch && (
                <tr>
                  <th className={`${TH} w-1/3`}>Judicial Branch</th>
                  <td className={`${TD} font-bold`} colSpan={3}>{d.judicial_branch}</td>
                </tr>
              )}
              <tr>
                <th className={TH}>State</th>
                <td className={TD}>{d.state || '—'}</td>
                <th className={TH}>District</th>
                <td className={`${TD} font-bold uppercase`}>{d.district || '—'}</td>
              </tr>
              {d.not_before_me && (
                <tr>
                  <th className={`${TH} w-1/3`}>Not Before Me</th>
                  <td className={`${TD} font-bold`} colSpan={3}>{d.not_before_me}</td>
                </tr>
              )}
            </tbody>
          </table>
        </Section>

        {/* ══ PETITIONER AND ADVOCATE ═════════════════════════════════════ */}
        <Section label="">
          <table className="w-full border-collapse">
            <tbody>
              <tr>
                <th colSpan={2} className={HDR} style={{ backgroundColor: COURT_BLUE }}>Petitioner and Advocate</th>
              </tr>
              <tr style={{ backgroundColor: '#dae8f5' }}>
                <td className="border border-black px-4 py-2 text-sm w-1/2 align-top">
                  <span className="font-bold">1) {d.petitioner || '—'}</span>
                </td>
                <td className="border border-black px-4 py-2 text-xs text-slate-600 w-1/2 align-top">
                  {d.petitioner_advocate || ''}
                </td>
              </tr>
            </tbody>
          </table>
        </Section>

        <Section label="">
          <table className="w-full border-collapse">
            <tbody>
              <tr>
                <th colSpan={2} className={HDR} style={{ backgroundColor: COURT_BLUE }}>Respondent and Advocate</th>
              </tr>
              <tr style={{ backgroundColor: '#ece4f7' }}>
                <td className="border border-black px-4 py-2 text-sm w-1/2 align-top">
                  <span className="font-bold">1) {d.respondent || '—'}</span>
                </td>
                <td className="border border-black px-4 py-2 text-xs text-slate-600 w-1/2 align-top">
                  {d.respondent_advocate || ''}
                </td>
              </tr>
            </tbody>
          </table>
        </Section>

        {/* ══ ACTS ════════════════════════════════════════════════════════ */}
        {d.acts?.length > 0 && (
          <Section label="Acts">
            <table className="w-full border-collapse" style={{ backgroundColor: '#fffbe6' }}>
              <thead>
                <tr>
                  <th className={TH}>Under Act(s)</th>
                  <th className={TH}>Under Section(s)</th>
                </tr>
              </thead>
              <tbody>
                {d.acts.map((act, i) => {
                  const { name, section } = parseAct(act);
                  return (
                    <tr key={i} style={{ backgroundColor: '#fffbe6' }}>
                      <td className={TD}>{name}</td>
                      <td className={TD}>{section}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Section>
        )}

        {/* ══ MAIN MATTERS ════════════════════════════════════════════════ */}
        {d.main_case_number && (
          <Section label="Main Matters">
            <table className="w-full border-collapse" style={{ backgroundColor: '#ede8f7' }}>
              <tbody>
                <tr style={{ backgroundColor: '#ede8f7' }}>
                  <th className={`${TH} w-1/3`} style={{ backgroundColor: '#d8d0f0' }}>Case Number</th>
                  <td className={`${TD} font-mono font-bold`} style={{ color: COURT_BLUE }}>{d.main_case_number}</td>
                </tr>
              </tbody>
            </table>
          </Section>
        )}

        {/* ══ IA DETAILS ══════════════════════════════════════════════════ */}
        {d.ia_details?.length > 0 && (
          <Section label="IA Details">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className={TH}>IA Number</th>
                  <th className={TH}>Party</th>
                  <th className={TH}>Date of Filing</th>
                  <th className={TH}>Next Date</th>
                  <th className={TH}>IA Status</th>
                </tr>
              </thead>
              <tbody>
                {d.ia_details.map((ia, i) => (
                  <tr key={i} style={{ backgroundColor: i % 2 === 0 ? '#f3eeff' : '#fff' }}>
                    <td className={`${TD} text-center font-mono`}>{ia.ia_number}</td>
                    <td className={`${TD} text-xs`}>{ia.party || '—'}</td>
                    <td className={`${TD} text-center font-mono`}>{ia.filing_date || '—'}</td>
                    <td className={`${TD} text-center font-mono`}>{ia.next_date || '—'}</td>
                    <td className={`${TD} text-center`}>{ia.status || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        )}

        {/* ══ HEARING HISTORY ═════════════════════════════════════════════ */}
        {d.hearing_history?.length > 0 && (
          <Section label="History of Case Hearing">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className={TH}>Cause List Type</th>
                  <th className={TH}>Judge</th>
                  <th className={TH}>Business On Date</th>
                  <th className={TH}>Hearing Date</th>
                  <th className={TH}>Purpose of Hearing</th>
                </tr>
              </thead>
              <tbody>
                {d.hearing_history.map((h, i) => (
                  <tr key={i} style={{ backgroundColor: i % 2 === 0 ? '#eaf5ea' : '#fff' }}>
                    <td className={`${TD} text-center text-xs`}>{h.cause_list_type || 'Daily List'}</td>
                    <td className={`${TD} text-xs`}>{h.judge || '—'}</td>
                    <td className={`${TD} text-center font-mono text-xs`}>{h.next_date || '—'}</td>
                    <td className={`${TD} text-center font-mono text-xs`}>{h.date || '—'}</td>
                    <td className={`${TD} text-center text-xs`}>{h.purpose || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        )}

        {/* ══ ORDERS ══════════════════════════════════════════════════════ */}
        {d.orders?.length > 0 && (
          <Section label="Orders">
            {downloadError && (
              <div className="mx-3 mt-2 rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 font-sans">
                {downloadError}
              </div>
            )}
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className={TH}>Order Number</th>
                  <th className={TH}>Order on</th>
                  <th className={TH}>Judge</th>
                  <th className={TH}>Order Date</th>
                  <th className={TH}>Order Details</th>
                </tr>
              </thead>
              <tbody>
                {d.orders.map((o, i) => (
                  <tr key={i} style={{ backgroundColor: i % 2 === 0 ? '#fff' : '#f7f7f7' }}>
                    <td className={`${TD} text-center`}>{o.order_number || (i + 1)}</td>
                    <td className={`${TD} text-center font-mono text-xs`}>{d.case_no}</td>
                    <td className={`${TD} text-xs`}>{o.judge || '—'}</td>
                    <td className={`${TD} text-center font-mono text-xs`}>{o.date}</td>
                    <td className={`${TD} text-center`}>
                      {o.document_url ? (
                        <button
                          type="button"
                          onClick={() => handlePdfDownload(o.document_url, i)}
                          disabled={downloadingIdx === i}
                          className="font-sans text-[11px] font-semibold underline disabled:opacity-60 disabled:cursor-wait"
                          style={{ color: COURT_BLUE }}
                        >
                          {downloadingIdx === i ? '…' : '_View'}
                        </button>
                      ) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        )}

        {/* ══ DOCUMENT DETAILS ════════════════════════════════════════════ */}
        {d.documents?.length > 0 && (
          <Section label="Document Details">
            <table className="w-full border-collapse" style={{ backgroundColor: '#fffbe6' }}>
              <thead>
                <tr>
                  <th className={TH}>Sr. No.</th>
                  <th className={TH}>Document No.</th>
                  <th className={TH}>Date of Receiving</th>
                  <th className={TH}>Filed by</th>
                  <th className={TH}>Name of Advocate</th>
                  <th className={TH}>Document Filed</th>
                </tr>
              </thead>
              <tbody>
                {d.documents.map((doc, i) => (
                  <tr key={i} style={{ backgroundColor: '#fffbe6' }}>
                    <td className={`${TD} text-center`}>{doc.sr_no}</td>
                    <td className={`${TD} text-center`}>{doc.document_no || '—'}</td>
                    <td className={`${TD} text-center font-mono text-xs`}>{doc.date_of_receiving || '—'}</td>
                    <td className={TD}>{doc.filed_by || '—'}</td>
                    <td className={TD}>{doc.advocate_name || '—'}</td>
                    <td className={TD}>{doc.document_filed || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        )}

        {/* ══ OBJECTION ═══════════════════════════════════════════════════ */}
        {d.objections?.length > 0 && (
          <Section label="Objection">
            <table className="w-full border-collapse" style={{ backgroundColor: '#f4f0ff' }}>
              <thead>
                <tr>
                  <th className={TH}>Sr.No.</th>
                  <th className={TH}>Scrutiny Date</th>
                  <th className={TH}>Objection</th>
                  <th className={TH}>Objection Compliance Date</th>
                  <th className={TH}>Receipt Date</th>
                </tr>
              </thead>
              <tbody>
                {d.objections.map((ob, i) => (
                  <tr key={i} style={{ backgroundColor: '#f4f0ff' }}>
                    <td className={`${TD} text-center`}>{ob.sr_no}</td>
                    <td className={`${TD} text-center font-mono text-xs`}>{ob.scrutiny_date || '—'}</td>
                    <td className={TD} style={{ color: ob.objection?.toLowerCase().includes('complied') ? '#15803d' : 'inherit', fontWeight: ob.objection?.toLowerCase().includes('complied') ? 700 : 400 }}>
                      {ob.objection || '—'}
                    </td>
                    <td className={`${TD} text-center font-mono text-xs`}>{ob.compliance_date || '—'}</td>
                    <td className={`${TD} text-center font-mono text-xs`}>{ob.receipt_date || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        )}

        {/* ══ LINKED CASES ════════════════════════════════════════════════ */}
        {d.linked_cases?.length > 0 && (
          <Section label={`Linked Cases (${d.linked_cases.length})`}>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className={TH}>Filing Number</th>
                  <th className={TH}>Case Number</th>
                  <th className={TH}>Main / IA</th>
                  <th className={TH}>Status</th>
                </tr>
              </thead>
              <tbody>
                {d.linked_cases.map((lc, i) => (
                  <tr key={i} style={{ backgroundColor: i % 2 === 0 ? '#fff' : '#f5f5f5' }}>
                    <td className={`${TD} text-center font-mono text-xs`}>{lc.filing_number}</td>
                    <td className={`${TD} text-center font-mono text-xs`}>{lc.case_number || '—'}</td>
                    <td className={`${TD} text-center`}>
                      {lc.is_main ? <span className="font-bold" style={{ color: COURT_BLUE }}>Main</span> : '—'}
                    </td>
                    <td className={`${TD} text-center`}>{lc.status || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        )}

        {/* ══ SUBORDINATE COURT ═══════════════════════════════════════════ */}
        {d.subordinate_court && (
          <Section label="Subordinate Court Information">
            <table className="w-full border-collapse">
              <tbody>
                {d.subordinate_court.court_number_and_name && (
                  <tr>
                    <th className={`${TH} w-1/3`}>Court Number and Name</th>
                    <td className={TD}>{d.subordinate_court.court_number_and_name}</td>
                  </tr>
                )}
                {d.subordinate_court.case_number_and_year && (
                  <tr>
                    <th className={`${TH} w-1/3`}>Case Number and Year</th>
                    <td className={`${TD} font-mono`}>{d.subordinate_court.case_number_and_year}</td>
                  </tr>
                )}
                {d.subordinate_court.case_decision_date && (
                  <tr>
                    <th className={`${TH} w-1/3`}>Case Decision Date</th>
                    <td className={`${TD} font-mono`}>{d.subordinate_court.case_decision_date}</td>
                  </tr>
                )}
                {(d.subordinate_court.state || d.subordinate_court.district) && (
                  <tr>
                    <th className={`${TH} w-1/3`}>State / District</th>
                    <td className={TD}>{[d.subordinate_court.state, d.subordinate_court.district].filter(Boolean).join(' / ')}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </Section>
        )}

      </main>
    </div>
  );
}
