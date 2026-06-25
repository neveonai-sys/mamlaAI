import React from 'react';
import { useNavigate } from 'react-router-dom';

// Feature definitions per user type
const LAWYER_FEATURES = [
  { icon: 'forum',        label: 'Legal Chat',        quota: '24 queries', desc: 'Ask Indian law questions — statutes, procedures, precedents.' },
  { icon: 'description',  label: 'Doc Analysis',      quota: '8 sessions', desc: 'Upload any legal document for clause-level AI analysis.' },
  { icon: 'auto_awesome', label: 'AI Draft Generation', quota: '20 drafts', desc: 'Generate petitions, affidavits, agreements — court-formatted.' },
  { icon: 'edit_note',    label: 'Drafting Actions',  quota: '12 actions', desc: 'Refine, rewrite, and improve sections with AI.' },
  { icon: 'lightbulb',    label: 'AI Suggestions',    quota: '5 suggestions', desc: 'Contextual suggestions as you draft.' },
  { icon: 'psychology',   label: 'Case Companion',    quota: '2 sessions', desc: 'AI case strategy — arguments, weaknesses, applicable law.' },
  { icon: 'gavel',        label: 'eCourts CNR Lookup', quota: '50 lookups', desc: 'Live case status, orders, hearings from District & High Courts.' },
  { icon: 'download',     label: 'Order Downloads',   quota: '5 PDFs',    desc: 'Download court order PDFs directly.' },
];

const NAGRIK_FEATURES = [
  { icon: 'forum',        label: 'Legal Chat',        quota: '5 queries', desc: 'Ask questions about your rights in plain language.' },
  { icon: 'description',  label: 'Doc Analysis',      quota: '2 sessions', desc: 'Upload documents — understand what they mean.' },
  { icon: 'auto_awesome', label: 'AI Draft Generation', quota: '1 draft',  desc: 'Generate a basic legal document.' },
  { icon: 'gavel',        label: 'eCourts CNR Lookup', quota: '10 lookups', desc: 'Track your case status on eCourts.' },
];

const NAGRIK_BLOCKED = [
  { icon: 'edit_note',    label: 'Drafting Actions',  reason: 'Professional lawyer tool' },
  { icon: 'lightbulb',   label: 'AI Suggestions',     reason: 'Professional lawyer tool' },
  { icon: 'psychology',  label: 'Case Companion',      reason: 'Professional lawyer tool' },
];

export default function WelcomeModal({ userType, email, planCode, trialEndsAt, onClose }) {
  const navigate = useNavigate();
  const isLawyer = userType !== 'Client';
  const features = isLawyer ? LAWYER_FEATURES : NAGRIK_FEATURES;
  const trialLabel = trialEndsAt
    ? new Date(trialEndsAt).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
    : '30 days';

  function dismiss(cta) {
    try {
      localStorage.setItem(`mamla_welcome_shown_${email}`, '1');
    } catch (_) { /* storage blocked */ }
    onClose();
    if (cta === 'draft') navigate('/drafting');
    else if (cta === 'docs') navigate('/documents');
    else if (cta === 'ecourts') navigate('/ecourts');
  }

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
      style={{ background: 'rgba(10,20,40,0.72)', backdropFilter: 'blur(4px)' }}
      onClick={(e) => { if (e.target === e.currentTarget) dismiss(); }}
    >
      <div className="relative w-full max-w-2xl rounded-[24px] border border-white/10 bg-white shadow-elevated overflow-hidden">

        {/* Header */}
        <div className="bg-background-dark px-8 py-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[10px] font-black uppercase tracking-[0.28em] text-primary-soft/70">
                {isLawyer ? 'Trial — 30 Days' : 'Nagrik Trial — 30 Days'}
              </p>
              <h2 className="mt-2 text-2xl font-black text-white">
                {isLawyer
                  ? "You're on the Free Trial 🎉"
                  : "Welcome to Mamla.AI"}
              </h2>
              <p className="mt-1.5 text-sm text-white/55">
                {isLawyer
                  ? `Full access to all lawyer tools until ${trialLabel}. No credit card needed.`
                  : `Access legal information, track your case, and understand your rights — free until ${trialLabel}.`}
              </p>
            </div>
            <button
              onClick={() => dismiss()}
              className="flex-shrink-0 rounded-xl p-1.5 text-white/40 hover:bg-white/10 hover:text-white transition-colors"
            >
              <span className="material-symbols-outlined text-xl">close</span>
            </button>
          </div>
          {/* Saffron accent */}
          <div className="mt-4 h-0.5 bg-gradient-to-r from-[#FF9800] via-[#FF9800]/60 to-transparent rounded-full" />
        </div>

        {/* Feature grid */}
        <div className="px-8 py-6">
          <p className="mb-4 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">
            What&apos;s included in your trial
          </p>
          <div className={`grid gap-3 ${isLawyer ? 'grid-cols-2 sm:grid-cols-4' : 'grid-cols-2'}`}>
            {features.map((f) => (
              <div key={f.label} className="rounded-xl border border-primary/10 bg-slate-50 p-3">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span className="material-symbols-outlined text-primary" style={{ fontSize: '16px' }}>{f.icon}</span>
                  <span className="text-xs font-bold text-ink">{f.label}</span>
                </div>
                <p className="text-[11px] font-black text-primary mb-1">{f.quota}</p>
                <p className="text-[10px] text-slate-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>

          {!isLawyer && NAGRIK_BLOCKED.length > 0 && (
            <div className="mt-4">
              <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">
                Not available on Nagrik plans
              </p>
              <div className="flex flex-wrap gap-2">
                {NAGRIK_BLOCKED.map((f) => (
                  <div key={f.label} className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5">
                    <span className="material-symbols-outlined text-slate-300" style={{ fontSize: '14px' }}>{f.icon}</span>
                    <span className="text-[11px] text-slate-400 font-medium">{f.label}</span>
                    <span className="text-[10px] text-slate-300">— {f.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer CTAs */}
        <div className="border-t border-slate-100 bg-slate-50 px-8 py-5 flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-slate-400">
            Wallet credits can be added anytime to extend beyond included limits.
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => dismiss()}
              className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
            >
              Go to Dashboard
            </button>
            {isLawyer ? (
              <button
                onClick={() => dismiss('draft')}
                className="rounded-xl bg-primary px-5 py-2 text-sm font-bold text-white hover:bg-primary/90 transition-colors"
              >
                Start Drafting
                <span className="material-symbols-outlined text-base align-middle ml-1">arrow_forward</span>
              </button>
            ) : (
              <button
                onClick={() => dismiss('ecourts')}
                className="rounded-xl bg-primary px-5 py-2 text-sm font-bold text-white hover:bg-primary/90 transition-colors"
              >
                Track My Case
                <span className="material-symbols-outlined text-base align-middle ml-1">arrow_forward</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
