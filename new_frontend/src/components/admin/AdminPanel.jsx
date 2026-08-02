import React, { useCallback, useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../services/api';

const ALLOWED_TYPES = new Set(['owner', 'admin', 'Owner', 'Admin']);
const ADMIN_EMAILS = (process.env.REACT_APP_ADMIN_EMAILS || '')
  .split(',').map((e) => e.trim()).filter(Boolean);

const PAGE_SIZE = 25;

const PLAN_LABELS = {
  trial:          'Trial',
  law_student:    'Law Student — ₹220/mo',
  basic:          'Basic — ₹1,000/mo',
  premium:        'Premium — ₹3,000/mo',
  vakil_starter:  'Vakil Starter — ₹349/mo (legacy)',
  vakil_pro:      'Vakil Pro — ₹749/mo (legacy)',
  vakil_power:    'Vakil Power — ₹1,349/mo (legacy)',
  nagrik_free:    'Nagrik Free',
  nagrik_basic:   'Nagrik Basic — ₹129/mo',
  firm_basic:     'Firm Basic — ₹2,049/mo/seat',
  firm_pro:       'Firm Pro — ₹4,549/mo/seat',
  pro:            'Pro',
  enterprise:     'Enterprise',
  internal:       'Internal (staff)',
  locked:         'Locked (no access)',
};

const FEATURE_LABELS = {
  brain_doc_analysis:     'Document Analysis',
  general_legal_chat:     'Legal Chat',
  brain_drafting_actions: 'Drafting Actions',
  case_companion:         'Case Companion',
  ai_suggestions:         'AI Suggestions',
  ai_draft_generation:    'AI Draft Generation',
  ecourts_case_lookup:    'eCourts CNR Lookup',
  ecourts_order_download: 'eCourts Order Download',
};

function PlanBadge({ planCode }) {
  const isLocked = planCode === 'locked';
  const isNone = !planCode;
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
        isNone ? 'bg-slate-100 text-slate-500' : isLocked ? 'bg-rose-100 text-rose-700' : 'bg-emerald-100 text-emerald-700'
      }`}
    >
      {planCode ? (PLAN_LABELS[planCode] || planCode) : 'No plan'}
    </span>
  );
}

function formatDate(value) {
  return value ? new Date(value).toLocaleDateString('en-IN') : '—';
}

const COLUMNS = [
  { key: 'name',                   label: 'Name / Email' },
  { key: 'user_type',              label: 'Type' },
  { key: 'plan_code',              label: 'Package' },
  { key: 'wallet_credits_balance', label: 'Wallet', align: 'right' },
  { key: 'tokens_30d',             label: 'Tokens (30d)', align: 'right' },
  { key: 'joined_at',              label: 'Joined' },
  { key: 'last_active',            label: 'Last active' },
];

function FeatureUsageRow({ code, feature }) {
  const label       = FEATURE_LABELS[code] || code;
  const used        = feature?.used_count ?? 0;
  const limit       = feature?.included_limit ?? 0;
  const isUnlimited = limit >= 1000000;
  const isBlocked   = feature?.hard_block;
  const pct         = isUnlimited || isBlocked || limit === 0 ? 0 : Math.min((used / limit) * 100, 100);
  const exhausted   = !isUnlimited && !isBlocked && limit > 0 && used >= limit;

  return (
    <div>
      <div className="flex items-center justify-between text-xs">
        <span className={`font-medium ${isBlocked ? 'text-gray-400' : 'text-gray-700'}`}>
          {label}
          {isBlocked && <span className="ml-1 text-[10px] text-gray-400">(plan restricted)</span>}
        </span>
        <span className={`tabular-nums ${exhausted ? 'text-rose-600 font-semibold' : 'text-gray-500'}`}>
          {isBlocked ? '—' : isUnlimited ? `${used} / ∞` : `${used} / ${limit}`}
        </span>
      </div>
      {!isBlocked && !isUnlimited && limit > 0 && (
        <div className="mt-1 h-1 w-full rounded-full bg-gray-100">
          <div
            className={`h-1 rounded-full transition-all ${exhausted ? 'bg-rose-400' : pct >= 75 ? 'bg-amber-400' : 'bg-emerald-400'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  );
}

