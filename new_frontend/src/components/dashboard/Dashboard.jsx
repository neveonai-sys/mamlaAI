import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import apiClient from '../../services/api';
import WelcomeModal from '../common/WelcomeModal';

function MetricCard({ label, value, sub, subColor, loading }) {
  return (
    <div className="metric-card">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">{label}</p>
      <div className="flex items-end gap-2">
        {loading
          ? <span className="inline-block h-8 w-14 rounded-md bg-slate-200 animate-pulse" />
          : <span className="text-3xl font-bold text-ink leading-none">{value}</span>
        }
        {sub && !loading && (
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

const QUOTA_FEATURE_META = [
  { code: 'general_legal_chat',     label: 'Legal Chat',       icon: 'forum',        lawyerOnly: false },
  { code: 'brain_doc_analysis',     label: 'Doc Analysis',     icon: 'description',  lawyerOnly: false },
  { code: 'ai_draft_generation',    label: 'AI Drafts',        icon: 'auto_awesome', lawyerOnly: false },
  { code: 'brain_drafting_actions', label: 'Drafting Actions', icon: 'edit_note',    lawyerOnly: true  },
  { code: 'case_companion',         label: 'Case Companion',   icon: 'psychology',   lawyerOnly: true  },
  { code: 'ai_suggestions',         label: 'AI Suggestions',   icon: 'lightbulb',    lawyerOnly: true  },
  { code: 'ecourts_case_lookup',    label: 'eCourts Lookup',   icon: 'gavel',        lawyerOnly: false },
  { code: 'ecourts_order_download', label: 'Order Downloads',  icon: 'download',     lawyerOnly: false },
];

export default function Dashboard() {
  const { firstname, email, user_type } = useSelector((s) => s.user);
  const { planCode, trial, wallet, usageSummary, quotaResetAt, features } = useSelector((s) => s.entitlements);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const [savedDrafts, setSavedDrafts] = useState([]);
  const [showWelcome, setShowWelcome] = useState(false);

  // Show welcome modal once per account
  useEffect(() => {
    if (!email || !planCode) return;
    const key = `mamla_welcome_shown_${email}`;
    if (!localStorage.getItem(key)) {
      setShowWelcome(true);
    }
  }, [email, planCode]);

  useEffect(() => {
    // Fetch dashboard summary and actual saved drafts in parallel
    Promise.allSettled([
      apiClient.get('dashboard/home/'),
      apiClient.get('aidrafts/get_user_saved_drafts_v2?page_size=5'),
    ]).then(([homeRes, draftsRes]) => {
      setData(homeRes.status === 'fulfilled' ? homeRes.value.data : {});
      if (draftsRes.status === 'fulfilled') {
        setSavedDrafts(draftsRes.value.data?.saved_drafts ?? []);
      }
    }).finally(() => setLoading(false));
  }, []);

  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? 'Good Morning' : hour < 17 ? 'Good Afternoon' : 'Good Evening';

  const draftCount = savedDrafts.length || data?.pending_drafts || '—';
  const agendaItems = data?.upcoming_events_list ?? [];
  const agendaCount = data?.upcoming_events ?? 0;
  const updateItems = data?.recent_updates ?? [];
  const recentDrafts = savedDrafts;
  const brainQuota = features?.brain_doc_analysis;
  const legalChatQuota = features?.general_legal_chat;
  const draftingQuota = features?.brain_drafting_actions;
  const quotaDateLabel = quotaResetAt ? new Date(quotaResetAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) : '';
  const daysRemaining = trial?.daysRemaining ?? 0;
  const trialExpired = !trial?.active && planCode === 'locked';
  const trialEndingSoon = trial?.active && daysRemaining <= 3;
  const allFeaturesExhausted = Object.keys(features || {}).length > 0
    && Object.values(features || {}).every((f) => (f.remaining_included ?? 1) === 0);
  const trialEndsLabel = trial?.endsAt
    ? new Date(trial.endsAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
    : '';

  const isLawyerUser = user_type !== 'Client';

  return (
    <div className="p-8 space-y-8 max-w-7xl">
      {showWelcome && (
        <WelcomeModal
          userType={user_type}
          email={email}
          planCode={planCode}
          trialEndsAt={trial?.endsAt}
          onClose={() => setShowWelcome(false)}
        />
      )}
      {/* ── Welcome & Metrics ────────────────────────────────── */}
      <section>
        <div className="mb-6">
          <h2 className="text-2xl font-black text-ink tracking-tight">
            {greeting}, {firstname || (isLawyerUser ? 'Counselor' : 'there')}
          </h2>
          <p className="text-slate-500 text-sm mt-1">
            {isLawyerUser
              ? "Here\u2019s your legal workspace overview for today."
              : "Here\u2019s your case and document overview."}
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Pending Drafts"
            value={draftCount}
            sub="High Priority"
            subColor="text-primary"
            loading={loading}
          />
          <MetricCard
            label="Court Dates (30d)"
            value={agendaCount || '—'}
            sub="This Week"
            loading={loading}
          />
          <MetricCard
            label="New Updates"
            value={updateItems.length || 0}
            sub="Today"
            subColor="text-emerald-600"
            loading={loading}
          />
          <button
            onClick={() => navigate('/wallet')}
            className="metric-card text-left w-full hover:ring-2 hover:ring-emerald-200 transition-all"
          >
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Wallet Credits</p>
            <div className="flex items-end gap-2">
              {loading
                ? <span className="inline-block h-8 w-14 rounded-md bg-slate-200 animate-pulse" />
                : <span className="text-3xl font-bold text-ink leading-none">{wallet?.balance ?? '—'}</span>
              }
              <span className="text-xs font-bold mb-1 text-emerald-600">Available</span>
            </div>
            {!loading && wallet?.inrEquivalent > 0 && (
              <p className="mt-0.5 text-[11px] text-slate-400">≈ ₹{wallet.inrEquivalent}</p>
            )}
            {!loading && trial?.active && (usageSummary?.trialValueInr ?? 0) > 0 && (
              <p className="mt-0.5 text-[11px] text-indigo-500">Trial used: ≈ ₹{usageSummary.trialValueInr}</p>
            )}
            <p className="mt-1 text-[10px] text-slate-400 underline">View details →</p>
          </button>
        </div>

        {planCode && (
          <div className={`mt-4 rounded-2xl border px-5 py-4 shadow-sm ${
            trialExpired ? 'border-red-200 bg-red-50' :
            trialEndingSoon ? 'border-amber-200 bg-amber-50' :
            'border-primary/10 bg-white'
          }`}>
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.22em] text-primary">Mamla Brain Access</p>
                <h3 className={`mt-2 text-lg font-bold ${
                  trialExpired ? 'text-red-700' : trialEndingSoon ? 'text-amber-700' : 'text-ink'
                }`}>
                  {trialExpired
                    ? 'Trial ended — upgrade to continue'
                    : trialEndingSoon
                    ? `Trial ending soon — ${daysRemaining} day${daysRemaining === 1 ? '' : 's'} left`
                    : trial?.active
                    ? 'Trial access is active'
                    : allFeaturesExhausted
                    ? 'Credits used up this cycle'
                    : `${String(planCode).replace(/_/g, ' ')} plan active`}
                </h3>
                <p className="mt-1 text-sm text-slate-500">
                  {trialExpired && 'Your 30-day trial has ended. Upgrade to keep using Mamla Brain.'}
                  {trialEndingSoon && `Trial expires on ${trialEndsLabel}. Upgrade now to avoid interruption.`}
                  {!trialExpired && !trialEndingSoon && trial?.active && `${daysRemaining} day${daysRemaining === 1 ? '' : 's'} remaining · expires ${trialEndsLabel}`}
                  {!trialExpired && !trialEndingSoon && !trial?.active && allFeaturesExhausted && 'All included AI quota used. Top up wallet credits or upgrade your plan.'}
                  {!trialExpired && !trialEndingSoon && !trial?.active && !allFeaturesExhausted && (typeof brainQuota?.remaining_included === 'number' ? `${brainQuota.remaining_included} document analyses left` : 'Brain quota will appear here')}
                  {!trialExpired && !trialEndingSoon && !trial?.active && !allFeaturesExhausted && typeof legalChatQuota?.remaining_included === 'number' && ` · ${legalChatQuota.remaining_included} general legal chats left`}
                  {!trialExpired && !trialEndingSoon && !trial?.active && !allFeaturesExhausted && typeof draftingQuota?.remaining_included === 'number' && ` · ${draftingQuota.remaining_included} drafting actions left`}
                  {!trialExpired && !trialEndingSoon && !trial?.active && !allFeaturesExhausted && quotaDateLabel && ` · resets ${quotaDateLabel}`}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {!trialExpired && typeof brainQuota?.remaining_included === 'number' && (
                  <span className="rounded-full bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary">
                    {brainQuota.remaining_included} doc analyses
                  </span>
                )}
                {!trialExpired && typeof legalChatQuota?.remaining_included === 'number' && (
                  <span className="rounded-full bg-amber-100 px-3 py-1.5 text-xs font-semibold text-amber-800">
                    {legalChatQuota.remaining_included} legal chats
                  </span>
                )}
                {!trialExpired && typeof draftingQuota?.remaining_included === 'number' && (
                  <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600">
                    {draftingQuota.remaining_included} drafting actions
                  </span>
                )}
                <span className="rounded-full bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary">
                  {wallet?.balance ?? 0} credits available
                </span>
                <button
                  onClick={() => navigate('/wallet')}
                  className={`rounded-xl border px-4 py-2 text-xs font-semibold transition-colors ${
                    trialExpired || (allFeaturesExhausted && planCode === 'locked')
                      ? 'border-primary bg-primary text-white hover:bg-primary-dark hover:border-primary-dark'
                      : 'border-primary/15 text-slate-700 hover:bg-primary/5'
                  }`}>
                  {trialExpired || (allFeaturesExhausted && planCode === 'locked')
                    ? 'Upgrade Now'
                    : allFeaturesExhausted
                    ? 'Add Credits'
                    : trial?.active
                    ? 'Review Trial Limits'
                    : 'Review Plan Limits'}
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
              icon="search"
              title="eCourts Search"
              desc="Search cases, lawyers, and cause lists"
              to="/ecourts/case-search"
            />
            <QuickActionCard
              icon="gavel"
              title="Citation Search"
              desc="Verify Supreme Court citations against e-SCR"
              to="/citations"
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
                <th className="px-6 py-3 text-left hidden md:table-cell">Client</th>
                <th className="px-6 py-3 text-left hidden lg:table-cell">Last Updated</th>
                <th className="px-6 py-3 text-right"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-primary/5">
              {loading ? (
                [1, 2, 3].map((i) => (
                  <tr key={i}>
                    <td colSpan={4} className="px-6 py-4">
                      <div className="h-4 bg-slate-100 rounded animate-pulse w-3/4" />
                    </td>
                  </tr>
                ))
              ) : recentDrafts.length > 0 ? (
                recentDrafts.map((draft, i) => {
                    const clientName = Array.isArray(draft.draft_for) && draft.draft_for.length > 0
                      ? draft.draft_for.map((c) => c.client_name).filter(Boolean).join(', ')
                      : '—';
                    const displayName = draft.draft_name || 'Untitled Draft';
                    const updatedOn = draft.last_updated_on || draft.created_on;
                    return (
                  <tr
                    key={draft.draft_id || draft.session_id || i}
                    className="hover:bg-primary/5 cursor-pointer transition-colors"
                    onClick={() => navigate(draft.session_id ? `/drafting/${draft.session_id}` : '/drafting')}
                  >
                    <td className="px-6 py-4">
                      <span className="font-medium text-ink">{displayName}</span>
                    </td>
                    <td className="px-6 py-4 text-slate-500 hidden md:table-cell">{clientName}</td>
                    <td className="px-6 py-4 text-slate-500 hidden lg:table-cell">
                      {updatedOn ? new Date(updatedOn).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className="material-symbols-outlined text-slate-400 text-lg">chevron_right</span>
                    </td>
                  </tr>
                    );
                  })
              ) : (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center">
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

      {/* ── AI Usage This Month ──────────────────────────── */}
      {planCode && Object.keys(features || {}).length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold text-ink flex items-center gap-2 uppercase tracking-wide text-xs">
              <span className="material-symbols-outlined text-primary text-lg">analytics</span>
              AI Usage This Month
            </h3>
            {quotaDateLabel && (
              <span className="text-[10px] text-slate-400 font-medium">resets {quotaDateLabel}</span>
            )}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
            {QUOTA_FEATURE_META.map(({ code, label, icon, lawyerOnly }) => {
              const f = features?.[code];
              if (!f) return null;
              // For Nagrik users, show lawyer-only features as greyed-out unavailable cards
              if (lawyerOnly && !isLawyerUser) {
                return (
                  <div key={code} className="rounded-xl border border-slate-100 bg-slate-50 p-3.5 flex flex-col gap-2 opacity-60">
                    <div className="flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-slate-300" style={{ fontSize: '15px' }}>{icon}</span>
                      <span className="text-[11px] font-semibold text-slate-400 leading-tight">{label}</span>
                    </div>
                    <span className="inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-400 self-start">Lawyer plan only</span>
                  </div>
                );
              }
              const limit = f.included_limit ?? 0;
              const used = f.used_count ?? 0;
              const remaining = f.remaining_included ?? Math.max(limit - used, 0);
              const isUnlimited = limit >= 1000000;
              const isLocked = !isUnlimited && limit === 0 && Boolean(f.hard_block);
              const pct = isUnlimited ? 0 : limit > 0 ? Math.min((used / limit) * 100, 100) : 100;
              const barColor = pct >= 90 ? 'bg-red-400' : pct >= 70 ? 'bg-amber-400' : 'bg-emerald-400';
              const remainingColor = pct >= 90 ? 'text-red-600' : pct >= 70 ? 'text-amber-600' : 'text-emerald-700';
              return (
                <div key={code} className="rounded-xl border border-primary/10 bg-white p-3.5 shadow-sm flex flex-col gap-2">
                  <div className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-primary" style={{ fontSize: '15px' }}>{icon}</span>
                    <span className="text-[11px] font-semibold text-slate-600 leading-tight">{label}</span>
                  </div>
                  {isLocked ? (
                    <span className="inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-400 self-start">Not in plan</span>
                  ) : isUnlimited ? (
                    <span className="inline-block rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-700 self-start">∞ Unlimited</span>
                  ) : (
                    <>
                      <div className="flex items-end justify-between">
                        <span className={`text-xl font-black leading-none ${remainingColor}`}>{remaining}</span>
                        <span className="text-[10px] text-slate-400 mb-0.5">/ {limit}</span>
                      </div>
                      <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <p className="text-[10px] text-slate-400">
                        {used} used{f.overage_credit_cost > 0 ? ` · ${f.overage_credit_cost} cr/extra` : ''}
                      </p>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
