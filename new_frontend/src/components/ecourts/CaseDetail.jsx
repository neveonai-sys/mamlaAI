import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import apiClient from '../../services/api';

function DetailRow({ label, value, mono = false }) {
  if (!value) return null;
  return (
    <div className="grid grid-cols-3 gap-3 py-3 border-b border-primary/5 last:border-b-0">
      <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">{label}</p>
      <p className={`col-span-2 text-sm text-ink ${mono ? 'font-mono' : 'font-medium'}`}>{value}</p>
    </div>
  );
}

function HearingRow({ h }) {
  const dateObj = h.date ? new Date(h.date) : null;
  const nextDateObj = h.next_date ? new Date(h.next_date) : null;
  return (
    <div className="flex items-start gap-4 py-3 border-b border-primary/5 last:border-b-0">
      <div className="text-center min-w-[48px]">
        <p className="text-lg font-black text-primary leading-none">
          {dateObj ? dateObj.getDate() : '—'}
        </p>
        <p className="text-[10px] text-slate-400">
          {dateObj ? dateObj.toLocaleDateString('en-IN', { month: 'short', year: '2-digit' }) : ''}
        </p>
      </div>
      <div>
        <p className="text-sm font-semibold text-ink">{h.purpose || 'Hearing'}</p>
        {h.order_text && (
          <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{h.order_text}</p>
        )}
        {nextDateObj && (
          <p className="text-xs text-primary font-semibold mt-1">
            Next: {nextDateObj.toLocaleDateString('en-IN')}
          </p>
        )}
      </div>
    </div>
  );
}

export default function CaseDetail() {
  const { cnr } = useParams();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!cnr) return;
    setLoading(true);
    apiClient.get(`ecourts/case/${encodeURIComponent(cnr)}/`)
      .then((r) => setCaseData(r.data))
      .catch(() => setError('Case not found or data unavailable.'))
      .finally(() => setLoading(false));
  }, [cnr]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="material-symbols-outlined text-primary text-4xl animate-spin">progress_activity</span>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="p-8 max-w-3xl">
        <Link to="/ecourts/case-search" className="flex items-center gap-1 text-sm text-primary mb-6 hover:underline">
          <span className="material-symbols-outlined text-sm">arrow_back</span>
          Back to Search
        </Link>
        <div className="card p-8 text-center">
          <span className="material-symbols-outlined text-slate-300 text-5xl block mb-3">gavel</span>
          <p className="text-slate-500">{error || 'Case data not available.'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl">
      {/* Back */}
      <Link to="/ecourts/case-search" className="flex items-center gap-1 text-sm text-primary mb-5 hover:underline w-fit">
        <span className="material-symbols-outlined text-sm">arrow_back</span>
        Back to Search
      </Link>

      {/* Header */}
      <div className="card p-6 mb-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-xs px-2 py-0.5 rounded font-bold uppercase ${
                caseData.status === 'Disposed'
                  ? 'bg-slate-100 text-slate-500'
                  : 'bg-emerald-100 text-emerald-600'
              }`}>
                {caseData.status ?? 'Active'}
              </span>
              <span className="text-xs font-mono text-slate-400">{cnr}</span>
            </div>
            <h1 className="text-xl font-black text-ink">{caseData.case_title || caseData.title}</h1>
          </div>
          {caseData.next_hearing_date && (
            <div className="text-right flex-shrink-0">
              <p className="text-[10px] text-slate-400 uppercase tracking-wider">Next Hearing</p>
              <p className="font-bold text-primary">
                {new Date(caseData.next_hearing_date).toLocaleDateString('en-IN', {
                  day: 'numeric', month: 'short', year: 'numeric',
                })}
              </p>
            </div>
          )}
        </div>

        <div className="divide-y divide-primary/5">
          <DetailRow label="Court" value={caseData.court || caseData.court_name} />
          <DetailRow label="Case Type" value={`${caseData.case_type} ${caseData.case_number}/${caseData.year}`} />
          <DetailRow label="Filing Date" value={caseData.filing_date ? new Date(caseData.filing_date).toLocaleDateString('en-IN') : null} />
          <DetailRow label="Petitioner" value={caseData.petitioner} />
          <DetailRow label="Respondent" value={caseData.respondent} />
          <DetailRow label="Petitioner Advocate" value={caseData.petitioner_advocate} />
          <DetailRow label="Respondent Advocate" value={caseData.respondent_advocate} />
          <DetailRow label="Act / Section" value={caseData.act} />
          <DetailRow label="Stage" value={caseData.stage || caseData.case_stage} />
        </div>
      </div>

      {/* Hearing history */}
      {caseData.hearings && caseData.hearings.length > 0 && (
        <div className="card p-6">
          <h3 className="font-bold text-ink mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary">history</span>
            Hearing History ({caseData.hearings.length})
          </h3>
          <div className="divide-y divide-primary/5">
            {caseData.hearings.map((h, i) => (
              <HearingRow key={i} h={h} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