function UserDetailPanel({ userId, onClose, onChanged }) {
  const [detail, setDetail]         = useState(null);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState('');
  const [planDraft, setPlanDraft]   = useState('');
  const [planSaving, setPlanSaving] = useState(false);
  const [credits, setCredits]       = useState('');
  const [note, setNote]             = useState('');
  const [walletSaving, setWalletSaving] = useState(false);
  const [actionMsg, setActionMsg]   = useState('');

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    apiClient.get(`admin/users/${userId}/`)
      .then((res) => {
        setDetail(res.data);
        setPlanDraft(res.data.plan_code || '');
      })
      .catch((err) => setError(err.response?.data?.error || err.message || 'Failed to load user.'))
      .finally(() => setLoading(false));
  }, [userId]);

  useEffect(() => { load(); }, [load]);

  const savePlan = async (nextPlan) => {
    setPlanSaving(true);
    setActionMsg('');
    try {
      await apiClient.post(`admin/users/${userId}/package/`, { plan_code: nextPlan });
      setActionMsg(`Plan updated to ${PLAN_LABELS[nextPlan] || nextPlan}.`);
      await load();
      onChanged?.();
    } catch (err) {
      setActionMsg(err.response?.data?.error || err.message || 'Failed to update plan.');
    } finally {
      setPlanSaving(false);
    }
  };

  const topUpWallet = async (e) => {
    e.preventDefault();
    const creditsNum = parseInt(credits, 10);
    if (!Number.isInteger(creditsNum) || creditsNum <= 0) {
      setActionMsg('Enter a positive whole number of credits.');
      return;
    }
    setWalletSaving(true);
    setActionMsg('');
    try {
      await apiClient.post('admin/wallet/top-up/', {
        target_email: detail.profile.email,
        credits: creditsNum,
        note,
      });
      setActionMsg(`Added ${creditsNum} credits.`);
      setCredits('');
      setNote('');
      await load();
      onChanged?.();
    } catch (err) {
      setActionMsg(err.response?.data?.error || err.message || 'Failed to add credits.');
    } finally {
      setWalletSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30" onClick={onClose}>
      <div
        className="h-full w-full max-w-md overflow-y-auto bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between">
          <h2 className="text-lg font-bold text-ink">User details</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {loading && <p className="text-sm text-slate-400">Loading…</p>}
        {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

        {detail && !loading && (
          <div className="space-y-6 text-sm">
            <div>
              <p className="text-base font-semibold text-ink">{detail.profile.name || '—'}</p>
              <p className="text-slate-500">{detail.profile.email}</p>
              <p className="mt-1 text-xs text-slate-400">
                {detail.profile.user_type} · {detail.profile.user_status} · {detail.profile.phone_number || 'no phone'}
              </p>
              <p className="mt-1 text-xs text-slate-400">Joined {formatDate(detail.profile.joined_at)}</p>
              <div className="mt-2 flex items-center gap-2">
                <PlanBadge planCode={detail.plan_code} />
                <span className="text-xs text-slate-500">Wallet: {detail.wallet_credits_balance} credits</span>
              </div>
              <p className="mt-1 text-xs text-slate-400">
                Last 30 days: {detail.usage_30d.requests} requests, {detail.usage_30d.tokens.toLocaleString()} tokens
              </p>
            </div>

            {actionMsg && (
              <div className="rounded-lg bg-primary/10 px-3 py-2 text-xs font-medium text-primary">{actionMsg}</div>
            )}

            {/* Package control */}
            <div className="rounded-xl border border-gray-200 p-4">
              <h3 className="mb-2 text-sm font-semibold text-gray-800">Package</h3>
              <select
                value={planDraft}
                onChange={(e) => setPlanDraft(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              >
                {Object.keys(PLAN_LABELS).map((code) => (
                  <option key={code} value={code}>{PLAN_LABELS[code]}</option>
                ))}
              </select>
              <div className="mt-3 flex gap-2">
                <button
                  disabled={planSaving || planDraft === detail.plan_code}
                  onClick={() => savePlan(planDraft)}
                  className="flex-1 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white disabled:opacity-40"
                >
                  {planSaving ? 'Saving…' : 'Update package'}
                </button>
                <button
                  disabled={planSaving || detail.plan_code === 'locked'}
                  onClick={() => savePlan('locked')}
                  className="rounded-lg border border-rose-300 px-3 py-2 text-xs font-semibold text-rose-700 disabled:opacity-40"
                >
                  Close package
                </button>
              </div>
            </div>

            {/* Wallet top-up */}
            <div className="rounded-xl border border-gray-200 p-4">
              <h3 className="mb-2 text-sm font-semibold text-gray-800">Add wallet credits</h3>
              <form onSubmit={topUpWallet} className="space-y-2">
                <input
                  type="number"
                  min="1"
                  step="1"
                  placeholder="Credits to add"
                  value={credits}
                  onChange={(e) => setCredits(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
                <input
                  type="text"
                  placeholder="Note (optional)"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
                <button
                  type="submit"
                  disabled={walletSaving}
                  className="w-full rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-white disabled:opacity-40"
                >
                  {walletSaving ? 'Adding…' : 'Add credits'}
                </button>
              </form>
            </div>

            {/* Feature usage */}
            <div className="rounded-xl border border-gray-200 p-4">
              <h3 className="mb-3 text-sm font-semibold text-gray-800">Feature usage (this cycle)</h3>
              <div className="space-y-2">
                {Object.entries(FEATURE_LABELS).map(([code, _]) => (
                  <FeatureUsageRow key={code} code={code} feature={detail.features?.[code]} />
                ))}
              </div>
            </div>

            {/* Wallet transactions */}
            <div className="rounded-xl border border-gray-200 p-4">
              <h3 className="mb-2 text-sm font-semibold text-gray-800">Recent wallet transactions</h3>
              {detail.wallet_transactions.length === 0 ? (
                <p className="text-xs text-slate-400">No transactions yet.</p>
              ) : (
                <table className="w-full text-xs">
                  <tbody>
                    {detail.wallet_transactions.map((tx, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-1.5 text-slate-500">
                          {tx.created_at ? new Date(tx.created_at).toLocaleDateString('en-IN') : '—'}
                        </td>
                        <td className={`py-1.5 text-right font-semibold ${tx.type === 'top_up' ? 'text-emerald-700' : 'text-rose-700'}`}>
                          {tx.type === 'top_up' ? '+' : '-'}{tx.credits}
                        </td>
                        <td className="py-1.5 text-right text-slate-400">{tx.note || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AdminPanel() {
  const navigate = useNavigate();
  const { user_type, email } = useSelector((s) => s.user);

  const [search, setSearch]         = useState('');
  const [page, setPage]             = useState(1);
  const [sortBy, setSortBy]         = useState('joined_at');
  const [sortDir, setSortDir]       = useState('desc');
  const [users, setUsers]           = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');
  const [selectedUserId, setSelectedUserId] = useState(null);

  const fetchUsers = useCallback(() => {
    setLoading(true);
    setError('');
    apiClient.get('admin/users/', { params: { search, page, page_size: PAGE_SIZE, sort_by: sortBy, sort_dir: sortDir } })
      .then((res) => {
        setUsers(res.data.users || []);
        setTotalCount(res.data.total_count || 0);
      })
      .catch((err) => setError(err.response?.data?.error || err.message || 'Failed to load users.'))
      .finally(() => setLoading(false));
  }, [search, page, sortBy, sortDir]);

  useEffect(() => {
    if (!ALLOWED_TYPES.has(user_type) && !ADMIN_EMAILS.includes(email)) {
      navigate('/not-authorized', { replace: true });
      return;
    }
    fetchUsers();
  }, [fetchUsers, navigate, user_type, email]);

  const toggleSort = (key) => {
    setPage(1);
    if (sortBy === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(key);
      setSortDir('asc');
    }
  };

  const totalPages = Math.max(Math.ceil(totalCount / PAGE_SIZE), 1);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink">Admin Panel</h1>
          <p className="text-sm text-slate-500 mt-0.5">Users, token usage, packages &amp; wallets</p>
        </div>
        <input
          type="text"
          placeholder="Search name or email…"
          value={search}
          onChange={(e) => { setPage(1); setSearch(e.target.value); }}
          className="w-64 rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{error}</div>
      )}

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  onClick={() => toggleSort(col.key)}
                  className={`cursor-pointer select-none px-4 py-3 hover:text-primary ${col.align === 'right' ? 'text-right' : ''}`}
                >
                  {col.label}
                  {sortBy === col.key && (
                    <span className="ml-1">{sortDir === 'asc' ? '▲' : '▼'}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={COLUMNS.length} className="px-4 py-6 text-center text-slate-400">Loading…</td></tr>
            )}
            {!loading && users.length === 0 && (
              <tr><td colSpan={COLUMNS.length} className="px-4 py-6 text-center text-slate-400">No users found.</td></tr>
            )}
            {!loading && users.map((u) => (
              <tr
                key={u.user_id}
                onClick={() => setSelectedUserId(u.user_id)}
                className="cursor-pointer border-b border-slate-100 hover:bg-ivory/60"
              >
                <td className="px-4 py-3">
                  <p className="font-medium text-ink">{u.name || '—'}</p>
                  <p className="text-xs text-slate-500">{u.email || '—'}</p>
                </td>
                <td className="px-4 py-3 text-slate-600">{u.user_type || '—'}</td>
                <td className="px-4 py-3"><PlanBadge planCode={u.plan_code} /></td>
                <td className="px-4 py-3 text-right tabular-nums text-slate-700">{u.wallet_credits_balance}</td>
                <td className="px-4 py-3 text-right tabular-nums text-slate-700">{u.tokens_30d.toLocaleString()}</td>
                <td className="px-4 py-3 text-xs text-slate-500">{formatDate(u.joined_at)}</td>
                <td className="px-4 py-3 text-xs text-slate-500">
                  {u.last_active ? new Date(u.last_active).toLocaleDateString('en-IN') : 'never'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>{totalCount} user{totalCount === 1 ? '' : 's'} total</span>
        <div className="flex items-center gap-2">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(p - 1, 1))}
            className="rounded-lg px-3 py-1.5 font-semibold bg-slate-100 text-slate-600 hover:bg-primary/10 hover:text-primary disabled:opacity-40"
          >
            Prev
          </button>
          <span>Page {page} of {totalPages}</span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
            className="rounded-lg px-3 py-1.5 font-semibold bg-slate-100 text-slate-600 hover:bg-primary/10 hover:text-primary disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>

      {selectedUserId && (
        <UserDetailPanel
          userId={selectedUserId}
          onClose={() => setSelectedUserId(null)}
          onChanged={fetchUsers}
        />
      )}
    </div>
  );
}
