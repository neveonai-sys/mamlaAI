import React from 'react';
import { Link } from 'react-router-dom';

// Two-column light hero for the Case Tracking page: copy + CTA on the left, a
// faux live eCourts "case status" preview card on the right (built with divs —
// no external images).
export default function CaseTrackingHero() {
  return (
    <header className="relative overflow-hidden border-b border-slate-100 bg-background-light py-16 md:py-20">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -left-10 -top-10 h-48 w-48 opacity-[0.18]"
        style={{ backgroundImage: 'radial-gradient(#94a3b8 1px, transparent 1px)', backgroundSize: '20px 20px' }}
      />
      <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
        <div>
          <p className="mb-4 text-[11px] font-black uppercase tracking-[0.22em] text-primary">Live eCourts Data</p>
          <h1 className="mb-6 font-display text-4xl font-extrabold leading-[1.1] tracking-tight text-ink md:text-5xl">
            AI Case Tracking: Unify Your Legal Portfolio
          </h1>
          <p className="mb-8 max-w-lg text-lg leading-8 text-slate-600">
            Track case status, hearing dates, orders and cause lists from all 25 High Courts and District Courts —
            in real time, from one dashboard. Never miss a development again.
          </p>
          <div className="flex flex-wrap gap-4">
            <Link to="/signup" className="rounded-lg bg-primary px-8 py-3.5 text-[15px] font-bold text-white shadow-sm transition-all hover:-translate-y-0.5 hover:bg-primary-dark">
              Start Tracking Free
            </Link>
            <Link to="/pricing" className="rounded-lg border border-slate-300 px-8 py-3.5 text-[15px] font-bold text-ink transition-all hover:border-primary hover:text-primary">
              View Pricing
            </Link>
          </div>
        </div>

        {/* Faux case-status preview card */}
        <div className="relative">
          <div className="rounded-3xl border border-slate-200 bg-background-dark p-6 shadow-elevated">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <p className="text-[11px] font-black uppercase tracking-[0.18em] text-primary-soft/70">Case Status</p>
                <p className="font-display text-lg font-bold text-white">CNR: DLHC01-004521-2026</p>
              </div>
              <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/20 px-3 py-1 text-[11px] font-semibold text-emerald-300">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" /> Live
              </span>
            </div>
            <div className="space-y-3">
              {[
                { icon: 'event', label: 'Next Hearing', value: '12 Aug 2026 · Court No. 4' },
                { icon: 'gavel', label: 'Stage', value: 'Arguments' },
                { icon: 'description', label: 'Last Order', value: 'Interim relief granted' },
                { icon: 'account_balance', label: 'Bench', value: 'Delhi High Court' },
              ].map((row) => (
                <div key={row.label} className="flex items-center gap-3 rounded-xl border border-white/8 bg-white/5 p-3">
                  <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-primary/25 text-primary-soft">
                    <span className="material-symbols-outlined text-base">{row.icon}</span>
                  </span>
                  <div>
                    <p className="text-[11px] uppercase tracking-wide text-white/40">{row.label}</p>
                    <p className="text-sm font-semibold text-white/90">{row.value}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
