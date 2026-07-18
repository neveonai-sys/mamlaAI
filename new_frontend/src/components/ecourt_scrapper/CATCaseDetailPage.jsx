import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import { searchCATCaseDetail } from './apiCAT';

const TRIBUNAL_BLUE = '#0b3260';

function statusClasses(status) {
  const s = (status || '').toLowerCase();
  if (s.includes('dispos')) return 'bg-emerald-100 text-emerald-700 border-emerald-300';
  if (s.includes('pend')) return 'bg-amber-100 text-amber-700 border-amber-300';
  return 'bg-slate-100 text-slate-600 border-slate-300';
}

function Section({ label, children }) {
  return (
    <div className="rounded-[24px] border border-primary/10 bg-white overflow-hidden mb-4 shadow-sm">
      {label && (
        <div className="text-white font-bold text-center py-2 px-4 text-xs tracking-widest uppercase" style={{ backgroundColor: TRIBUNAL_BLUE }}>
          {label}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

function Field({ label, value }) {
  if (!value) return null;
  return (
    <div>
      <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">{label}</p>
      <p className="mt-1 text-sm text-ink">{value}</p>
    </div>
  );
}

function HighlightField({ label, value, tone = 'primary' }) {
  if (!value) return null;
  const toneClasses = tone === 'amber'
    ? 'border-amber-200 bg-amber-50 text-amber-900'
    : 'border-primary/20 bg-primary/5 text-ink';
  return (
    <div className={`rounded-2xl border px-4 py-3 ${toneClasses}`}>
      <p className="text-[10px] font-black uppercase tracking-[0.2em] opacity-60">{label}</p>
      <p className="mt-1 text-sm font-bold">{value}</p>
    </div>
  );
}

function PartyColumn({ side, names, advocates, address }) {
  const isPetitioner = side === 'petitioner';
  const railColor = isPetitioner ? 'border-l-primary' : 'border-l-amber-400';
  const label = isPetitioner ? 'Petitioner(s)' : 'Respondent(s)';
  const labelColor = isPetitioner ? 'text-primary' : 'text-amber-600';
  return (
    <div className={`flex-1 border-l-4 ${railColor} pl-4`}>
      <p className={`text-[11px] font-black uppercase tracking-[0.2em] ${labelColor}`}>{label}</p>
      <div className="mt-2 flex flex-col gap-1">
        {(names || []).map((n, i) => (
          <p key={i} className="text-sm font-semibold text-ink">{n}</p>
        ))}
      </div>
      {address && <p className="mt-2 whitespace-pre-line text-xs text-slate-500">{address}</p>}
      {advocates?.length > 0 && (
        <div className="mt-3 border-t border-primary/10 pt-2">
          <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Advocate(s)</p>
          <div className="mt-1 flex flex-col gap-0.5">
            {advocates.map((n, i) => (
              <p key={i} className="text-xs text-slate-600">{n}</p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// A generic best-effort row renderer for the reference/connected/filing
// sub-tables — their column sets vary, so just join whatever's present.
// "Daily Order" is dropped from the text join since its value is always the
// literal word "View" — daily_order_url (the link it actually points to) is
// rendered as a real action instead.
function SubTableRow({ row }) {
  const { daily_order_url, 'Daily Order': _omit, ...rest } = row;
  const text = Object.values(rest).filter(Boolean).join(' · ');
  if (!text && !daily_order_url) return null;
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-primary/10 bg-background-light px-4 py-2 text-sm text-slate-600">
      <span>{text}</span>
      {daily_order_url && (
        <a
          href={daily_order_url}
          target="_blank"
          rel="noreferrer"
          className="shrink-0 text-xs font-semibold text-primary hover:underline"
        >
          View Orders ↗
        </a>
      )}
    </div>
  );
}

export default function CATCaseDetailPage() {
  const { id: token } = useParams();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) return;
    let active = true;
    setLoading(true);
    setError('');
    dispatch(beginBlocking({ message: 'Loading case details...' }));
    searchCATCaseDetail(token)
      .then((res) => { if (active) setCaseData(res.data?.case_details || null); })
      .catch((err) => {
        if (!active) return;
        setError(err.response?.data?.detail || err.response?.data?.error || 'Unable to fetch case details.');
      })
      .finally(() => { if (active) setLoading(false); dispatch(stopBlocking()); });
    return () => { active = false; };
  }, [token]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <span className="material-symbols-outlined text-primary text-4xl animate-spin">progress_activity</span>
        <p className="text-sm text-slate-500">Fetching case details from the CAT portal…</p>
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
          <button type="button" onClick={() => navigate('/ecourts/cat')} className="text-sm text-slate-500 hover:text-primary hover:underline">CAT Home</button>
        </div>
        <div className="card p-8 text-center">
          <span className="material-symbols-outlined text-slate-300 text-5xl block mb-3">gavel</span>
          <p className="text-slate-500">{error || 'Case data not available.'}</p>
        </div>
      </div>
    );
  }

  const d = caseData;
  const title = [d.applicant, d.respondent].filter(Boolean).join(' vs ') || 'Case';

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <button type="button" onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-primary hover:underline">
            <span className="material-symbols-outlined text-sm">arrow_back</span> Back
          </button>
          <span className="text-slate-300">·</span>
          <button type="button" onClick={() => navigate('/ecourts/cat/case-status')} className="text-sm text-slate-500 hover:text-primary hover:underline">Case Search</button>
          <span className="text-slate-300">·</span>
          <button type="button" onClick={() => navigate('/ecourts/cat')} className="text-sm text-slate-500 hover:text-primary hover:underline">CAT Home</button>
        </div>
        {d.status_stage && (
          <span className={`rounded-full border px-3 py-1 text-[11px] font-bold uppercase tracking-wide ${statusClasses(d.status_stage)}`}>
            {d.status_stage}
          </span>
        )}
      </div>

      <header className="text-white py-5 px-6 text-center rounded-[24px] mb-6" style={{ backgroundColor: TRIBUNAL_BLUE }}>
        <p className="font-mono text-white/60 text-xs mb-1">
          {d.diary_no ? `Diary No. ${d.diary_no}` : ''}{d.case_number ? ` · ${d.case_number}` : ''}
        </p>
        <h1 className="text-xl font-serif leading-snug max-w-4xl mx-auto">{title}</h1>
        {d.present_next_listed_on && (
          <p className="mt-2 inline-block rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-amber-200">
            Next Listing: {d.present_next_listed_on}
          </p>
        )}
      </header>

      <Section label="Case Details">
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Location" value={d.location} />
          <Field label="Case Number" value={d.case_number} />
          <Field label="Court No." value={d.in_the_court_no} />
          <Field label="Filing Date" value={d.filing_date} />
          <Field label="Subject" value={d.subject} />
          <Field label="Court Fee" value={d.court_fee ? `${d.court_fee}${d.group ? ` (Group ${d.group})` : ''}` : ''} />
        </div>
        {(d.status_stage || d.present_next_listed_on || d.notification_date) && (
          <div className="mt-5 grid gap-3 border-t border-primary/10 pt-5 sm:grid-cols-3">
            <HighlightField label="Status / Stage" value={d.status_stage} />
            <HighlightField label="Present / Next Listed On" value={d.present_next_listed_on} tone="amber" />
            <HighlightField label="Notification Date" value={d.notification_date} />
          </div>
        )}
      </Section>

      {(d.petitioners?.length > 0 || d.respondents?.length > 0) && (
        <Section label="Parties">
          <div className="flex flex-col gap-6 sm:flex-row">
            {d.petitioners?.length > 0 && (
              <PartyColumn side="petitioner" names={d.petitioners} advocates={d.petitioner_advocates} address={d.petitioner_address} />
            )}
            {d.respondents?.length > 0 && (
              <PartyColumn side="respondent" names={d.respondents} advocates={d.respondent_advocates} address={d.respondent_address} />
            )}
          </div>
        </Section>
      )}

      {d.reference_cases?.length > 0 && (
        <Section label="Reference Case Details">
          <div className="flex flex-col gap-2">
            {d.reference_cases.map((rc, i) => <SubTableRow key={i} row={rc} />)}
          </div>
        </Section>
      )}

      {d.connected_cases?.length > 0 && (
        <Section label="Connected Case Details">
          <div className="flex flex-col gap-2">
            {d.connected_cases.map((cc, i) => <SubTableRow key={i} row={cc} />)}
          </div>
        </Section>
      )}

      {d.document_filings?.length > 0 && (
        <Section label="Document Filing Details">
          <div className="flex flex-col gap-2">
            {d.document_filings.map((doc, i) => <SubTableRow key={i} row={doc} />)}
          </div>
        </Section>
      )}
    </div>
  );
}
