import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import apiClient from '../../services/api';

function MetricCard({ label, value, sub, subColor }) {
  return (
    <div className="metric-card">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">{label}</p>
      <div className="flex items-end gap-2">
        <span className="text-3xl font-bold text-ink leading-none">{value}</span>
        {sub && (
          <span className={`text-xs font-bold mb-1 ${subColor || 'text-slate-400'}`}>{sub}</span>
        )}
      </div>
    </div>
  );
}

function AgendaItem({ time, title, subtitle, location, isActive }) {
  return (
    <div
      className={`bg-ivory p-4 rounded-xl border border-primary/10 shadow-sm border-l-4 ${
        isActive ? 'border-l-primary' : 'border-l-slate-300 opacity-80'
      }`}
    >
      <div className="flex justify-between items-start mb-2">
        <span
          className={`text-[10px] font-bold px-2 py-0.5 rounded ${
            isActive ? 'bg-primary/10 text-primary' : 'bg-slate-100 text-slate-600'
          }`}
        >
          {time}
        </span>
        {location && <span className="text-[10px] text-slate-400 font-medium">{location}</span>}
      </div>
      <h4 className="text-sm font-bold text-ink mb-1">{title}</h4>
      <p className="text-xs text-slate-500 line-clamp-1">{subtitle}</p>
    </div>
  );
}

function QuickActionCard({ icon, title, desc, to }) {
  const navigate = useNavigate();
  return (
    <button
      onClick={() => navigate(to)}
      className="action-card text-left w-full p-5"
    >
      <div className="size-10 bg-primary/10 rounded-lg flex items-center justify-center mb-3">
        <span className="material-symbols-outlined text-primary">{icon}</span>
      </div>
      <h4 className="text-sm font-bold text-ink mb-1">{title}</h4>
      <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
    </button>
  );
}

