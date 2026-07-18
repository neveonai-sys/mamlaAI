import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import { searchSCIByDiary, downloadSCIPdf } from './apiSCI';

const COURT_BLUE = '#0b3260';

function Section({ label, children }) {
  return (
    <div className="rounded-[24px] border border-primary/10 bg-white overflow-hidden mb-4 shadow-sm">
      {label && (
        <div className="text-white font-bold text-center py-2 px-4 text-xs tracking-widest uppercase" style={{ backgroundColor: COURT_BLUE }}>
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

// id is "<diary_no>_<diary_year>"
function parseId(id) {
  const idx = id.lastIndexOf('_');
  if (idx === -1) return { diary_no: id, diary_year: '' };
  return { diary_no: id.slice(0, idx), diary_year: id.slice(idx + 1) };
}

export default function SCICaseDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [caseData, setCaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!id) return;
    let active = true;
    setLoading(true);
    setError('');
    dispatch(beginBlocking({ message: 'Loading case details...' }));
    const { diary_no, diary_year } = parseId(id);
    searchSCIByDiary({ diary_no, diary_year })
      .then((res) => { if (active) setCaseData(res.data?.cases?.[0] || res.data); })
      .catch((err) => {
        if (!active) return;
        setError(err.response?.data?.detail || err.response?.data?.error || 'Unable to fetch case details.');
      })
      .finally(() => { if (active) { setLoading(false); dispatch(stopBlocking()); } });
    return () => { active = false; };
  }, [id]);

  async function handleDownload(docUrl) {
    setDownloading(true);
    try {
      const resp = await downloadSCIPdf(docUrl);
      const blob = new Blob([resp.data], { type: 'application/pdf' });
      const objUrl = URL.createObjectURL(blob);
      window.open(objUrl, '_blank');
      setTimeout(() => URL.revokeObjectURL(objUrl), 60000);
    } catch (err) {
      setError('PDF download failed. Please try again.');
    } finally {
      setDownloading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <span className="material-symbols-outlined text-primary text-4xl animate-spin">progress_activity</span>
        <p className="text-sm text-slate-500">Fetching case details from the Supreme Court portal…</p>
        <p className="text-xs text-slate-400">This may take 10–30 seconds (CAPTCHA solve required).</p>
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
          <button type="button" onClick={() => navigate('/ecourts/sci')} className="text-sm text-slate-500 hover:text-primary hover:underline">Supreme Court Home</button>
        </div>
        <div className="card p-8 text-center">
          <span className="material-symbols-outlined text-slate-300 text-5xl block mb-3">gavel</span>
          <p className="text-slate-500">{error || 'Case data not available.'}</p>
        </div>
      </div>
    );
  }

  const d = caseData;

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button type="button" onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-primary hover:underline">
          <span className="material-symbols-outlined text-sm">arrow_back</span> Back
        </button>
        <span className="text-slate-300">·</span>
        <button type="button" onClick={() => navigate('/ecourts/sci/case-status')} className="text-sm text-slate-500 hover:text-primary hover:underline">Case Search</button>
        <span className="text-slate-300">·</span>
        <button type="button" onClick={() => navigate('/ecourts/sci')} className="text-sm text-slate-500 hover:text-primary hover:underline">Supreme Court Home</button>
      </div>

      <header className="text-white py-5 px-6 text-center rounded-[24px] mb-6" style={{ backgroundColor: COURT_BLUE }}>
        <p className="font-mono text-white/60 text-xs mb-1">
          {d.diary_no ? `Diary No. ${d.diary_no}/${d.diary_year}` : ''}
          {d.case_no ? ` · ${d.case_no}/${d.case_year}` : ''}
        </p>
        <h1 className="text-xl font-serif leading-snug max-w-4xl mx-auto">
          {d.petitioner || 'Case'} {d.respondent ? `vs ${d.respondent}` : ''}
        </h1>
        {d.status && <p className="mt-1 text-white/70 text-sm">{d.status}</p>}
      </header>

      <Section label="Case Details">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Diary Number" value={d.diary_no ? `${d.diary_no}/${d.diary_year}` : null} />
          <Field label="Case Number" value={d.case_no ? `${d.case_no}/${d.case_year}` : null} />
          <Field label="Case Type" value={d.case_type} />
          <Field label="Filing Date" value={d.filing_date} />
          <Field label="Status" value={d.status} />
          <Field label="Next Hearing" value={d.next_hearing} />
        </div>
      </Section>

      {(d.petitioner || d.petitioner_advocate) && (
        <Section label="Petitioner">
          <Field label="Petitioner" value={d.petitioner} />
          <Field label="Advocate" value={d.petitioner_advocate} />
        </Section>
      )}

      {(d.respondent || d.respondent_advocate) && (
        <Section label="Respondent">
          <Field label="Respondent" value={d.respondent} />
          <Field label="Advocate" value={d.respondent_advocate} />
        </Section>
      )}

      {d.hearing_history?.length > 0 && (
        <Section label="Hearing History">
          <div className="flex flex-col gap-2">
            {d.hearing_history.map((h, i) => (
              <div key={i} className="flex items-center justify-between rounded-xl border border-primary/10 bg-background-light px-4 py-2 text-sm">
                <span className="font-mono text-xs text-slate-500">{h.date}</span>
                <span className="text-slate-600">{h.purpose || '—'}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {d.orders?.length > 0 && (
        <Section label="Orders">
          <div className="flex flex-col gap-2">
            {d.orders.map((o, i) => (
              <div key={i} className="flex items-center justify-between rounded-xl border border-primary/10 bg-background-light px-4 py-2 text-sm">
                <span className="font-mono text-xs text-slate-500">{o.date || o.order_date}</span>
                {o.doc_url ? (
                  <button
                    type="button"
                    onClick={() => handleDownload(o.doc_url)}
                    disabled={downloading}
                    className="text-xs font-semibold underline disabled:opacity-60"
                    style={{ color: COURT_BLUE }}
                  >
                    {downloading ? '…' : 'View PDF'}
                  </button>
                ) : <span className="text-slate-400">—</span>}
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}
