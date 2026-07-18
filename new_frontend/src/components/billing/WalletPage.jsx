import React, { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import apiClient from '../../services/api';
import { getUsageSummary } from '../../services/chatApi';

const TIER_LABELS = {
  t1: 'Low (Llama)',
  t2: 'Medium (Haiku)',
  t3: 'High (Sonnet)',
};

const WHATSAPP_NUMBER = '919999999999'; // update to real number
const SUPPORT_EMAIL   = 'neveon.ai@gmail.com';
const CREDIT_RATE     = 1.33;

const PACKS = [
  {
    credits: 60,
    price: 99,
    label: 'Starter',
    perks: ['~30-60 legal chats*', '~30 doc analyses', '~15 drafts'],
  },
  {
    credits: 150,
    price: 199,
    label: 'Regular',
    popular: true,
    perks: ['~75-150 legal chats*', '~75 doc analyses', '~37 drafts'],
  },
  {
    credits: 450,
    price: 499,
    label: 'Value',
    perks: ['~225-450 legal chats*', '~225 doc analyses', '~112 drafts'],
  },
  {
    credits: 1000,
    price: 999,
    label: 'Power',
    perks: ['~500-1000 legal chats*', '~500 doc analyses', '~250 drafts'],
  },
];
const CHAT_PERK_NOTE = '* Legal chat usage varies with the model tier you pick — Low/Medium cost less per message than High or Premium.';

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

function toInr(credits) {
  return (credits * CREDIT_RATE).toFixed(2);
}

function TxTypeBadge({ type }) {
  if (type === 'top_up') {
    return (
      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
        + Top-up
      </span>
    );
  }
  return (
    <span className="rounded-full bg-rose-100 px-2 py-0.5 text-[11px] font-semibold text-rose-700">
      - Used
    </span>
  );
}

export default function WalletPage() {
  const { wallet, usageSummary, trial, features, planCode } = useSelector((s) => s.entitlements);
  const [selectedPack, setSelectedPack]   = useState(null);
  const [transactions, setTransactions]   = useState([]);
  const [txLoading, setTxLoading]         = useState(true);
  const [usageByTier, setUsageByTier]     = useState([]);
  const [usageLoading, setUsageLoading]   = useState(true);

  useEffect(() => {
    apiClient
      .get('users/wallet/transactions/?limit=10')
      .then((r) => setTransactions(r.data?.transactions || []))
      .catch(() => setTransactions([]))
      .finally(() => setTxLoading(false));
  }, []);

  useEffect(() => {
    getUsageSummary()
      .then((r) => setUsageByTier(r.data?.by_tier || []))
      .catch(() => setUsageByTier([]))
      .finally(() => setUsageLoading(false));
  }, []);

  const balance      = wallet?.balance ?? 0;
  const inrEquiv     = wallet?.inrEquivalent ?? toInr(balance);
  const trialValueInr = usageSummary?.trialValueInr ?? 0;
  const totalConsumed = usageSummary?.totalCreditsConsumed ?? 0;
  const isInternal    = planCode === 'internal' || planCode === 'enterprise';

  const waLink = selectedPack
    ? `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(
        `Hi, I'd like to top up my Mamla AI wallet with the ${selectedPack.label} pack — ${selectedPack.credits} credits for ₹${selectedPack.price}.`
      )}`
    : null;

  const mailLink = selectedPack
    ? `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent(
        `Recharge - ${selectedPack.label} | ${selectedPack.credits} credits | ₹${selectedPack.price}`
      )}&body=${encodeURIComponent(
        `Hi,\n\nI'd like to recharge my Mamla AI wallet.\n\nPack: ${selectedPack.label} — ${selectedPack.credits} credits for ₹${selectedPack.price}\n\nI'll send the UPI payment and share the transaction reference.\n\nThanks`
      )}`
    : null;

  return (
    <div className="mx-auto max-w-2xl px-4 py-8 text-sm text-gray-800">
      <h1 className="mb-6 text-xl font-semibold text-gray-900">Wallet & Usage</h1>

      {/* ── Balance card ─────────────────────────────────────────── */}
      <div className="mb-5 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        {trial?.active ? (
          /* Trial plan — show included feature counts, not wallet balance */
          <>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-widest text-gray-400">Trial Plan</p>
                {trial.daysRemaining > 0 && (
                  <p className="mt-1 text-base font-semibold text-indigo-700">
                    {trial.daysRemaining} day{trial.daysRemaining !== 1 ? 's' : ''} remaining
                  </p>
                )}
              </div>
              <span className="rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700">
                Trial
              </span>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2">
              {[
                { code: 'general_legal_chat',     label: 'Legal Chats' },
                { code: 'brain_doc_analysis',     label: 'Doc Analyses' },
                { code: 'brain_drafting_actions', label: 'Drafts' },
              ].map(({ code, label }) => {
                const f     = features?.[code] || {};
                const limit = f.included_limit ?? 0;
                const used  = f.used_count ?? 0;
                const left  = Math.max(limit - used, 0);
                const isUnlimited = limit >= 1000000;
                return (
                  <div key={code} className="rounded-lg bg-indigo-50 px-3 py-2.5 text-center">
                    <p className="text-lg font-bold text-indigo-800">
                      {isUnlimited ? '∞' : left}
                    </p>
                    <p className="text-[10px] text-indigo-600">{label} left</p>
                    {!isUnlimited && (
                      <p className="text-[9px] text-indigo-400">{used}/{limit} used</p>
                    )}
                  </div>
                );
              })}
            </div>
            {trialValueInr > 0 && (
              <p className="mt-3 text-xs text-indigo-600">
                ≈ ₹{trialValueInr} of AI assistance delivered so far
              </p>
            )}
          </>
        ) : (
          /* Paid / post-trial — show wallet credits */
          <>
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium uppercase tracking-widest text-gray-400">Available Credits</p>
                <p className="mt-1 text-4xl font-bold text-gray-900">{balance}</p>
                <p className="mt-0.5 text-sm text-gray-500">≈ ₹{inrEquiv} equivalent</p>
              </div>
              <span className="rounded-lg bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700">
                {planCode ? planCode.replace(/_/g, ' ') : 'Active'}
              </span>
            </div>
          </>
        )}
      </div>

      {/* ── Add credits (pack selector) ──────────────────────────── */}
      <div className="mb-5 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-1 text-sm font-semibold text-gray-800">Add credits</h2>
        <p className="mb-4 text-xs text-gray-500">
          Choose a pack, then reach out via WhatsApp or email with your UPI payment. Credits are added within a few hours.
        </p>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {PACKS.map((pack) => {
            const active = selectedPack?.credits === pack.credits;
            return (
              <button
                key={pack.credits}
                onClick={() => setSelectedPack(active ? null : pack)}
                className={`relative flex flex-col rounded-xl border-2 p-3 text-left transition-all ${
                  active
                    ? 'border-emerald-500 bg-emerald-50 shadow-sm'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
              >
                {pack.popular && (
                  <span className="absolute -top-2 left-1/2 -translate-x-1/2 rounded-full bg-emerald-600 px-2 py-0.5 text-[10px] font-bold text-white">
                    Popular
                  </span>
                )}
                <span className="text-xs font-semibold text-gray-500">{pack.label}</span>
                <span className="mt-1 text-lg font-bold text-gray-900">{pack.credits}</span>
                <span className="text-[11px] text-gray-400">credits</span>
                <span className="mt-2 text-sm font-bold text-emerald-700">₹{pack.price}</span>
                <ul className="mt-2 space-y-0.5">
                  {pack.perks.map((p) => (
                    <li key={p} className="text-[10px] text-gray-500">{p}</li>
                  ))}
                </ul>
              </button>
            );
          })}
        </div>
        <p className="mt-3 text-[10px] text-gray-400">{CHAT_PERK_NOTE}</p>

        {selectedPack ? (
          <div className="mt-4 flex flex-wrap gap-3">
            <a
              href={waLink}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-700"
            >
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
              </svg>
              WhatsApp — {selectedPack.label} pack
            </a>
            <a
              href={mailLink}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50"
            >
              <svg className="h-4 w-4 text-gray-500" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              Email us
            </a>
          </div>
        ) : (
          <p className="mt-4 text-xs text-gray-400">Select a pack above to see contact options.</p>
        )}
      </div>

      {/* ── Usage this cycle ─────────────────────────────────────── */}
      <div className="mb-5 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-gray-800">This cycle's usage</h2>
        <div className="space-y-2">
          {Object.entries(FEATURE_LABELS).map(([code, label]) => {
            const f          = features?.[code] || {};
            const used       = f.used_count ?? 0;
            const limit      = f.included_limit ?? 0;
            const isUnlimited = limit >= 1000000;
            const isBlocked  = f.hard_block;
            const pct        = isUnlimited || isBlocked || limit === 0 ? 0 : Math.min((used / limit) * 100, 100);
            const exhausted  = !isUnlimited && !isBlocked && limit > 0 && used >= limit;

            return (
              <div key={code}>
                <div className="flex items-center justify-between text-xs">
                  <span className={`font-medium ${isBlocked ? 'text-gray-400' : 'text-gray-700'}`}>
                    {label}
                    {isBlocked && <span className="ml-1 text-[10px] text-gray-400">(plan restricted)</span>}
                  </span>
                  <span className={`tabular-nums ${exhausted ? 'text-rose-600 font-semibold' : 'text-gray-500'}`}>
                    {isBlocked ? '—' : isUnlimited ? `${used} / ∞` : `${used} / ${limit}`}
                    {exhausted && ' · used up'}
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
          })}
        </div>
        {!isInternal && (
          <p className="mt-3 text-[11px] text-gray-400">
            When a feature's limit is reached, that feature is paused — other features keep working. Wallet credits can extend individual features as overage.
          </p>
        )}
      </div>

      {/* ── Model usage breakdown ────────────────────────────────── */}
      <div className="mb-5 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-semibold text-gray-800">Model usage breakdown</h2>
        {usageLoading ? (
          <p className="text-xs text-gray-400">Loading…</p>
        ) : usageByTier.length === 0 ? (
          <p className="text-xs text-gray-400">No MamlaAI Chat activity yet — usage by model tier will appear here.</p>
        ) : (
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b text-left text-gray-400">
                <th className="pb-2 font-medium">Model tier</th>
                <th className="pb-2 text-right font-medium">Messages</th>
                <th className="pb-2 text-right font-medium">Tokens</th>
                <th className="pb-2 text-right font-medium">Credits</th>
              </tr>
            </thead>
            <tbody>
              {usageByTier.map((row, i) => (
                <tr key={`${row.tier}-${row.premium}-${i}`} className="border-b last:border-0">
                  <td className="py-2 font-medium text-gray-700">
                    {row.premium ? 'Premium (Opus)' : (TIER_LABELS[row.tier] || row.tier || 'Unknown')}
                  </td>
                  <td className="py-2 text-right tabular-nums text-gray-600">{row.messages}</td>
                  <td className="py-2 text-right tabular-nums text-gray-600">{row.tokens}</td>
                  <td className="py-2 text-right tabular-nums font-semibold text-gray-700">{row.credits_charged}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="mt-3 text-[11px] text-gray-400">
          Lower tiers use cheaper models and cost fewer wallet credits; Premium (Opus) drains credits fastest.
        </p>
      </div>

      {/* ── Transaction history ──────────────────────────────────── */}
      {(transactions.length > 0 || !txLoading) && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-sm font-semibold text-gray-800">Recent transactions</h2>
          {txLoading ? (
            <p className="text-xs text-gray-400">Loading…</p>
          ) : transactions.length === 0 ? (
            <p className="text-xs text-gray-400">No transactions yet — your first top-up will appear here.</p>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b text-left text-gray-400">
                  <th className="pb-2 font-medium">Date</th>
                  <th className="pb-2 font-medium">Type</th>
                  <th className="pb-2 text-right font-medium">Credits</th>
                  <th className="pb-2 text-right font-medium">₹</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx, i) => (
                  <tr key={i} className="border-b last:border-0">
                    <td className="py-2 text-gray-500">
                      {tx.created_at ? new Date(tx.created_at).toLocaleDateString('en-IN') : '—'}
                    </td>
                    <td className="py-2">
                      <TxTypeBadge type={tx.type} />
                    </td>
                    <td className={`py-2 text-right tabular-nums font-semibold ${tx.type === 'top_up' ? 'text-emerald-700' : 'text-rose-700'}`}>
                      {tx.type === 'top_up' ? '+' : '-'}{tx.credits}
                    </td>
                    <td className="py-2 text-right tabular-nums text-gray-600">
                      {tx.amount_inr != null ? `₹${tx.amount_inr}` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