export default function Dashboard() {
  const { firstname } = useSelector((s) => s.user);
  const { planCode, trial, wallet, quotaResetAt, features } = useSelector((s) => s.entitlements);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    // Single aggregation call — GET /api/dashboard/home/
    apiClient.get('dashboard/home/')
      .then((r) => setData(r.data))
      .catch(() => setData({}))
      .finally(() => setLoading(false));
  }, []);

  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? 'Good Morning' : hour < 17 ? 'Good Afternoon' : 'Good Evening';

  const draftCount = data?.pending_drafts ?? '—';
  const agendaItems = data?.upcoming_events_list ?? [];
  const agendaCount = data?.upcoming_events ?? 0;
  const updateItems = data?.recent_updates ?? [];
  const recentDrafts = data?.recent_drafts ?? [];
  const brainQuota = features?.brain_doc_analysis;
  const legalChatQuota = features?.general_legal_chat;
  const draftingQuota = features?.brain_drafting_actions;
  const quotaDateLabel = quotaResetAt ? new Date(quotaResetAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) : '';

  return (
    <div className="p-8 space-y-8 max-w-7xl">
      {/* ── Welcome & Metrics ────────────────────────────────── */}
      <section>
        <div className="mb-6">
          <h2 className="text-2xl font-black text-ink tracking-tight">
            {greeting}, {firstname || 'Counselor'}
          </h2>
          <p className="text-slate-500 text-sm mt-1">
            Here&apos;s your legal workspace overview for today.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Pending Drafts"
            value={loading ? '…' : draftCount}
            sub="High Priority"
            subColor="text-primary"
          />
          <MetricCard
            label="Court Dates (30d)"
            value={loading ? '…' : (agendaCount || '—')}
            sub="This Week"
          />
          <MetricCard
            label="New Updates"
            value={loading ? '…' : (updateItems.length || 0)}
            sub="Today"
            subColor="text-emerald-600"
          />
          <MetricCard
            label="AI Efficiency"
            value="84%"
            sub="↑ 12%"
            subColor="text-emerald-600"
          />
        </div>

        {planCode && (
          <div className="mt-4 rounded-2xl border border-primary/10 bg-white px-5 py-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-primary">Mamla Brain Access</p>
                <h3 className="mt-2 text-lg font-bold text-ink">
                  {trial?.active ? 'Trial access is active' : `${String(planCode).replace(/_/g, ' ')} plan active`}
                </h3>
                <p className="mt-1 text-sm text-slate-500">
                  {typeof brainQuota?.remaining_included === 'number' ? `${brainQuota.remaining_included} document analyses left` : 'Brain quota will appear here'}
                  {typeof legalChatQuota?.remaining_included === 'number' ? ` · ${legalChatQuota.remaining_included} general legal chats left` : ''}
                  {typeof draftingQuota?.remaining_included === 'number' ? ` · ${draftingQuota.remaining_included} drafting actions left` : ''}
                  {quotaDateLabel ? ` · resets ${quotaDateLabel}` : ''}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {typeof brainQuota?.remaining_included === 'number' && (
                  <span className="rounded-full bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary">
                    {brainQuota.remaining_included} doc analyses
                  </span>
                )}
                {typeof legalChatQuota?.remaining_included === 'number' && (
                  <span className="rounded-full bg-amber-100 px-3 py-1.5 text-xs font-semibold text-amber-800">
                    {legalChatQuota.remaining_included} legal chats
                  </span>
                )}
                {typeof draftingQuota?.remaining_included === 'number' && (
                  <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">
                    {draftingQuota.remaining_included} drafting actions
                  </span>
                )}
                <span className="rounded-full bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary">
                  {wallet?.balance ?? 0} credits available
                </span>
                <button className="rounded-xl border border-primary/15 px-4 py-2 text-xs font-semibold text-slate-700 transition-colors hover:bg-primary/5">
                  {trial?.active ? 'Review Trial Limits' : 'Review Plan Limits'}
                </button>
              </div>
            </div>
          </div>
        )}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* ── Today's Agenda ─────────────────────────────────── */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-ink flex items-center gap-2 uppercase tracking-wide text-xs">
              <span className="material-symbols-outlined text-primary text-lg">event_note</span>
              Today's Agenda
            </h3>
            <Link to="/calendar" className="text-primary text-[10px] font-bold uppercase hover:underline">
              View Calendar
            </Link>
          </div>

          <div className="space-y-3">
            {loading ? (
              [1, 2, 3].map((i) => (
                <div key={i} className="h-20 bg-ivory rounded-xl border border-primary/10 animate-pulse" />
              ))
            ) : agendaItems.length > 0 ? (
              agendaItems.slice(0, 4).map((item, i) => {
                const startDate = item.start ? new Date(item.start) : null;
                const timeStr = startDate
                  ? startDate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
                  : '—';
                return (
                  <AgendaItem
                    key={item.id || i}
                    time={timeStr}
                    title={item.title || 'Event'}
                    subtitle={item.description || item.event_type || ''}
                    location={item.location}
                    isActive={i === 0}
                  />
                );
              })
            ) : (
              <div className="bg-ivory border border-primary/10 rounded-xl p-6 text-center">
                <span className="material-symbols-outlined text-slate-300 text-3xl">event_busy</span>
                <p className="text-xs text-slate-400 mt-2">No upcoming events</p>
                <button
                  className="btn-primary mt-3 text-xs px-4 py-2"
                  onClick={() => navigate('/calendar')}
                >
                  Add Event
                </button>
              </div>
            )}
          </div>
        </div>

        {/* ── Quick Actions ───────────────────────────────────── */}
        <div className="space-y-4">
          <h3 className="font-bold text-ink flex items-center gap-2 uppercase tracking-wide text-xs">
            <span className="material-symbols-outlined text-primary text-lg">bolt</span>
            Quick Actions
          </h3>
          <div className="grid grid-cols-1 gap-3">
            <QuickActionCard
              icon="edit_note"
              title="New AI Draft"
              desc="Generate a legal document with AI assistance"
              to="/drafting"
            />
            <QuickActionCard
              icon="description"
              title="Upload & Analyse"
              desc="Upload documents for AI-powered analysis"
              to="/documents"
            />
            <QuickActionCard
              icon="search"
              title="eCourts Search"
              desc="Search cases, lawyers, and cause lists"
              to="/ecourts/case-search"
            />
          </div>
        </div>

        {/* ── Court Updates Feed ──────────────────────────────── */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-ink flex items-center gap-2 uppercase tracking-wide text-xs">
              <span className="material-symbols-outlined text-primary text-lg">dynamic_feed</span>
              Court Updates
            </h3>
            <Link to="/court-updates" className="text-primary text-[10px] font-bold uppercase hover:underline">
              View All
            </Link>
          </div>

          <div className="space-y-3">
            {loading ? (
              [1, 2, 3].map((i) => (
                <div key={i} className="h-16 bg-ivory rounded-xl border border-primary/10 animate-pulse" />
              ))
            ) : updateItems.length > 0 ? (
              updateItems.slice(0, 4).map((item, i) => (
                <div
                  key={item.id || i}
                  className="bg-ivory p-3 rounded-xl border border-primary/10 cursor-pointer hover:border-primary/30 transition-colors"
                  onClick={() => navigate('/court-updates')}
                >
                  <div className="flex items-start gap-2">
                    <div className="size-7 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                      <span className="material-symbols-outlined text-primary text-sm">update</span>
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-ink line-clamp-1">{item.case_title || item.title}</p>
                      <p className="text-[10px] text-slate-500 mt-0.5">{item.status || item.detail || item.update_type || 'Status update'}</p>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="bg-ivory border border-primary/10 rounded-xl p-6 text-center">
                <span className="material-symbols-outlined text-slate-300 text-3xl">notifications_none</span>
                <p className="text-xs text-slate-400 mt-2">No updates today</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Recent Drafts ────────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-ink flex items-center gap-2 uppercase tracking-wide text-xs">
            <span className="material-symbols-outlined text-primary text-lg">edit_document</span>
            Recent Drafts
          </h3>
          <Link to="/drafting" className="text-primary text-[10px] font-bold uppercase hover:underline">
            View All
          </Link>
        </div>

        <div className="bg-ivory rounded-2xl border border-primary/10 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="table-header">
                <th className="px-6 py-3 text-left">Document</th>
                <th className="px-6 py-3 text-left hidden md:table-cell">Type</th>
                <th className="px-6 py-3 text-left hidden lg:table-cell">Modified</th>
                <th className="px-6 py-3 text-left">Status</th>
                <th className="px-6 py-3 text-right"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-primary/5">
              {loading ? (
                [1, 2, 3].map((i) => (
                  <tr key={i}>
                    <td colSpan={5} className="px-6 py-4">
                      <div className="h-4 bg-slate-100 rounded animate-pulse w-3/4" />
                    </td>
                  </tr>
                ))
              ) : recentDrafts.length > 0 ? (
                recentDrafts.map((draft) => (
                  <tr
                    key={draft.session_id || draft.draft_name}
                    className="hover:bg-primary/5 cursor-pointer transition-colors"
                    onClick={() => navigate(draft.session_id ? `/drafting/${draft.session_id}` : '/drafting')}
                  >
                    <td className="px-6 py-4">
                      <span className="font-medium text-ink">{draft.draft_name || 'Untitled Draft'}</span>
                    </td>
                    <td className="px-6 py-4 text-slate-500 hidden md:table-cell">{draft.status || '—'}</td>
                    <td className="px-6 py-4 text-slate-500 hidden lg:table-cell">
                      {draft.created_at ? new Date(draft.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="px-6 py-4">
                      <span className="badge-pending">{draft.status || 'Draft'}</span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="material-symbols-outlined text-slate-400 text-lg">chevron_right</span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center">
                    <span className="material-symbols-outlined text-slate-300 text-4xl block mb-2">edit_note</span>
                    <p className="text-sm text-slate-400">No drafts yet.</p>
                    <button
                      className="btn-primary mt-3 text-xs px-4 py-2"
                      onClick={() => navigate('/drafting')}
                    >
                      Create First Draft
                    </button>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
