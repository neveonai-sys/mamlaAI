import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import { searchCATByNumber } from './apiCAT';

const TRIBUNAL_BLUE = '#0b3260';

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

// id is "<bench>_<case_type>_<case_no>_<year>"
function parseId(id) {
  const parts = id.split('_');
  if (parts.length < 4) return { bench: id, case_type: '', case_no: '', year: '' };
  const [bench, case_type, case_no, year] = parts;
  return { bench, case_type, case_no, year };
}

export default function CATCaseDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    let active = true;
    setLoading(true);
    setError('');
    dispatch(beginBlocking({ message: 'Loading case details...' }));
    const { bench, case_type, case_no, year } = parseId(id);
    searchCATByNumber({ bench, case_type, case_no, year })
      .then((res) => { if (active) setCaseData(res.data); })
      .catch((err) => {
        if (!active) return;
        setError(err.response?.data?.detail || err.response?.data?.error || 'Unable to fetch case details.');
      })
      .finally(() => { if (active) { setLoading(false); dispatch(stopBlocking()); } });
    return () => { active = false; };
  }, [id]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <span className="material-symbols-outlined text-primary text-4xl animate-spin">progress_activity</span>
        <p className="text-sm text-slate-500">Fetching case details from the CAT portal…</p>
      </div>
    );
  }

  if (error || !caseData || caseData.error) {
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
          <p className="text-slate-500">{error || caseData?.error || 'Case data not available.'}</p>
        </div>
      </div>
    );
  }

  const d = caseData;
  const details = d.case_details || {};
  const history = d.case_history || [];
  const orders = d.orders || [];

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button type="button" onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-primary hover:underline">
          <span className="material-symbols-outlined text-sm">arrow_back</span> Back
        </button>
        <span className="text-slate-300">·</span>
        <button type="button" onClick={() => navigate('/ecourts/cat/case-status')} className="text-sm text-slate-500 hover:text-primary hover:underline">Case Search</button>
        <span className="text-slate-300">·</span>
        <button type="button" onClick={() => navigate('/ecourts/cat')} className="text-sm text-slate-500 hover:text-primary hover:underline">CAT Home</button>
      </div>

      <header className="text-white py-5 px-6 text-center rounded-[24px] mb-6" style={{ backgroundColor: TRIBUNAL_BLUE }}>
        <p className="font-mono text-white/60 text-xs mb-1">
          {d.bench} · {d.case_type}/{d.case_no}/{d.year}
        </p>
        <h1 className="text-xl font-serif leading-snug max-w-4xl mx-auto">
          {details.Applicant || 'Case'} {details.Respondent ? `vs ${details.Respondent}` : ''}
        </h1>
        {details.Status && <p className="mt-1 text-white/70 text-sm">{details.Status}</p>}
      </header>

      {Object.keys(details).length > 0 && (
        <Section label="Case Details">
          <div className="grid gap-4 sm:grid-cols-2">
            {Object.entries(details).map(([key, value]) => (
              <Field key={key} label={key} value={value} />
            ))}
          </div>
        </Section>
      )}

      {history.length > 0 && (
        <Section label="Hearing History">
          <div className="flex flex-col gap-2">
            {history.map((h, i) => (
              <div key={i} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-primary/10 bg-background-light px-4 py-2 text-sm">
                <span className="text-slate-600">
                  {Object.entries(h)
                    .filter(([k]) => k !== 'order_pdf_url')
                    .map(([, v]) => v)
                    .filter(Boolean)
                    .join(' · ')}
                </span>
                {h.order_pdf_url && (
                  <a href={h.order_pdf_url} target="_blank" rel="noreferrer" className="text-xs font-semibold underline" style={{ color: TRIBUNAL_BLUE }}>
                    View PDF
                  </a>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {orders.length > 0 && (
        <Section label="Orders">
          <div className="flex flex-col gap-2">
            {orders.map((o, i) => (
              <div key={i} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-primary/10 bg-background-light px-4 py-2 text-sm">
                <span className="text-slate-600">
                  {Object.entries(o)
                    .filter(([k]) => k !== 'pdf_url')
                    .map(([, v]) => v)
                    .filter(Boolean)
                    .join(' · ')}
                </span>
                {o.pdf_url ? (
                  <a href={o.pdf_url} target="_blank" rel="noreferrer" className="text-xs font-semibold underline" style={{ color: TRIBUNAL_BLUE }}>
                    View PDF
                  </a>
                ) : <span className="text-slate-400">—</span>}
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}
