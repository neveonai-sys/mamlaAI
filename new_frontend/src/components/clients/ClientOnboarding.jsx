import React, { useState, useEffect } from 'react';
import apiClient from '../../services/api';

const USER_TYPE_LABELS = { Client: 'Client', Paralegal: 'Paralegal', Lawyer: 'Lawyer' };

function splitName(name = '') {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) {
    return { firstname: '', lastname: '' };
  }
  return {
    firstname: parts[0],
    lastname: parts.slice(1).join(' '),
  };
}

function normalizeClient(client) {
  const fallbackName = splitName(client?.name || '');
  const firstname = client?.firstname || client?.fname || client?.first_name || fallbackName.firstname;
  const lastname = client?.lastname || client?.lname || client?.last_name || fallbackName.lastname;

  return {
    id: client?.id || client?.client_id || client?.user_id || '',
    client_id: client?.client_id || client?.id || client?.user_id || '',
    firstname,
    lastname,
    name: `${firstname} ${lastname}`.trim(),
    email: client?.email || '',
    phone: client?.phone || client?.phone_number || client?.phonenumber || '',
    case_id: client?.case_id || client?.caseId || null,
    user_type: client?.user_type || 'Client',
    status: client?.status || client?.user_status || '',
    created_at: client?.created_at || client?.onboarding_time || null,
  };
}

function buildUpdatePayload(form) {
  return {
    fname: form.firstname.trim(),
    lname: form.lastname.trim(),
    email: form.email.trim(),
    phonenumber: form.phone.trim(),
  };
}

function buildInvitePayload(form) {
  return {
    fname: form.firstname.trim(),
    lname: form.lastname.trim(),
    email: form.email.trim(),
    phonenumber: form.phone.trim(),
    case_id: form.case_id.trim(),
  };
}

function ClientCard({ client, onClick, isSelected }) {
  const initials = `${client.firstname?.[0] ?? ''}${client.lastname?.[0] ?? ''}`.toUpperCase() || 'C';
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-4 rounded-xl border transition-all ${
        isSelected
          ? 'bg-primary/5 border-primary/30'
          : 'bg-ivory border-primary/10 hover:border-primary/20'
      }`}
    >
      <div className="flex items-center gap-3">
        <div className="size-10 rounded-full bg-primary/10 text-primary font-bold text-sm flex items-center justify-center flex-shrink-0">
          {initials}
        </div>
        <div className="min-w-0">
          <p className="font-semibold text-sm text-ink truncate">
            {client.firstname} {client.lastname}
          </p>
          <p className="text-xs text-slate-500 truncate">{client.email}</p>
        </div>
      </div>
    </button>
  );
}

function InviteClientForm({ initial, onSave, onCancel, loading }) {
  const [form, setForm] = useState(initial || {
    firstname: '', lastname: '', email: '', phone: '', case_id: '', user_type: 'Client',
  });

  function handleChange(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  }

  return (
    <form
      className="space-y-5 p-6"
      onSubmit={(e) => { e.preventDefault(); onSave(form); }}
    >
      <h3 className="font-bold text-ink">{initial?.id ? 'Edit Client' : 'Invite New Client'}</h3>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold mb-1 text-slate-700">First Name *</label>
          <input name="firstname" required value={form.firstname} onChange={handleChange} className="input-base" placeholder="Priya" />
        </div>
        <div>
          <label className="block text-xs font-semibold mb-1 text-slate-700">Last Name *</label>
          <input name="lastname" required value={form.lastname} onChange={handleChange} className="input-base" placeholder="Doe" />
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold mb-1 text-slate-700">Email *</label>
        <input type="email" name="email" required value={form.email} onChange={handleChange} className="input-base" placeholder="priya.sharma@example.com" />
      </div>

      <div>
        <label className="block text-xs font-semibold mb-1 text-slate-700">Phone {initial?.id ? '' : '*'}</label>
        <input name="phone" value={form.phone} onChange={handleChange} className="input-base" placeholder="9876543210" />
        {!initial?.id ? (
          <p className="mt-1 text-[11px] text-slate-400">The backend requires phone for new lawyer-created onboarding.</p>
        ) : null}
      </div>

      <div>
        <label className="block text-xs font-semibold mb-1 text-slate-700">Case ID</label>
        <input name="case_id" value={form.case_id} onChange={handleChange} className="input-base" placeholder="Optional case to link during onboarding" />
      </div>

      {!initial?.id ? (
        <div>
          <label className="block text-xs font-semibold mb-1 text-slate-700">Role</label>
          <div className="flex gap-2">
            {['Client', 'Paralegal'].map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => setForm((f) => ({ ...f, user_type: opt }))}
                className={`flex-1 py-2 text-xs font-semibold rounded-lg border transition-all ${
                  form.user_type === opt
                    ? 'bg-primary text-ivory border-primary'
                    : 'bg-white text-slate-600 border-slate-200 hover:border-primary/50'
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div className="flex gap-2 pt-2">
        <button type="button" className="rounded-full border border-primary/15 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-primary/5 hover:text-primary flex-1" onClick={onCancel}>Cancel</button>
        <button type="submit" disabled={loading} className="btn-primary flex-1">
          {loading ? 'Saving…' : initial?.id ? 'Update' : 'Send Invite'}
        </button>
      </div>
    </form>
  );
}

