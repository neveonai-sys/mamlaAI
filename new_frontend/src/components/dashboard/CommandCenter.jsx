import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import apiClient from '../../services/api';

const PRIORITY_COLORS = {
  critical: 'bg-red-50 border-red-200 text-red-700',
  high: 'bg-amber-50 border-amber-200 text-amber-700',
  medium: 'bg-blue-50 border-blue-200 text-blue-700',
  low: 'bg-slate-50 border-slate-200 text-slate-600',
};

function PriorityBadge({ level }) {
  const colors = PRIORITY_COLORS[level] || PRIORITY_COLORS.medium;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${colors}`}>
      {level}
    </span>
  );
}

function StatCard({ label, value, icon, trend, trendColor }) {
  return (
    <div className="bg-ivory border border-primary/10 rounded-xl p-5 shadow-sm">
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{label}</p>
        <div className="size-7 bg-primary/10 rounded-lg flex items-center justify-center">
          <span className="material-symbols-outlined text-primary text-sm">{icon}</span>
        </div>
      </div>
      <div className="flex items-end gap-2">
        <span className="text-3xl font-black text-ink leading-none">{value}</span>
        {trend && (
          <span className={`text-xs font-bold mb-1 ${trendColor || 'text-slate-400'}`}>{trend}</span>
        )}
      </div>
    </div>
  );
}

export default function CommandCenter() {
  const { firstname } = useSelector((s) => s.user);
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      apiClient.get('aidrafts/list/?page_size=10'),
      apiClient.get('calendar/events/?upcoming=true&page_size=5'),
      apiClient.get('todaysupdates/updates/?page_size=5'),
    ]).then(([drafts, events, updates]) => {
      setData({
        drafts: drafts.status === 'fulfilled' ? drafts.value.data : { count: 0, results: [] },
        events: events.status === 'fulfilled' ? events.value.data : { results: [] },
        updates: updates.status === 'fulfilled' ? updates.value.data : { results: [] },
      });
    }).finally(() => setLoading(false));
  }, []);

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : 'evening';

  const drafts = data?.drafts?.results ?? [];
  const events = data?.events?.results ?? [];
  const updates = data?.updates?.results ?? [];

  return (
    <div className="flex-1 overflow-y-auto p-8 custom-scrollbar max-w-7xl">
      {/* ── Welcome ──────────────────────────────────────────── */}
      <section className="mb-10">
        <h2 className="text-3xl font-black text-ink tracking-tight">
          Good {greeting}, Counselor.
        </h2>
        <p className="text-ink/60 mt-1 flex items-center gap-2 text-sm">
          <span className="material-symbols-outlined text-primary text-sm">warning</span>
          You have{' '}
          <span className="font-bold text-ink underline decoration-primary/40 underline-offset-4">
            {loading ? '…' : `${drafts.length} pending drafts`}
          </span>{' '}
          requiring attention today.
        </p>
      </section>

      {/* ── Stats Row ────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        <StatCard
          label="Active Drafts"
          value={loading ? '…' : (data?.drafts?.count ?? '—')}
          icon="edit_note"
          trend="Today"
        />
        <StatCard
          label="Court Dates"
          value={loading ? '…' : (events.length || '—')}
          icon="gavel"
          trend="Upcoming"
          trendColor="text-primary"
        />
        <StatCard
          label="New Updates"
          value={loading ? '…' : (updates.length || '—')}
          icon="dynamic_feed"
          trend="↑ Fresh"
          trendColor="text-emerald-600"
        />
        <StatCard
          label="AI Efficiency"
          value="84%"
          icon="auto_awesome"
          trend="↑ 12%"
          trendColor="text-emerald-600"
        />
      </div>

      <div className="grid grid-cols-12 gap-8">
        {/* ── Left: Priority Drafts + Deadlines ─────────────── */}
        <div className="col-span-12 lg:col-span-8 space-y-8">
          {/* Priority Drafts */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-ink flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">priority_high</span>
                Priority Drafts
              </h3>
              <button
                className="text-xs font-bold text-primary uppercase tracking-wider hover:underline"
                onClick={() => navigate('/drafting')}
              >
                View All
              </button>
            </div>

            <div className="space-y-3">
              {loading ? (
                [1, 2, 3].map((i) => (
                  <div key={i} className="h-20 bg-ivory rounded-xl border border-primary/10 animate-pulse" />
                ))
              ) : drafts.length > 0 ? (
                drafts.slice(0, 5).map((draft, i) => (
                  <div
                    key={draft.session_id || draft.id || i}
                    className="bg-ivory border border-primary/10 rounded-xl p-4 cursor-pointer hover:border-primary/30 transition-all flex items-center gap-4"
                    onClick={() => navigate(`/drafting/${draft.session_id || draft.id}`)}
                  >
                    <div className="size-10 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
                      <span className="material-symbols-outlined text-primary">description</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="font-bold text-sm text-ink truncate">
                          {draft.draft_name || draft.title || 'Untitled Draft'}
                        </span>
                        <PriorityBadge level={i === 0 ? 'critical' : i === 1 ? 'high' : 'medium'} />
                      </div>
                      <p className="text-xs text-slate-500">
                        {draft.status || 'Draft'} ·{' '}
                        {draft.created_at ? new Date(draft.created_at).toLocaleDateString() : '—'}
                      </p>
                    </div>
                    <span className="material-symbols-outlined text-slate-400">chevron_right</span>
                  </div>
                ))
              ) : (
                <div className="bg-ivory border border-primary/10 rounded-xl p-8 text-center">
                  <span className="material-symbols-outlined text-slate-300 text-4xl block mb-2">edit_note</span>
                  <p className="text-sm text-slate-400">No pending drafts</p>
                  <button
                    className="btn-primary mt-3 text-xs px-4 py-2"
                    onClick={() => navigate('/drafting')}
                  >
                    Start New Draft
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Court Updates */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-ink flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">dynamic_feed</span>
                Latest Court Updates
              </h3>
              <Link
                to="/court-updates"
                className="text-xs font-bold text-primary uppercase tracking-wider hover:underline"
              >
                View All
              </Link>
            </div>

            <div className="bg-ivory rounded-xl border border-primary/10 overflow-hidden">
              {loading ? (
                <div className="p-6 space-y-3">
                  {[1, 2, 3].map((i) => <div key={i} className="h-10 bg-slate-100 rounded animate-pulse" />)}
                </div>
              ) : updates.length > 0 ? (
                <div className="divide-y divide-primary/5">
                  {updates.map((u, i) => (
                    <div
                      key={u.id || i}
                      className="flex items-start gap-3 px-5 py-4 hover:bg-primary/5 cursor-pointer transition-colors"
                      onClick={() => navigate('/court-updates')}
                    >
                      <span className="material-symbols-outlined text-primary text-lg flex-shrink-0 mt-0.5">
                        {u.is_critical ? 'warning' : 'update'}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-ink line-clamp-1">
                          {u.case_title || u.title || 'Court Update'}
                        </p>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {u.court || u.detail || u.update_type || 'Status update'}
                        </p>
                      </div>
                      <span className="text-[10px] text-slate-400 flex-shrink-0">
                        {u.date ? new Date(u.date).toLocaleDateString() : 'Today'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center">
                  <span className="material-symbols-outlined text-slate-300 text-3xl block mb-2">notifications_none</span>
                  <p className="text-xs text-slate-400">No updates available</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Right: Agenda ────────────────────────────────────── */}
        <div className="col-span-12 lg:col-span-4 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-ink flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">event_note</span>
              Upcoming Events
            </h3>
            <Link
              to="/calendar"
              className="text-xs font-bold text-primary uppercase tracking-wider hover:underline"
            >
              Calendar
            </Link>
          </div>

          <div className="space-y-3">
            {loading ? (
              [1, 2, 3].map((i) => (
                <div key={i} className="h-20 bg-ivory rounded-xl border border-primary/10 animate-pulse" />
              ))
            ) : events.length > 0 ? (
              events.map((ev, i) => {
                const startDate = ev.start ? new Date(ev.start) : null;
                const timeStr = startDate
                  ? startDate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
                  : ev.start_time || ev.time || 'TBD';
                return (
                  <div
                    key={ev.id || i}
                    className={`bg-ivory p-4 rounded-xl border border-primary/10 shadow-sm border-l-4 ${
                      i === 0 ? 'border-l-primary' : 'border-l-slate-300'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          i === 0 ? 'bg-primary/10 text-primary' : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {timeStr}
                      </span>
                      {ev.location && (
                        <span className="text-[10px] text-slate-400">{ev.location}</span>
                      )}
                    </div>
                    <p className="text-sm font-bold text-ink mt-1">{ev.title}</p>
                    {(ev.description || ev.event_type) && (
                      <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">
                        {ev.description || ev.event_type}
                      </p>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="bg-ivory border border-primary/10 rounded-xl p-6 text-center">
                <span className="material-symbols-outlined text-slate-300 text-3xl">event_busy</span>
                <p className="text-xs text-slate-400 mt-2">No upcoming events</p>
              </div>
            )}
          </div>

          {/* Quick actions */}
          <div className="pt-4 space-y-2">
            <button
              className="w-full btn-primary text-xs py-3 flex items-center justify-center gap-2"
              onClick={() => navigate('/drafting')}
            >
              <span className="material-symbols-outlined text-base">add</span>
              New AI Draft
            </button>
            <button
              className="w-full btn-ghost text-xs py-3 border border-primary/20 rounded-lg flex items-center justify-center gap-2"
              onClick={() => navigate('/ecourts/case-search')}
            >
              <span className="material-symbols-outlined text-base">search</span>
              Search eCourts
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
