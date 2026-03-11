import React, { useState, useEffect } from 'react';
import apiClient from '../../services/api';

const USER_TYPE_LABELS = { Client: 'Client', Paralegal: 'Paralegal', Lawyer: 'Lawyer' };

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

function ClientForm({ initial, onSave, onCancel, loading }) {
  const [form, setForm] = useState(initial || {
    firstname: '', lastname: '', email: '', phone: '', organization: '', user_type: 'Client',
  });

  function handleChange(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  }

  return (
    <form
      className="space-y-5 p-6"
      onSubmit={(e) => { e.preventDefault(); onSave(form); }}
    >
      <h3 className="font-bold text-ink">{initial?.id ? 'Edit Client' : 'Add New Client'}</h3>

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
        <label className="block text-xs font-semibold mb-1 text-slate-700">Phone</label>
        <input name="phone" value={form.phone} onChange={handleChange} className="input-base" placeholder="+91 98xxx xxxxx" />
      </div>

      <div>
        <label className="block text-xs font-semibold mb-1 text-slate-700">Organization / Firm</label>
        <input name="organization" value={form.organization} onChange={handleChange} className="input-base" placeholder="Company or firm name" />
      </div>

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

      <div className="flex gap-2 pt-2">
        <button type="button" className="btn-ghost flex-1" onClick={onCancel}>Cancel</button>
        <button type="submit" disabled={loading} className="btn-primary flex-1">
          {loading ? 'Saving…' : initial?.id ? 'Update' : 'Add Client'}
        </button>
      </div>
    </form>
  );
}

export default function ClientOnboarding() {
  const [clients, setClients] = useState([]);
  const [selected, setSelected] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [editClient, setEditClient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [formLoading, setFormLoading] = useState(false);
  const [search, setSearch] = useState('');

  useEffect(() => {
    apiClient.get('users/clients/')
      .then((r) => setClients(r.data?.results ?? r.data ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleSave(form) {
    setFormLoading(true);
    try {
      if (form.id) {
        const res = await apiClient.put(`users/clients/${form.id}/`, form);
        setClients((c) => c.map((x) => (x.id === form.id ? res.data : x)));
      } else {
        const res = await apiClient.post('users/invite_client/', form);
        setClients((c) => [res.data, ...c]);
      }
      setShowForm(false);
      setEditClient(null);
    } catch (err) {
      alert(err.response?.data?.error || 'Save failed.');
    } finally {
      setFormLoading(false);
    }
  }

  const filtered = clients.filter((c) => {
    const q = search.toLowerCase();
    return (
      !q ||
      `${c.firstname} ${c.lastname}`.toLowerCase().includes(q) ||
      c.email?.toLowerCase().includes(q)
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
              onClick={() => { setEditClient(null); setShowForm(true); }}
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
                onClick={() => { setSelected(c); setShowForm(false); }}
                isSelected={selected?.id === c.id}
              />
            ))
          )}
        </div>
      </aside>

      {/* Right: detail / form */}
      <div className="flex-1 overflow-y-auto bg-background-light">
        {showForm ? (
          <ClientForm
            initial={editClient}
            onSave={handleSave}
            onCancel={() => { setShowForm(false); setEditClient(null); }}
            loading={formLoading}
          />
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
                  <span className="badge-info mt-1">{selected.user_type || 'Client'}</span>
                </div>
              </div>
              <button
                className="btn-ghost border border-primary/20 rounded-lg flex items-center gap-1.5 text-xs"
                onClick={() => { setEditClient(selected); setShowForm(true); }}
              >
                <span className="material-symbols-outlined text-sm">edit</span>
                Edit
              </button>
            </div>

            <div className="grid grid-cols-1 gap-5">
              {[
                { label: 'Phone', value: selected.phone, icon: 'phone' },
                { label: 'Organization', value: selected.organization, icon: 'corporate_fare' },
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
          <div className="flex-1 flex flex-col items-center justify-center h-full gap-4 text-center">
            <span className="material-symbols-outlined text-slate-300 text-6xl">people</span>
            <div>
              <h3 className="text-lg font-bold text-ink mb-1">Select a Client</h3>
              <p className="text-sm text-slate-400">
                Choose a client from the left panel to view their details.
              </p>
            </div>
            <button
              className="btn-primary flex items-center gap-2 mt-2"
              onClick={() => setShowForm(true)}
            >
              <span className="material-symbols-outlined text-base">person_add</span>
              Add First Client
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
