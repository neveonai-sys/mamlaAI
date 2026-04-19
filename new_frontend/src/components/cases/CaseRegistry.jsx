import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { beginBlocking, stopBlocking } from '../../features/uiSlice';
import { listCases, createCase, updateCase } from '../../services/casesApi';
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

function CasesTable({ cases, onEdit, onFullDetails }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-primary/10 bg-white shadow-subtle">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-primary/10 bg-ivory/70 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-500">
            <th className="px-4 py-3 text-left">Case Ref</th>
            <th className="px-4 py-3 text-left">Title</th>
            <th className="px-4 py-3 text-left">Client</th>
            <th className="px-4 py-3 text-left">Status</th>
            <th className="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-primary/5">
          {cases.map(c => {
            const isInactive = c.client_status === 'I';
            return (
              <tr key={c._id} className={`hover:bg-primary/3 transition-colors ${isInactive ? 'opacity-60' : ''}`}>
                <td className="px-4 py-3 font-mono text-xs text-graphite/70 whitespace-nowrap">{c.case_ref || '—'}</td>
                <td className="px-4 py-3">
                  <p className="font-medium text-ink text-sm">{c.title}</p>
                  {c.cnr && <p className="text-[11px] text-graphite/50 mt-0.5">{c.cnr}</p>}
                </td>
                <td className="px-4 py-3">
                  {c.client_ids?.length > 0 ? (
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm text-slate-700">{c.client_name || '—'}</span>
                      {isInactive && (
                        <span className="text-[10px] font-semibold bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">Inactive</span>
                      )}
                      {c.client_status === 'P' && (
                        <span className="text-[10px] font-semibold bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded">Pending</span>
                      )}
                    </div>
                  ) : (
                    <span className="text-xs text-graphite/50 italic">{c.client_name_display || 'No client'}</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={c.status} />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => onEdit(c)}
                      className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-graphite hover:border-primary/40 hover:text-primary transition"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => onFullDetails(c._id)}
                      className="px-3 py-1.5 rounded-lg bg-primary/10 text-xs font-semibold text-primary hover:bg-primary/20 transition"
                    >
                      Full Details
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── EditCaseModal ─────────────────────────────────────────────────────────────
function EditCaseModal({ c, onClose, onSaved }) {
  const [title, setTitle] = useState(c.title || '');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');
  // Client re-link section
  const [clientSearch, setClientSearch] = useState('');
  const [clientSuggestions, setClientSuggestions] = useState([]);
  const [newClientId, setNewClientId] = useState(c.client_ids?.[0] || '');
  const [newClientName, setNewClientName] = useState(c.client_name || '');
  const [showChangeClient, setShowChangeClient] = useState(false);
  const [showAddClientForm, setShowAddClientForm] = useState(false);
  const [addFname, setAddFname] = useState('');
  const [addLname, setAddLname] = useState('');
  const [addPhone, setAddPhone] = useState('');
  const [addEmail, setAddEmail] = useState('');
  const [addInviting, setAddInviting] = useState(false);
  const [addErr, setAddErr] = useState('');
  // Invite section (pending clients only)
  const [inviteEmail, setInviteEmail] = useState(c.client_email || '');
  const [inviting, setInviting] = useState(false);
  const [inviteMsg, setInviteMsg] = useState('');
  // Status toggle
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [currentClientStatus, setCurrentClientStatus] = useState(c.client_status || '');

  const hasLinkedClient = (c.client_ids?.length > 0);
  const isPending = hasLinkedClient && !c.client_is_registered;
  const linkedClientId = c.client_ids?.[0] || '';

  useEffect(() => {
    if (!clientSearch.trim()) { setClientSuggestions([]); return; }
    const timer = setTimeout(() => {
      apiClient.get(`users/clients/?search=${encodeURIComponent(clientSearch.trim())}`)
        .then(r => setClientSuggestions(r.data?.results ?? []))
        .catch(() => setClientSuggestions([]));
    }, 300);
    return () => clearTimeout(timer);
  }, [clientSearch]);

  async function handleInviteNewClient() {
    if (!addFname.trim() || !addPhone.trim()) { setAddErr('First name and phone are required.'); return; }
    setAddInviting(true); setAddErr('');
    try {
      const res = await apiClient.post('users/invite_client/', {
        fname: addFname.trim(),
        lname: addLname.trim(),
        email: addEmail.trim(),
        phonenumber: addPhone.trim(),
      });
      const clientId = res.data?.client_id || res.data?.user_id;
      const clientName = `${addFname.trim()} ${addLname.trim()}`.trim();
      if (clientId) {
        setNewClientId(clientId);
        setNewClientName(clientName || addFname.trim());
      } else {
        const lookup = await apiClient.get(`users/clients/?search=${encodeURIComponent(addPhone.trim())}`);
        const found = (lookup.data?.results ?? []).find(cl => cl.phone === addPhone.trim());
        if (found) { setNewClientId(found.id); setNewClientName(found.name || clientName); }
        else { setNewClientName(clientName || addFname.trim()); }
      }
      setShowAddClientForm(false);
      setShowChangeClient(false);
      setAddFname(''); setAddLname(''); setAddPhone(''); setAddEmail('');
    } catch (e) {
      setAddErr(e?.response?.data?.message || 'Failed to invite client.');
    } finally {
      setAddInviting(false);
    }
  }

  async function handleSave() {
    if (!title.trim()) { setErr('Title is required.'); return; }
    setSaving(true); setErr('');
    try {
      const payload = { title: title.trim() };
      if (newClientId && newClientId !== (c.client_ids?.[0] || '')) {
        payload.client_ids = [newClientId];
      }
      const res = await updateCase(c._id, payload);
      onSaved(res.data.case);
    } catch (e) {
      setErr(e?.response?.data?.error || 'Failed to save.');
    } finally {
      setSaving(false);
    }
  }

  async function handleToggleStatus() {
    const next = currentClientStatus === 'I' ? 'A' : 'I';
    setStatusUpdating(true);
    try {
      await apiClient.patch(`users/clients/${linkedClientId}/status/`, { status: next });
      setCurrentClientStatus(next);
    } catch (e) {
      setErr(e?.response?.data?.error || 'Failed to update status.');
    } finally {
      setStatusUpdating(false);
    }
  }

  async function handleSendInvite() {
    setInviting(true); setInviteMsg('');
    try {
      const res = await apiClient.post(`users/clients/${linkedClientId}/resend-invite/`, { email: inviteEmail.trim() });
      setInviteMsg(res.data?.message || 'Invite sent.');
    } catch (e) {
      setInviteMsg(e?.response?.data?.error || 'Failed to send invite.');
    } finally {
      setInviting(false);
    }
  }

  const statusLabel = currentClientStatus === 'I' ? 'Inactive' : currentClientStatus === 'P' ? 'Pending' : 'Active';
  const statusClass = currentClientStatus === 'I' ? 'bg-slate-100 text-slate-600'
    : currentClientStatus === 'P' ? 'bg-amber-100 text-amber-700'
    : 'bg-emerald-100 text-emerald-800';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 backdrop-blur-sm p-4">
      <div className="bg-ivory rounded-2xl shadow-elevated w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h2 className="text-base font-semibold text-ink">Edit Case</h2>
          <button type="button" onClick={onClose} className="text-graphite/50 hover:text-ink">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>
        <div className="px-6 py-4 space-y-4 max-h-[80vh] overflow-y-auto">
          {/* Case Ref — read-only */}
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1">Case Ref</label>
            <p className="font-mono text-sm text-graphite bg-slate-50 rounded-lg px-3 py-2">{c.case_ref || '—'}</p>
          </div>
          {/* Title — editable */}
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1">Title</label>
            <input
              className="form-input w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              value={title}
              onChange={e => setTitle(e.target.value)}
            />
          </div>
          {/* Client section */}
          <div className="rounded-xl border border-slate-100 bg-white p-3 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-500">Client</label>
              {hasLinkedClient && (
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${statusClass}`}>{statusLabel}</span>
              )}
            </div>
            {hasLinkedClient ? (
              <>
                <p className="text-sm text-ink font-medium">{c.client_name || '—'}</p>
                {c.client_phone && <p className="text-xs text-graphite/60">{c.client_phone}</p>}
                {/* Pending-only: editable email + invite button */}
                {isPending && (
                  <div className="space-y-2 pt-2 border-t border-slate-100">
                    <label className="block text-xs font-semibold text-slate-500">Email (to send invite)</label>
                    <div className="flex gap-2">
                      <input
                        className="form-input flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                        placeholder="client@email.com"
                        value={inviteEmail}
                        onChange={e => setInviteEmail(e.target.value)}
                      />
                      <button
                        type="button"
                        onClick={handleSendInvite}
                        disabled={inviting}
                        className="px-3 py-2 rounded-lg bg-primary text-white text-xs font-semibold disabled:opacity-50"
                      >
                        {inviting ? '…' : 'Send invite'}
                      </button>
                    </div>
                    {inviteMsg && <p className="text-xs text-emerald-600">{inviteMsg}</p>}
                  </div>
                )}
                {/* Active/Inactive toggle (only for real clients, not pending-unregistered) */}
                <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                  <span className="text-xs text-graphite/70">Client active in workspace</span>
                  <button
                    type="button"
                    onClick={handleToggleStatus}
                    disabled={statusUpdating}
                    className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors disabled:opacity-50 ${
                      currentClientStatus === 'I' ? 'bg-slate-200' : 'bg-primary'
                    }`}
                  >
                    <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                      currentClientStatus === 'I' ? 'translate-x-0.5' : 'translate-x-[18px]'
                    }`} />
                  </button>
                </div>
              </>
            ) : (
              <p className="text-xs text-graphite/50 italic">{c.client_name_display || 'No client linked'}</p>
            )}
            {/* Change / Add client */}
            {!showChangeClient ? (
              <button type="button" onClick={() => setShowChangeClient(true)} className="text-xs text-primary hover:underline">
                {hasLinkedClient ? 'Change client' : 'Link a client'}
              </button>
            ) : (
              <div className="space-y-2 pt-2 border-t border-slate-100">
                {!showAddClientForm ? (
                  <>
                    <div className="relative">
                      <input
                        className="form-input w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                        placeholder="Search by name, email, or phone…"
                        value={clientSearch}
                        onChange={e => setClientSearch(e.target.value)}
                      />
                      {clientSuggestions.length > 0 && (
                        <ul className="absolute z-20 left-0 right-0 mt-1 bg-white border border-slate-200 rounded-xl shadow-lg max-h-36 overflow-y-auto">
                          {clientSuggestions.map(cl => (
                            <li key={cl.id}
                              className="px-3 py-2 text-sm cursor-pointer hover:bg-primary/5 flex items-center justify-between"
                              onClick={() => {
                                setNewClientId(cl.id);
                                setNewClientName(cl.name || cl.email || cl.phone || cl.id);
                                setClientSearch('');
                                setClientSuggestions([]);
                                setShowChangeClient(false);
                              }}>
                              <span>{cl.name || cl.email || cl.phone}</span>
                              <span className="text-xs text-graphite/50">{cl.phone}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                    {newClientId && newClientId !== (c.client_ids?.[0] || '') && (
                      <p className="text-xs text-primary/80 font-medium">
                        <span className="material-symbols-outlined align-middle text-sm">check_circle</span> Will link: {newClientName}
                      </p>
                    )}
                    <div className="flex items-center gap-3">
                      <button type="button" onClick={() => setShowAddClientForm(true)} className="text-xs text-primary hover:underline">+ Invite new client</button>
                      <button type="button" onClick={() => { setShowChangeClient(false); setClientSearch(''); setClientSuggestions([]); }} className="text-xs text-graphite/60 hover:text-graphite">Cancel</button>
                    </div>
                  </>
                ) : (
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 gap-2">
                      <input className="form-input rounded-lg border border-slate-200 px-3 py-2 text-sm" placeholder="First name *" value={addFname} onChange={e => setAddFname(e.target.value)} />
                      <input className="form-input rounded-lg border border-slate-200 px-3 py-2 text-sm" placeholder="Last name" value={addLname} onChange={e => setAddLname(e.target.value)} />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <input className="form-input rounded-lg border border-slate-200 px-3 py-2 text-sm" placeholder="Phone * (+91…)" value={addPhone} onChange={e => setAddPhone(e.target.value)} />
                      <input className="form-input rounded-lg border border-slate-200 px-3 py-2 text-sm" placeholder="Email" value={addEmail} onChange={e => setAddEmail(e.target.value)} />
                    </div>
                    {addErr && <p className="text-xs text-red-600">{addErr}</p>}
                    <div className="flex gap-2">
                      <button type="button" onClick={handleInviteNewClient} disabled={addInviting} className="flex-1 px-3 py-1.5 rounded-lg bg-primary text-white text-xs font-medium disabled:opacity-50">{addInviting ? 'Inviting…' : 'Invite & Link'}</button>
                      <button type="button" onClick={() => { setShowAddClientForm(false); setAddErr(''); }} className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs text-graphite">Back</button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
          {err && <p className="text-xs text-red-600">{err}</p>}
        </div>
        <div className="flex justify-end gap-2 px-6 py-4 border-t border-slate-100">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-xl text-sm font-medium text-graphite hover:bg-slate-100 transition">Cancel</button>
          <button type="button" onClick={handleSave} disabled={saving} className="px-4 py-2 rounded-xl text-sm font-semibold bg-primary text-white hover:bg-primary-dark transition disabled:opacity-50">
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── CreateCaseModal ───────────────────────────────────────────────────────────
function CreateCaseModal({ onClose, onCreate, prefillClientId, prefillClientName }) {
  const [form, setForm] = useState({
    title: '', case_type: 'Civil',
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

  // Client link
  const [clientSectionOpen, setClientSectionOpen] = useState(false);
  const [clientSearch, setClientSearch] = useState('');
  const [clientSuggestions, setClientSuggestions] = useState([]);
  const [linkedClientId, setLinkedClientId] = useState('');
  const [linkedClientName, setLinkedClientName] = useState('');
  const [showNewClientForm, setShowNewClientForm] = useState(false);
  const [newClientFname, setNewClientFname] = useState('');
  const [newClientLname, setNewClientLname] = useState('');
  const [newClientEmail, setNewClientEmail] = useState('');
  const [newClientPhone, setNewClientPhone] = useState('');
  const [inviting, setInviting] = useState(false);
  const [inviteErr, setInviteErr] = useState('');

  useEffect(() => {
    apiClient.get('users/get-states/').then(r => {
      const raw = r.data?.states ?? r.data ?? [];
      setStates(raw.map((s) => (typeof s === 'string' ? s : s.name)));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!courtState) { setDistricts([]); setCourtDistrict(''); setCourts([]); setCourtName(''); return; }
    apiClient.get(`users/get-districts/?state_code=${encodeURIComponent(courtState)}`).then(r => {
      const raw = r.data?.districts ?? r.data ?? [];
      setDistricts(raw.map((d) => (typeof d === 'string' ? d : d.name)));
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

  useEffect(() => {
    if (!clientSearch.trim()) { setClientSuggestions([]); return; }
    const timer = setTimeout(() => {
      apiClient.get(`users/clients/?search=${encodeURIComponent(clientSearch.trim())}`)
        .then(r => setClientSuggestions(r.data?.results ?? []))
        .catch(() => setClientSuggestions([]));
    }, 300);
    return () => clearTimeout(timer);
  }, [clientSearch]);

  async function handleInviteClient() {
    if (!newClientFname.trim() || !newClientPhone.trim()) { setInviteErr('First name and phone are required.'); return; }
    setInviting(true); setInviteErr('');
    try {
      const res = await apiClient.post('users/invite_client/', {
        fname: newClientFname.trim(),
        lname: newClientLname.trim(),
        email: newClientEmail.trim(),
        phonenumber: newClientPhone.trim(),
      });
      const clientId = res.data?.client_id || res.data?.user_id;
      const clientName = `${newClientFname.trim()} ${newClientLname.trim()}`.trim();
      if (clientId) {
        setLinkedClientId(clientId);
        setLinkedClientName(clientName || newClientFname.trim());
      } else {
        const lookup = await apiClient.get(`users/clients/?search=${encodeURIComponent(newClientPhone.trim())}`);
        const found = (lookup.data?.results ?? []).find(c => c.phone === newClientPhone.trim());
        if (found) { setLinkedClientId(found.id); setLinkedClientName(found.name || clientName); }
        else { setLinkedClientName(clientName || newClientFname.trim()); }
      }
      setShowNewClientForm(false);
      setNewClientFname(''); setNewClientLname(''); setNewClientEmail(''); setNewClientPhone('');
    } catch (e) {
      setInviteErr(e?.response?.data?.message || 'Failed to invite client.');
    } finally {
      setInviting(false);
    }
  }

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
        client_ids: prefillClientId ? [prefillClientId] : (linkedClientId ? [linkedClientId] : []),
        client_name_display: linkedClientName.trim() || undefined,
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
          {/* Link Client (only shown when no prefillClientId) */}
          {!prefillClientId && (
            <div className="border border-slate-200 rounded-xl overflow-hidden">
              <button
                type="button"
                onClick={() => setClientSectionOpen(o => !o)}
                className="w-full flex items-center justify-between px-3 py-2 bg-slate-50 hover:bg-slate-100 text-sm font-medium text-graphite transition"
              >
                <span className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-base text-primary/70">person_add</span>
                  {linkedClientName ? `Client: ${linkedClientName}` : 'Link Client (optional)'}
                </span>
                <span className="material-symbols-outlined text-sm">{clientSectionOpen ? 'expand_less' : 'expand_more'}</span>
              </button>
              {clientSectionOpen && (
                <div className="px-3 py-3 space-y-2 bg-white">
                  {!showNewClientForm ? (
                    <>
                      <div className="relative">
                        <input
                          className="form-input w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                          placeholder="Search by name, email, or phone…"
                          value={clientSearch}
                          onChange={e => { setClientSearch(e.target.value); setLinkedClientId(''); setLinkedClientName(''); }}
                        />
                        {clientSuggestions.length > 0 && (
                          <ul className="absolute z-20 left-0 right-0 mt-1 bg-white border border-slate-200 rounded-xl shadow-lg max-h-40 overflow-y-auto">
                            {clientSuggestions.map(c => (
                              <li key={c.id}
                                className="px-3 py-2 text-sm cursor-pointer hover:bg-primary/5 flex items-center justify-between"
                                onClick={() => { setLinkedClientId(c.id); setLinkedClientName(c.name || c.email || c.phone || c.id); setClientSearch(''); setClientSuggestions([]); }}>
                                <span>{c.name || c.email || c.phone}</span>
                                <span className="text-xs text-graphite/50">{c.phone}</span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                      {linkedClientId && (
                        <div className="flex items-center gap-1.5 text-xs text-primary/80 font-medium">
                          <span className="material-symbols-outlined text-sm">check_circle</span>
                          {linkedClientName}
                          <button type="button" onClick={() => { setLinkedClientId(''); setLinkedClientName(''); }} className="ml-auto text-graphite/40 hover:text-red-500"><span className="material-symbols-outlined text-sm">close</span></button>
                        </div>
                      )}
                      <button type="button" onClick={() => setShowNewClientForm(true)} className="text-xs text-primary hover:underline">+ Invite new client</button>
                    </>
                  ) : (
                    <div className="space-y-2">
                      <div className="grid grid-cols-2 gap-2">
                        <input className="form-input rounded-lg border border-slate-200 px-3 py-2 text-sm" placeholder="First name *" value={newClientFname} onChange={e => setNewClientFname(e.target.value)} />
                        <input className="form-input rounded-lg border border-slate-200 px-3 py-2 text-sm" placeholder="Last name" value={newClientLname} onChange={e => setNewClientLname(e.target.value)} />
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <input className="form-input rounded-lg border border-slate-200 px-3 py-2 text-sm" placeholder="Phone * (e.g. +91…)" value={newClientPhone} onChange={e => setNewClientPhone(e.target.value)} />
                        <input className="form-input rounded-lg border border-slate-200 px-3 py-2 text-sm" placeholder="Email" value={newClientEmail} onChange={e => setNewClientEmail(e.target.value)} />
                      </div>
                      {inviteErr && <p className="text-xs text-red-600">{inviteErr}</p>}
                      <div className="flex gap-2">
                        <button type="button" onClick={handleInviteClient} disabled={inviting} className="flex-1 px-3 py-1.5 rounded-lg bg-primary text-white text-xs font-medium disabled:opacity-50">{inviting ? 'Inviting…' : 'Invite & Link'}</button>
                        <button type="button" onClick={() => { setShowNewClientForm(false); setInviteErr(''); }} className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs text-graphite">Cancel</button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
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
  const dispatch = useDispatch();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [editingCase, setEditingCase] = useState(null);
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
    dispatch(beginBlocking({ message: 'Loading cases...' }));
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
      dispatch(stopBlocking());
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
        <CasesTable
          cases={cases}
          onEdit={(c) => setEditingCase(c)}
          onFullDetails={(id) => navigate(`/cases/${id}`)}
        />
      )}

      {showCreate && (
        <CreateCaseModal
          onClose={() => { setShowCreate(false); setPrefillClient(null); }}
          onCreate={handleCreated}
          prefillClientId={prefillClient?.id}
          prefillClientName={prefillClient?.name}
        />
      )}

      {editingCase && (
        <EditCaseModal
          c={editingCase}
          onClose={() => setEditingCase(null)}
          onSaved={() => {
            setEditingCase(null);
            load();
          }}
        />
      )}
    </div>
  );
}
