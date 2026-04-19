import React, { useState, useEffect } from 'react';
import apiClient from '../../services/api';

const STATUS_ICONS = {
  'Order Uploaded': { icon: 'upload_file', color: 'text-emerald-600 bg-emerald-50' },
  'Next Date Set': { icon: 'event', color: 'text-blue-600 bg-blue-50' },
  'Hearing Tomorrow': { icon: 'warning', color: 'text-amber-600 bg-amber-50' },
  'Case Dismissed': { icon: 'cancel', color: 'text-red-600 bg-red-50' },
  'default': { icon: 'update', color: 'text-slate-600 bg-slate-100' },
};

function getStatusStyle(update_type) {
  return STATUS_ICONS[update_type] || STATUS_ICONS.default;
}

function UpdateRow({ item, onClick }) {
  const style = getStatusStyle(item.update_type || item.status);
  return (
    <div
      className="flex items-start gap-4 px-5 py-4 hover:bg-primary/5 cursor-pointer transition-colors border-b border-primary/5 last:border-b-0"
      onClick={onClick}
    >
      <div className={`size-9 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${style.color.split(' ')[1]}`}>
        <span className={`material-symbols-outlined text-lg ${style.color.split(' ')[0]}`}>{style.icon}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className="font-semibold text-sm text-ink line-clamp-1">
            {item.case_title || item.title || 'Court Update'}
          </p>
          <span className="text-[10px] text-slate-400 flex-shrink-0">
            {item.date ? new Date(item.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : 'Today'}
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">
          {item.court || item.detail || item.update_type || 'Status updated'}
        </p>
        {item.next_date && (
          <p className="text-xs text-primary font-semibold mt-1 flex items-center gap-1">
            <span className="material-symbols-outlined text-xs">event</span>
            Next date: {new Date(item.next_date).toLocaleDateString('en-IN', {
              day: 'numeric', month: 'short', year: 'numeric',
            })}
          </p>
        )}
      </div>
    </div>
  );
}

function UpdateDetail({ item, onClose }) {
  if (!item) return null;
  const style = getStatusStyle(item.update_type || item.status);
  return (
    <aside className="w-96 border-l border-primary/10 bg-ivory flex flex-col flex-shrink-0">
      <div className="flex items-center justify-between p-5 border-b border-primary/10">
        <h3 className="font-bold text-sm text-ink">Update Detail</h3>
        <button onClick={onClose} className="p-1.5 hover:bg-primary/5 rounded-lg transition-colors">
          <span className="material-symbols-outlined text-slate-400">close</span>
        </button>
      </div>
      <div className="flex-1 overflow-y-auto custom-scrollbar p-5 space-y-5">
        <div className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg ${style.color.split(' ')[1]}`}>
          <span className={`material-symbols-outlined text-lg ${style.color.split(' ')[0]}`}>{style.icon}</span>
          <span className={`text-sm font-bold ${style.color.split(' ')[0]}`}>
            {item.update_type || item.status || 'Update'}
          </span>
        </div>
        <div className="space-y-3">
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Case</p>
            <p className="font-semibold text-ink">{item.case_title || item.title || '—'}</p>
          </div>
          {item.cnr_number && (
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">CNR Number</p>
              <p className="font-mono text-sm font-semibold text-ink">{item.cnr_number}</p>
            </div>
          )}
          {item.court && (
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Court</p>
              <p className="text-sm font-semibold text-ink">{item.court}</p>
            </div>
          )}
          {item.next_date && (
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Next Hearing Date</p>
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-lg icon-filled">event</span>
                <p className="font-bold text-primary">
                  {new Date(item.next_date).toLocaleDateString('en-IN', {
                    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
                  })}
                </p>
              </div>
            </div>
          )}
          {item.detail && (
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Details</p>
              <p className="text-sm text-slate-600 leading-relaxed">{item.detail}</p>
            </div>
          )}
          {item.order_text && (
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Order Text</p>
              <div className="bg-background-light border border-primary/10 rounded-lg p-3 text-xs text-slate-600 leading-relaxed">
                {item.order_text}
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

function SubscriptionPanel({ onClose }) {
  const [subscriptions, setSubscriptions] = useState([]);
  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [courts, setCourts] = useState([]);
  const [selState, setSelState] = useState('');
  const [selDistrict, setSelDistrict] = useState('');
  const [selCourt, setSelCourt] = useState('');
  const [subLoading, setSubLoading] = useState(false);
  const [loadingSubs, setLoadingSubs] = useState(true);

  useEffect(() => {
    apiClient.get('todaysupdates/get-subscriptions/')
      .then((r) => setSubscriptions(r.data?.subscriptions ?? r.data ?? []))
      .catch(() => {})
      .finally(() => setLoadingSubs(false));
    apiClient.get('users/get-states/')
      .then((r) => {
        const raw = r.data?.states ?? r.data ?? [];
        setStates(raw.map((s) => (typeof s === 'string' ? s : s.name)));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selState) { setDistricts([]); setSelDistrict(''); return; }
    apiClient.get(`users/get-districts/?state_code=${encodeURIComponent(selState)}`)
      .then((r) => { 
        const raw = r.data?.districts ?? r.data ?? [];
        setDistricts(raw.map((d) => (typeof d === 'string' ? d : d.name)));
        setSelDistrict(''); setCourts([]); setSelCourt('');
      })
      .catch(() => {});
  }, [selState]);

  useEffect(() => {
    if (!selState || !selDistrict) { setCourts([]); setSelCourt(''); return; }
    apiClient.get(`users/get-courts/?state=${encodeURIComponent(selState)}&district=${encodeURIComponent(selDistrict)}`)
      .then((r) => { setCourts(r.data?.courts ?? r.data ?? []); setSelCourt(''); })
      .catch(() => {});
  }, [selState, selDistrict]);

  async function handleSubscribe() {
    if (!selCourt) return;
    setSubLoading(true);
    try {
      await apiClient.post('todaysupdates/subscribe-court/', { court: selCourt, state: selState, district: selDistrict });
      setSubscriptions((s) => [...s, { court: selCourt, state: selState, district: selDistrict }]);
      setSelCourt('');
    } catch (err) {
      alert(err.response?.data?.error || 'Could not subscribe.');
    } finally {
      setSubLoading(false);
    }
  }

  async function handleUnsubscribe(court) {
    if (!window.confirm(`Unsubscribe from ${court}?`)) return;
    try {
      await apiClient.post('todaysupdates/unsubscribe-court/', { court });
      setSubscriptions((s) => s.filter((x) => x.court !== court && x !== court));
    } catch {
      alert('Could not unsubscribe.');
    }
  }

  return (
    <aside className="w-80 border-l border-primary/10 bg-ivory flex flex-col flex-shrink-0">
      <div className="flex items-center justify-between p-5 border-b border-primary/10">
        <h3 className="font-bold text-sm text-ink flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-lg">notifications_active</span>
          Court Subscriptions
        </h3>
        <button onClick={onClose} className="p-1.5 hover:bg-primary/5 rounded-lg transition-colors">
          <span className="material-symbols-outlined text-slate-400">close</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar p-5 space-y-6">
        {/* Add new subscription */}
        <div className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Add Court</p>
          <div>
            <label className="block text-xs font-semibold mb-1 text-slate-700">State</label>
            <select
              value={selState}
              onChange={(e) => setSelState(e.target.value)}
              className="input-base"
            >
              <option value="">Select state…</option>
              {states.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold mb-1 text-slate-700">District</label>
            <select
              value={selDistrict}
              onChange={(e) => setSelDistrict(e.target.value)}
              disabled={!selState || districts.length === 0}
              className="input-base disabled:opacity-50"
            >
              <option value="">Select district…</option>
              {districts.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold mb-1 text-slate-700">Court</label>
            <select
              value={selCourt}
              onChange={(e) => setSelCourt(e.target.value)}
              disabled={!selDistrict || courts.length === 0}
              className="input-base disabled:opacity-50"
            >
              <option value="">Select court…</option>
              {courts.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <button
            onClick={handleSubscribe}
            disabled={!selCourt || subLoading}
            className="w-full btn-primary text-xs py-2 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-sm">add_alert</span>
            {subLoading ? 'Subscribing…' : 'Subscribe'}
          </button>
        </div>

        {/* Current subscriptions */}
        <div className="space-y-2">
          <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Subscribed Courts ({subscriptions.length})
          </p>
          {loadingSubs ? (
            [1, 2].map((i) => <div key={i} className="h-12 bg-slate-100 rounded-lg animate-pulse" />)
          ) : subscriptions.length === 0 ? (
            <p className="text-xs text-slate-400 text-center py-4">No subscriptions yet</p>
          ) : (
            subscriptions.map((sub, i) => {
              const court = sub.court || sub;
              const district = sub.district || '';
              const state = sub.state || '';
              return (
                <div key={i} className="flex items-center justify-between bg-white border border-primary/10 rounded-lg px-3 py-2">
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-ink truncate">{court}</p>
                    {(state || district) && (
                      <p className="text-[10px] text-slate-400">{[state, district].filter(Boolean).join(' · ')}</p>
                    )}
                  </div>
                  <button
                    onClick={() => handleUnsubscribe(court)}
                    className="flex-shrink-0 text-red-400 hover:text-red-600 transition-colors ml-2"
                    title="Unsubscribe"
                  >
                    <span className="material-symbols-outlined text-sm">notifications_off</span>
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>
    </aside>
  );
}

export default function CourtUpdates() {
  const [updates, setUpdates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [filter, setFilter] = useState('all'); // 'all' | 'today' | 'critical'
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [showSubscriptions, setShowSubscriptions] = useState(false);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({ page, page_size: 20 });
    if (filter === 'today') params.append('today', 'true');
    if (filter === 'critical') params.append('is_critical', 'true');

    apiClient.get(`todaysupdates/updates/?${params}`)
      .then((r) => {
        const res = r.data?.results ?? r.data ?? [];
        setUpdates(page === 1 ? res : (prev) => [...prev, ...res]);
        setHasMore(!!r.data?.next);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [filter, page]);

  function changeFilter(f) {
    setFilter(f);
    setPage(1);
    setUpdates([]);
    setSelected(null);
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-primary/10 flex-shrink-0">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-2xl font-black text-ink tracking-tight">Court Updates</h2>
              <p className="text-sm text-slate-500 mt-0.5">
                Real-time updates from your tracked cases
              </p>
            </div>
            <button
              onClick={() => { setShowSubscriptions((v) => !v); setSelected(null); }}
              className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg border transition-all ${
                showSubscriptions
                  ? 'bg-primary text-ivory border-primary'
                  : 'bg-ivory border-primary/10 text-slate-600 hover:text-primary hover:border-primary/30'
              }`}
            >
              <span className="material-symbols-outlined text-sm">notifications_active</span>
              Manage Subscriptions
            </button>
          </div>

          {/* Filter tabs */}
          <div className="flex gap-1">
            {[
              { key: 'all', label: 'All Updates' },
              { key: 'today', label: "Today's" },
              { key: 'critical', label: 'Critical' },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => changeFilter(tab.key)}
                className={`px-4 py-2 text-xs font-semibold rounded-lg transition-all ${
                  filter === tab.key
                    ? 'bg-primary text-ivory'
                    : 'bg-ivory border border-primary/10 text-slate-600 hover:text-primary hover:border-primary/30'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Updates list */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          <div className="bg-ivory rounded-0 border-x-0">
            {loading && updates.length === 0 ? (
              <div className="flex items-center justify-center h-64">
                <span className="material-symbols-outlined text-primary text-4xl animate-spin">progress_activity</span>
              </div>
            ) : updates.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-64 gap-3">
                <span className="material-symbols-outlined text-slate-300 text-5xl">notifications_none</span>
                <p className="text-slate-400 text-sm">No updates found</p>
                <button
                  className="btn-primary text-xs px-4 py-2 flex items-center gap-2"
                  onClick={() => setShowSubscriptions(true)}
                >
                  <span className="material-symbols-outlined text-sm">add_alert</span>
                  Subscribe to Courts
                </button>
              </div>
            ) : (
              updates.map((item) => (
                <UpdateRow
                  key={item.id || item._id}
                  item={item}
                  onClick={() => { setSelected(item); setShowSubscriptions(false); }}
                />
              ))
            )}
            {hasMore && (
              <div className="py-4 text-center">
                <button
                  className="btn-ghost"
                  onClick={() => setPage((p) => p + 1)}
                >
                  Load More
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Detail panel */}
      {selected && !showSubscriptions && (
        <UpdateDetail item={selected} onClose={() => setSelected(null)} />
      )}

      {/* Subscription panel */}
      {showSubscriptions && (
        <SubscriptionPanel onClose={() => setShowSubscriptions(false)} />
      )}
    </div>
  );
}
