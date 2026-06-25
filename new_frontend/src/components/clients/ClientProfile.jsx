import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import apiClient from '../../services/api';
import { listCases } from '../../services/casesApi';

const STATUS_COLOUR = {
  Active:   'bg-emerald-100 text-emerald-700',
  Closed:   'bg-slate-100 text-slate-500',
  Pending:  'bg-amber-100 text-amber-700',
};

export default function ClientProfile() {
  const { clientId } = useParams();
  const navigate = useNavigate();

  const [client, setClient] = useState(null);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError('');
      try {
        const [clientsRes, casesRes] = await Promise.all([
          apiClient.get('users/clients/'),
          listCases(),
        ]);
        const allClients = clientsRes.data?.results ?? [];
        const found = allClients.find((c) => c.id === clientId || c.client_id === clientId);
        setClient(found || null);
        const allCases = casesRes.data?.cases ?? [];
        setCases(allCases.filter((c) => Array.isArray(c.client_ids) && c.client_ids.includes(clientId)));
      } catch {
        setError('Could not load client profile.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [clientId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <span className="material-symbols-outlined animate-spin text-primary text-4xl">progress_activity</span>
      </div>
    );
  }

  if (error || !client) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-3">
        <span className="material-symbols-outlined text-5xl text-slate-300">person_off</span>
        <p className="text-sm text-graphite/60">{error || 'Client not found.'}</p>
        <button onClick={() => navigate('/clients')} className="text-sm text-primary hover:underline">← Back to Clients</button>
      </div>
    );
  }

  const initials = `${(client.fname || ' ')[0]}${(client.lname || ' ')[0]}`.trim().toUpperCase() || '?';
  const fullName = client.name || `${client.fname || ''} ${client.lname || ''}`.trim() || client.email || 'Unknown';

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      {/* Back */}
      <button onClick={() => navigate('/clients')} className="flex items-center gap-1 text-sm text-graphite/60 hover:text-primary transition">
        <span className="material-symbols-outlined text-base">arrow_back</span>
        All Clients
      </button>

      {/* Header card */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 flex items-start gap-5">
        <div className="w-16 h-16 rounded-2xl bg-primary/10 text-primary font-bold text-2xl flex items-center justify-center shrink-0">
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-ink truncate">{fullName}</h1>
          <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm text-graphite/70">
            {client.email && (
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-sm">mail</span>
                {client.email}
              </span>
            )}
            {client.phone && (
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-sm">phone</span>
                {client.phone}
              </span>
            )}
            {client.status && (
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOUR[client.status] || 'bg-slate-100 text-slate-500'}`}>
                {client.status}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Cases */}
      <div>
        <h2 className="text-sm font-semibold text-graphite mb-3 flex items-center gap-1.5">
          <span className="material-symbols-outlined text-base text-primary/70">folder_open</span>
          Cases ({cases.length})
        </h2>
        {cases.length === 0 ? (
          <p className="text-sm text-graphite/50 bg-white rounded-xl border border-slate-100 px-4 py-6 text-center">No cases linked to this client yet.</p>
        ) : (
          <div className="space-y-2">
            {cases.map((c) => (
              <button
                key={c._id}
                onClick={() => navigate(`/cases/${c._id}`)}
                className="w-full text-left bg-white rounded-xl border border-slate-100 px-4 py-3 hover:border-primary/30 hover:shadow-sm transition flex items-center justify-between gap-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-ink truncate">{c.title}</p>
                  <p className="text-xs text-graphite/50 mt-0.5">{c.case_type} · {c.stage}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {c.case_ref && (
                    <span className="text-xs font-mono text-graphite/40">{c.case_ref}</span>
                  )}
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOUR[c.status] || 'bg-slate-100 text-slate-500'}`}>
                    {c.status}
                  </span>
                  <span className="material-symbols-outlined text-sm text-graphite/30">chevron_right</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
