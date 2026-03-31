import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { listCases, createCase } from '../../services/casesApi';
import apiClient from '../../services/api';

const STATUS_OPTIONS = ['Active', 'Settled', 'Disposed', 'Appeal', 'Archived'];
const STAGE_OPTIONS  = ['Filing', 'Pleadings', 'Evidence', 'Arguments', 'Judgment', 'Closed'];
const CASE_TYPES     = ['Civil', 'Criminal', 'Family', 'Labour', 'Revenue', 'Commercial', 'Constitutional', 'Other'];

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

function CaseCard({ c, onClick }) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left p-4 rounded-xl border border-primary/10 bg-ivory hover:border-primary/30 hover:shadow-subtle transition-all group"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-sm text-ink truncate group-hover:text-primary transition-colors">
            {c.title}
          </p>
          {c.case_ref && (
            <p className="text-[11px] text-graphite/70 mt-0.5 truncate">{c.case_ref}</p>
          )}
          <div className="mt-2 flex flex-wrap gap-2 items-center">
            <StatusBadge status={c.status} />
            {c.stage && (
              <span className="text-[11px] text-graphite border border-slate-200 rounded px-1.5 py-0.5">
                {c.stage}
              </span>
            )}
            {c.case_type && (
              <span className="text-[11px] text-graphite/70">{c.case_type}</span>
            )}
          </div>
        </div>
        <div className="flex-shrink-0 text-right">
          {c.next_hearing && (
            <p className="text-[11px] text-graphite/70">
              <span className="material-symbols-outlined align-middle text-sm text-primary/60">event</span>{' '}
              {c.next_hearing}
            </p>
          )}
          {c.cnr && (
            <p className="text-[10px] text-graphite/50 mt-1 font-mono">{c.cnr}</p>
          )}
        </div>
      </div>
      {c.brief && (
        <p className="mt-2 text-xs text-graphite/80 line-clamp-2">{c.brief}</p>
      )}
    </button>
  );
}