function ExistingClientForm({ onSave, onCancel, loading }) {
  const [form, setForm] = useState({ email: '', phone: '', case_id: '' });

  function handleChange(e) {
    setForm((current) => ({ ...current, [e.target.name]: e.target.value }));
  }

  return (
    <form className="space-y-5 p-6" onSubmit={(e) => { e.preventDefault(); onSave(form); }}>
      <h3 className="font-bold text-ink">Link Existing User</h3>
      <p className="text-sm text-slate-500">Use this when the client already exists in the system and only needs to be linked to your account.</p>

      <div>
        <label className="block text-xs font-semibold mb-1 text-slate-700">Phone</label>
        <input name="phone" value={form.phone} onChange={handleChange} className="input-base" placeholder="9876543210" />
      </div>

      <div>
        <label className="block text-xs font-semibold mb-1 text-slate-700">Email</label>
        <input type="email" name="email" value={form.email} onChange={handleChange} className="input-base" placeholder="client@example.com" />
      </div>

      <div>
        <label className="block text-xs font-semibold mb-1 text-slate-700">Case ID</label>
        <input name="case_id" value={form.case_id} onChange={handleChange} className="input-base" placeholder="Optional case to attach while linking" />
      </div>

      <div className="flex gap-2 pt-2">
        <button type="button" className="rounded-full border border-primary/15 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-primary/5 hover:text-primary flex-1" onClick={onCancel}>Cancel</button>
        <button type="submit" disabled={loading} className="btn-primary flex-1">
          {loading ? 'Linking…' : 'Link Client'}
        </button>
      </div>
    </form>
  );
}

function EmptyState({ onAdd, onLink }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center h-full gap-4 text-center">
      <span className="material-symbols-outlined text-slate-300 text-6xl">people</span>
      <div>
        <h3 className="text-lg font-bold text-ink mb-1">Select a Client</h3>
        <p className="text-sm text-slate-400">
          Choose a client from the left panel to view their details.
        </p>
      </div>
      <div className="flex gap-3 mt-2">
        <label className="block text-xs font-semibold mb-1 text-slate-700">Role</label>
        <button className="btn-primary flex items-center gap-2" onClick={onAdd}>
          <span className="material-symbols-outlined text-base">person_add</span>
          Invite Client
        </button>
        <button className="rounded-full border border-primary/15 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-primary/5 hover:text-primary" onClick={onLink}>
          Link Existing
        </button>
      </div>
    </div>
  );
}

