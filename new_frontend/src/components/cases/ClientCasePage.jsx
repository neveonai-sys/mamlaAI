/**
 * ClientCasePage — /my-case
 * Read-only portal for clients: see their case(s), shared notes, upcoming hearings,
 * and a link to their shared documents.
 *
 * Backend already filters:
 *  - listCases()         → only cases where user_id in client_ids
 *  - listCaseNotes()     → only visibility:'shared' notes for client role
 *  - listHearingNotes()  → accessible via the cases the client belongs to
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  listCases,
  listCaseNotes,
  listHearingNotes,
} from '../../services/casesApi';

const STATUS_STYLE = {
  Active:   'bg-emerald-100 text-emerald-800',
  Settled:  'bg-sky-100 text-sky-800',
  Disposed: 'bg-slate-100 text-slate-700',
  Appeal:   'bg-amber-100 text-amber-800',
  Archived: 'bg-rose-100 text-rose-700',
};

function StatusBadge({ status }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_STYLE[status] || 'bg-slate-100 text-slate-600'}`}>
      {status}
    </span>
  );
}

function fmtDate(v) {
  if (!v) return '—';
  try { return new Date(v).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); }
  catch { return v; }
}

// ─── Per-case detail panel ────────────────────────────────────────────────────
function CasePanel({ c }) {
  const navigate = useNavigate();
  const [notes, setNotes] = useState([]);
  const [hearings, setHearings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState('overview');

  useEffect(() => {
    setLoading(true);
    Promise.allSettled([
      listCaseNotes(c._id),
      listHearingNotes(c._id),
    ]).then(([notesRes, hearingsRes]) => {
      if (notesRes.status === 'fulfilled') {
        // Backend already filters to shared-only for client role
        setNotes(notesRes.value.data?.case_notes ?? []);
      }
      if (hearingsRes.status === 'fulfilled') {
        const all = hearingsRes.value.data?.hearing_notes ?? [];
        // Show only upcoming hearings (next_date >= today) or recent outcomes
        const today = new Date().toISOString().slice(0, 10);
        const upcoming = all
          .filter(h => h.next_date && h.next_date >= today)
          .sort((a, b) => a.next_date.localeCompare(b.next_date));
        setHearings(upcoming);
      }
    }).finally(() => setLoading(false));
  }, [c._id]);

  const SECTIONS = [
    { id: 'overview', label: 'Overview', icon: 'info' },
    { id: 'updates',  label: `Updates (${notes.length})`, icon: 'notifications' },
    { id: 'hearings', label: `Hearings (${hearings.length})`, icon: 'gavel' },
  ];

  return (
    <div className="rounded-2xl border border-primary/10 bg-ivory shadow-subtle overflow-hidden">
      {/* Case header */}
      <div className="px-5 py-4 border-b border-slate-100">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-ink truncate">{c.title}</h2>
            {c.case_ref && <p className="text-xs text-graphite/60 mt-0.5">{c.case_ref}</p>}
            <div className="mt-2 flex flex-wrap gap-2 items-center">
              <StatusBadge status={c.status} />
              {c.stage && (
                <span className="text-xs text-graphite border border-slate-200 rounded px-1.5 py-0.5">{c.stage}</span>
              )}
              {c.case_type && (
                <span className="text-xs text-graphite/70">{c.case_type}</span>
              )}
            </div>
          </div>
          <button
            onClick={() => navigate('/chat')}
            title="Discuss case documents"
            className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-primary/30 text-primary text-xs font-semibold hover:bg-primary/5 transition"
          >
            <span className="material-symbols-outlined text-sm">forum</span>
            Chat
          </button>
        </div>
        {c.next_hearing && (
          <div className="mt-3 flex items-center gap-2 rounded-xl bg-sky-50 border border-sky-200 px-3 py-2 text-sm text-sky-700">
            <span className="material-symbols-outlined text-base">event</span>
            <span>Next hearing: <strong>{fmtDate(c.next_hearing)}</strong></span>
          </div>
        )}
        {c.brief && (
          <p className="mt-3 text-xs text-graphite/70 line-clamp-2 leading-relaxed">{c.brief}</p>
        )}
      </div>

      {/* Section nav */}
      <div className="flex gap-1 px-4 pt-3 pb-0">
        {SECTIONS.map(s => (
          <button key={s.id} onClick={() => setActiveSection(s.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeSection === s.id
                ? 'bg-primary text-white'
                : 'text-graphite hover:bg-primary/5'
            }`}>
            <span className="material-symbols-outlined text-sm">{s.icon}</span>
            {s.label}
          </button>
        ))}
      </div>

      {/* Section content */}
      <div className="p-4">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <span className="material-symbols-outlined animate-spin text-primary text-2xl">progress_activity</span>
          </div>
        ) : (
          <>
            {activeSection === 'overview' && (
              <div className="space-y-3 text-sm">
                {c.court?.state && (
                  <div className="flex items-start gap-2 text-graphite">
                    <span className="material-symbols-outlined text-sm text-primary/60 mt-0.5">account_balance</span>
                    <span>{[c.court.court, c.court.district, c.court.state].filter(Boolean).join(', ')}</span>
                  </div>
                )}
                {c.filing_date && (
                  <div className="flex items-start gap-2 text-graphite">
                    <span className="material-symbols-outlined text-sm text-primary/60 mt-0.5">calendar_month</span>
                    <span>Filed: {fmtDate(c.filing_date)}</span>
                  </div>
                )}
                {c.cnr && (
                  <div className="flex items-start gap-2 text-graphite">
                    <span className="material-symbols-outlined text-sm text-primary/60 mt-0.5">tag</span>
                    <span>CNR: <span className="font-mono text-xs">{c.cnr}</span></span>
                  </div>
                )}
                {!c.court?.state && !c.filing_date && !c.cnr && (
                  <p className="text-graphite/50 text-xs py-4 text-center">No additional details available.</p>
                )}
              </div>
            )}

            {activeSection === 'updates' && (
              <div className="space-y-3">
                {notes.length === 0 ? (
                  <p className="text-xs text-graphite/50 text-center py-6">No updates from your lawyer yet.</p>
                ) : (
                  notes.map(n => (
                    <div key={n._id} className="rounded-xl border border-slate-100 bg-white p-3">
                      <div className="flex items-center justify-between mb-1 gap-2">
                        <span className="text-xs font-semibold text-ink">{n.author_role || 'Update'}</span>
                        <span className="text-[11px] text-graphite/50">{fmtDate(n.created_at)}</span>
                      </div>
                      <p className="text-xs text-graphite leading-relaxed whitespace-pre-wrap">{n.content}</p>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeSection === 'hearings' && (
              <div className="space-y-3">
                {hearings.length === 0 ? (
                  <p className="text-xs text-graphite/50 text-center py-6">No upcoming hearing dates on record.</p>
                ) : (
                  hearings.map(h => (
                    <div key={h._id} className="rounded-xl border border-sky-100 bg-sky-50 p-3 flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-sky-700">{fmtDate(h.next_date)}</p>
                        {h.purpose && <p className="text-xs text-sky-600/80 mt-0.5">{h.purpose}</p>}
                      </div>
                      <span className="material-symbols-outlined text-sky-400 text-base">gavel</span>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ─── Main page ─────────────────────────────────────────────────────────────────
export default function ClientCasePage() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const res = await listCases({});
      setCases(res.data?.cases ?? []);
    } catch (e) {
      setError(e?.response?.data?.error || 'Failed to load your case.');
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-ink flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-2xl">folder_open</span>
          My Case
        </h1>
        <p className="text-sm text-graphite/70 mt-1">Track your case status, updates from your lawyer, and upcoming hearing dates.</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <span className="material-symbols-outlined animate-spin text-primary text-4xl">progress_activity</span>
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 text-red-700 p-4 text-sm">{error}</div>
      ) : cases.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center text-graphite/60 gap-4">
          <span className="material-symbols-outlined text-5xl text-primary/30">folder</span>
          <p className="text-base font-medium">No case found.</p>
          <p className="text-sm">Your lawyer hasn&apos;t linked you to a case yet. Contact your lawyer for more details.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {cases.map(c => <CasePanel key={c._id} c={c} />)}
        </div>
      )}
    </div>
  );
}