function CreateCaseModal({ onClose, onCreate, prefillClientId, prefillClientName }) {
  const [form, setForm] = useState({
    title: '', case_ref: '', case_type: 'Civil',
    cnr: '', status: 'Active', stage: 'Filing',
    brief: '', filing_date: '', next_hearing: '',
  });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  // Court cascade
  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [courts, setCourts] = useState([]);
  const [courtState, setCourtState] = useState('');
  const [courtDistrict, setCourtDistrict] = useState('');
  const [courtName, setCourtName] = useState('');

  useEffect(() => {
    apiClient.get('users/get-states/').then(r => setStates(r.data?.states ?? r.data ?? [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (!courtState) { setDistricts([]); setCourtDistrict(''); setCourts([]); setCourtName(''); return; }
    apiClient.get(`users/get-districts/?state=${encodeURIComponent(courtState)}`).then(r => {
      setDistricts(r.data?.districts ?? r.data ?? []);
      setCourtDistrict('');
      setCourts([]);
      setCourtName('');
    }).catch(() => {});
  }, [courtState]);

  useEffect(() => {
    if (!courtState || !courtDistrict) { setCourts([]); setCourtName(''); return; }
    apiClient.get(`users/get-courts/?state=${encodeURIComponent(courtState)}&district=${encodeURIComponent(courtDistrict)}`).then(r => {
      setCourts(r.data?.courts ?? r.data ?? []);
      setCourtName('');
    }).catch(() => {});
  }, [courtState, courtDistrict]);

  function set(field, val) {
    setForm(f => ({ ...f, [field]: val }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.title.trim()) { setErr("Case title is required."); return; }
    setSaving(true);
    setErr('');
    try {
      const payload = {
        title: form.title.trim(),
        case_ref: form.case_ref.trim(),
        case_type: form.case_type,
        cnr: form.cnr.trim(),
        status: form.status,
        stage: form.stage,
        brief: form.brief.trim(),
        filing_date: form.filing_date,
        next_hearing: form.next_hearing,
        court: {
          state: courtState,
          district: courtDistrict,
          court: courtName,
        },
        client_ids: prefillClientId ? [prefillClientId] : [],
      };
      const res = await createCase(payload);
      onCreate(res.data.case);
    } catch (e) {
      setErr(e?.response?.data?.error || 'Failed to create case.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 backdrop-blur-sm p-4">
      <div className="bg-ivory rounded-2xl shadow-elevated w-full max-w-lg">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div>
            <h2 className="text-base font-semibold text-ink">New Case</h2>
            {prefillClientName && (
              <p className="text-xs text-graphite/70 mt-0.5">
                <span className="material-symbols-outlined align-middle text-sm text-primary/70">person</span>{' '}
                Linked to {prefillClientName}
              </p>
            )}
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-slate-100 text-graphite">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4 max-h-[70vh] overflow-y-auto custom-scrollbar">
          <div>
            <label className="block text-xs font-semibold text-graphite mb-1">Case Title *</label>
            <input
              className="form-input w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              placeholder="Sharma v. Singh — Injunction Matter"
              value={form.title}
              onChange={e => set('title', e.target.value)}
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-graphite mb-1">Internal Ref</label>
              <input
                className="form-input w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                placeholder="MAT/2026/001"
                value={form.case_ref}
                onChange={e => set('case_ref', e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-graphite mb-1">CNR</label>
              <input
                className="form-input w-full rounded-xl border border-slate-200 px-3 py-2 text-sm font-mono"
                placeholder="MHAU0500012024"
                value={form.cnr}
                onChange={e => set('cnr', e.target.value.toUpperCase())}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-graphite mb-1">Case Type</label>
              <select className="form-select w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={form.case_type} onChange={e => set('case_type', e.target.value)}>
                {CASE_TYPES.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-graphite mb-1">Stage</label>
              <select className="form-select w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={form.stage} onChange={e => set('stage', e.target.value)}>
                {STAGE_OPTIONS.map(s => <option key={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-graphite mb-1">Filing Date</label>
              <input type="date" className="form-input w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={form.filing_date} onChange={e => set('filing_date', e.target.value)} />
            </div>
            <div>
              <label className="block text-xs font-semibold text-graphite mb-1">Next Hearing</label>
              <input type="date" className="form-input w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                value={form.next_hearing} onChange={e => set('next_hearing', e.target.value)} />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-graphite mb-1">Court</label>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <select
                  className="form-select w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
                  value={courtState}
                  onChange={e => setCourtState(e.target.value)}
                >
                  <option value="">State</option>
                  {states.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <select
                  className="form-select w-full rounded-xl border border-slate-200 px-3 py-2 text-sm disabled:opacity-50"
                  value={courtDistrict}
                  onChange={e => setCourtDistrict(e.target.value)}
                  disabled={!courtState || districts.length === 0}
                >
                  <option value="">District</option>
                  {districts.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </div>
              <div>
                <select
                  className="form-select w-full rounded-xl border border-slate-200 px-3 py-2 text-sm disabled:opacity-50"
                  value={courtName}
                  onChange={e => setCourtName(e.target.value)}
                  disabled={!courtDistrict || courts.length === 0}
                >
                  <option value="">Court</option>
                  {courts.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-graphite mb-1">Brief / Description</label>
            <textarea
              className="form-textarea w-full rounded-xl border border-slate-200 px-3 py-2 text-sm resize-none"
              rows={3}
              placeholder="Short description of the matter..."
              value={form.brief}
              onChange={e => set('brief', e.target.value)}
            />
          </div>
          {err && <p className="text-xs text-red-600">{err}</p>}
        </form>
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-slate-100">
          <button type="button" onClick={onClose}
            className="px-4 py-2 rounded-xl text-sm font-medium text-graphite hover:bg-slate-100 transition">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="px-4 py-2 rounded-xl text-sm font-semibold bg-primary text-white hover:bg-primary-dark transition disabled:opacity-50">
            {saving ? 'Creating…' : 'Create Case'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function CaseRegistry() {
  const navigate = useNavigate();
  const location = useLocation();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [prefillClient, setPrefillClient] = useState(null);

  // Auto-open modal when navigated from ClientOnboarding
  useEffect(() => {
    const s = location.state;
    if (s?.openCreate) {
      setPrefillClient(s.prefillClientId ? { id: s.prefillClientId, name: s.prefillClientName || '' } : null);
      setShowCreate(true);
      // clear state so refresh doesn't re-open
      window.history.replaceState({}, '');
    }
  }, [location.state]);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (statusFilter) params.status = statusFilter;
      if (search.trim()) params.search = search.trim();
      const res = await listCases(params);
      setCases(res.data.cases || []);
    } catch (e) {
      setError(e?.response?.data?.error || 'Failed to load cases.');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, search]);

  useEffect(() => { load(); }, [load]);

  function handleCreated(newCase) {
    setShowCreate(false);
    setPrefillClient(null);
    navigate(`/cases/${newCase._id}`);
  }

  return (
    <div className="max-w-5xl mx-auto py-6 px-2">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-ink flex items-center gap-2">
            <span className="material-symbols-outlined text-primary icon-filled">folder_open</span>
            Case Registry
          </h1>
          <p className="text-sm text-graphite/70 mt-0.5">All your active and archived matters in one place.</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-white text-sm font-semibold hover:bg-primary-dark transition shadow-subtle"
        >
          <span className="material-symbols-outlined text-lg">add</span>
          New Case
        </button>
      </div>

      {/* Quick-filter pills + search + status selector */}
      <div className="flex flex-col gap-3 mb-4">
        {/* Quick-filter pills: Active | Archived | All */}
        <div className="flex gap-2 flex-wrap">
          {[
            { label: 'All',      value: '',         icon: 'folder_open' },
            { label: 'Active',   value: 'Active',   icon: 'pending_actions' },
            { label: 'Archived', value: 'Archived', icon: 'archive' },
          ].map(pill => (
            <button key={pill.value}
              onClick={() => setStatusFilter(pill.value)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                statusFilter === pill.value
                  ? 'bg-primary text-white border-primary'
                  : 'border-slate-200 text-graphite hover:border-primary/40 hover:text-primary'
              }`}>
              <span className="material-symbols-outlined text-sm">{pill.icon}</span>
              {pill.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-3">
          <input
            type="search"
            className="form-input rounded-xl border border-slate-200 px-3 py-2 text-sm w-56"
            placeholder="Search cases…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <select
            className="form-select rounded-xl border border-slate-200 px-3 py-2 text-sm"
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
          >
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      {/* Cases list */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <span className="material-symbols-outlined animate-spin text-primary text-4xl">progress_activity</span>
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-200 bg-red-50 text-red-700 p-4 text-sm">{error}</div>
      ) : cases.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center text-graphite/60 gap-4">
          <span className="material-symbols-outlined text-5xl text-primary/30">folder</span>
          <p className="text-base font-medium">No cases yet.</p>
          <p className="text-sm">Build your case registry by clicking <strong>New Case</strong> above.</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {cases.map(c => (
            <CaseCard
              key={c._id}
              c={c}
              onClick={() => navigate(`/cases/${c._id}`)}
            />
          ))}
        </div>
      )}

      {showCreate && (
        <CreateCaseModal
          onClose={() => { setShowCreate(false); setPrefillClient(null); }}
          onCreate={handleCreated}
          prefillClientId={prefillClient?.id}
          prefillClientName={prefillClient?.name}
        />
      )}
    </div>
  );
}