export default function ClientOnboarding() {
  const [clients, setClients] = useState([]);
  const [selected, setSelected] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [formMode, setFormMode] = useState('invite');
  const [editClient, setEditClient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [formLoading, setFormLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function loadClients(preferredId = null) {
    setLoading(true);
    try {
      const response = await apiClient.get('users/clients/');
      const nextClients = (response.data?.results ?? response.data ?? []).map(normalizeClient);
      setClients(nextClients);

      const selectedId = preferredId || selected?.id;
      if (selectedId) {
        const match = nextClients.find((client) => client.id === selectedId);
        setSelected(match || nextClients[0] || null);
      } else {
        setSelected((current) => current || nextClients[0] || null);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load clients.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadClients();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSave(form) {
    setFormLoading(true);
    setError('');
    setMessage('');
    try {
      if (form.id) {
        const payload = buildUpdatePayload(form);
        await apiClient.put(`users/clients/${form.id}/`, payload);
        await loadClients(form.id);
        setMessage('Client details updated.');
      } else {
        const payload = buildInvitePayload(form);
        await apiClient.post('users/invite_client/', payload);
        await loadClients();
        setMessage('Client invite sent successfully.');
      }
      setShowForm(false);
      setEditClient(null);
      setFormMode('invite');
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.message || 'Save failed.');
    } finally {
      setFormLoading(false);
    }
  }

  async function handleLinkExisting(form) {
    setFormLoading(true);
    setError('');
    setMessage('');
    try {
      const payload = {
        phonenumber: form.phone.trim(),
        email: form.email.trim(),
        case_id: form.case_id.trim(),
      };
      const checkResponse = await apiClient.post('users/check-existing-user/', payload);
      if (!checkResponse.data?.exists) {
        setError('No existing user matched that phone or email.');
        return;
      }

      await apiClient.post('users/onboard-existing-client/', payload);
      await loadClients();
      setShowForm(false);
      setFormMode('invite');
      setMessage('Existing client linked successfully.');
    } catch (err) {
      setError(err.response?.data?.error || err.response?.data?.message || 'Failed to link existing client.');
    } finally {
      setFormLoading(false);
    }
  }

  const filtered = clients.filter((c) => {
    const q = search.toLowerCase();
    return (
      !q ||
      `${c.firstname} ${c.lastname}`.toLowerCase().includes(q) ||
      c.email?.toLowerCase().includes(q) ||
      c.phone?.toLowerCase().includes(q) ||
      c.case_id?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: client list */}
      <aside className="w-80 border-r border-primary/10 bg-slate-50 flex flex-col">
        <div className="p-4 border-b border-primary/10">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-bold text-ink">Clients</h2>
            <button
              className="btn-primary text-xs py-1.5 px-3 flex items-center gap-1"
              onClick={() => {
                setEditClient(null);
                setFormMode('invite');
                setShowForm(true);
                setError('');
                setMessage('');
              }}
            >
              <span className="material-symbols-outlined text-sm">person_add</span>
              Add
            </button>
          </div>
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">search</span>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search clients…"
              className="w-full bg-white border border-slate-200 rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2">
          {loading ? (
            [1, 2, 3].map((i) => <div key={i} className="h-16 bg-ivory rounded-xl animate-pulse" />)
          ) : filtered.length === 0 ? (
            <div className="text-center py-10">
              <span className="material-symbols-outlined text-slate-300 text-4xl block mb-2">people</span>
              <p className="text-xs text-slate-400">{search ? 'No results' : 'No clients yet'}</p>
            </div>
          ) : (
            filtered.map((c) => (
              <ClientCard
                key={c.id}
                client={c}
                onClick={() => { setSelected(c); setShowForm(false); setError(''); setMessage(''); }}
                isSelected={selected?.id === c.id}
              />
            ))
          )}
        </div>
      </aside>

      {/* Right: detail / form */}
      <div className="flex-1 overflow-y-auto bg-background-light">
        {error ? (
          <div className="mx-6 mt-6 flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            <span className="material-symbols-outlined text-base">error</span>
            {error}
          </div>
        ) : null}
        {message ? (
          <div className="mx-6 mt-6 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            <span className="material-symbols-outlined text-base">check_circle</span>
            {message}
          </div>
        ) : null}

        {showForm ? (
          <div className="p-6">
            {!editClient ? (
              <div className="mb-4 flex gap-2 rounded-2xl border border-primary/10 bg-white p-1 w-fit">
                <button
                  type="button"
                  onClick={() => setFormMode('invite')}
                  className={`rounded-xl px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition-colors ${
                    formMode === 'invite' ? 'bg-primary text-ivory' : 'text-slate-500 hover:text-primary'
                  }`}
                >
                  Invite New
                </button>
                <button
                  type="button"
                  onClick={() => setFormMode('existing')}
                  className={`rounded-xl px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition-colors ${
                    formMode === 'existing' ? 'bg-primary text-ivory' : 'text-slate-500 hover:text-primary'
                  }`}
                >
                  Link Existing
                </button>
              </div>
            ) : null}

            <div className="card max-w-2xl">
              {editClient || formMode === 'invite' ? (
                <InviteClientForm
                  initial={editClient}
                  onSave={handleSave}
                  onCancel={() => { setShowForm(false); setEditClient(null); setFormMode('invite'); }}
                  loading={formLoading}
                />
              ) : (
                <ExistingClientForm
                  onSave={handleLinkExisting}
                  onCancel={() => { setShowForm(false); setFormMode('invite'); }}
                  loading={formLoading}
                />
              )}
            </div>
          </div>
        ) : selected ? (
          <div className="p-8 max-w-2xl">
            <div className="flex items-start justify-between mb-8">
              <div className="flex items-center gap-4">
                <div className="size-16 rounded-full bg-primary/10 text-primary font-black text-xl flex items-center justify-center">
                  {`${selected.firstname?.[0] ?? ''}${selected.lastname?.[0] ?? ''}`.toUpperCase()}
                </div>
                <div>
                  <h2 className="text-xl font-black text-ink">
                    {selected.firstname} {selected.lastname}
                  </h2>
                  <p className="text-sm text-slate-500">{selected.email}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">{USER_TYPE_LABELS[selected.user_type] || 'Client'}</span>
                    {selected.status ? <span className="rounded-full bg-background-light px-3 py-1 text-xs font-semibold text-slate-500">Status: {selected.status}</span> : null}
                  </div>
                </div>
              </div>
              <button
                className="rounded-full border border-primary/20 px-4 py-2 flex items-center gap-1.5 text-xs font-semibold text-slate-600 transition-colors hover:bg-primary/5 hover:text-primary"
                onClick={() => { setEditClient(selected); setShowForm(true); setFormMode('invite'); setError(''); setMessage(''); }}
              >
                <span className="material-symbols-outlined text-sm">edit</span>
                Edit
              </button>
            </div>

            <div className="grid grid-cols-1 gap-5">
              {[
                { label: 'Phone', value: selected.phone, icon: 'phone' },
                { label: 'Client ID', value: selected.client_id || selected.id, icon: 'badge' },
                { label: 'Case ID', value: selected.case_id, icon: 'folder_open' },
                { label: 'Joined', value: selected.created_at ? new Date(selected.created_at).toLocaleDateString('en-IN') : '—', icon: 'calendar_today' },
              ].map(({ label, value, icon }) => value && (
                <div key={label} className="card flex items-center gap-4">
                  <div className="size-10 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
                    <span className="material-symbols-outlined text-primary">{icon}</span>
                  </div>
                  <div>
                    <p className="text-xs text-slate-400 uppercase tracking-wider">{label}</p>
                    <p className="font-semibold text-ink">{value}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <EmptyState
            onAdd={() => { setShowForm(true); setFormMode('invite'); setError(''); setMessage(''); }}
            onLink={() => { setShowForm(true); setFormMode('existing'); setError(''); setMessage(''); }}
          />
        )}
      </div>
    </div>
  );
}
