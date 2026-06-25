import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { LAWYER_PLANS, NAGRIK_PLANS } from '../data/pricing';

function PlanCard({ plan }) {
  const recommended = plan.recommended;
  return (
    <div
      className={`relative flex flex-col overflow-hidden rounded-3xl bg-white transition-transform ${
        recommended
          ? 'border-4 border-primary shadow-elevated lg:-translate-y-2 z-10'
          : 'border-2 border-slate-200 shadow-card hover:-translate-y-1'
      }`}
    >
      {/* Corner ribbon for the recommended plan */}
      {recommended && (
        <div className="pointer-events-none absolute -right-px -top-px h-24 w-24 overflow-hidden">
          <span
            className="absolute right-[-34px] top-[22px] w-[150px] rotate-45 bg-primary py-1 text-center text-[10px] font-black uppercase tracking-wider text-white shadow-md"
          >
            Most Popular
          </span>
        </div>
      )}

      {/* Header bar */}
      <div className="bg-primary py-4 text-center">
        <h3 className="font-display text-xl font-bold text-white">{plan.name}</h3>
      </div>

      <div className="flex flex-grow flex-col p-7">
        <div className="mb-6 text-center">
          <div className="flex items-baseline justify-center gap-1">
            <span className="font-display text-4xl font-extrabold text-ink">{plan.price}</span>
            <span className="text-sm font-medium text-graphite">{plan.period}</span>
          </div>
          <p className="mt-2 text-xs font-medium text-graphite">{plan.subtitle}</p>
          {plan.offer && (
            <p className="mt-3 inline-block rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-[10px] font-bold text-emerald-700">
              {plan.offer}
            </p>
          )}
        </div>

        <ul className="mb-8 flex flex-grow flex-col gap-3 text-sm">
          {plan.items.map((item) => (
            <li key={item} className="flex items-start gap-2 text-graphite">
              <span className="material-symbols-outlined mt-0.5 flex-shrink-0 text-base text-emerald-500">check_circle</span>
              {item}
            </li>
          ))}
          {plan.blocked && plan.blocked.map((item) => (
            <li key={item} className="flex items-start gap-2 text-slate-400">
              <span className="material-symbols-outlined mt-0.5 flex-shrink-0 text-base text-slate-300">block</span>
              {item}
            </li>
          ))}
        </ul>

        <Link
          to="/signup"
          className={`mt-auto block rounded-2xl py-3 text-center text-sm font-bold transition-all hover:-translate-y-0.5 ${
            recommended
              ? 'bg-primary text-white hover:bg-primary-dark shadow-md'
              : 'border-2 border-primary/20 bg-white text-primary hover:bg-primary/5'
          }`}
        >
          {plan.cta}
        </Link>
      </div>
    </div>
  );
}

export default function PricingSection() {
  const [activeTab, setActiveTab] = useState('lawyer');
  const plans = activeTab === 'lawyer' ? LAWYER_PLANS : NAGRIK_PLANS;
  const cols = plans.length === 2 ? 'md:grid-cols-2 max-w-3xl mx-auto' : 'md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5';

  return (
    <section id="pricing" className="border-t border-slate-200 bg-gray-50 py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mb-4 text-center">
          <p className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">Pricing</p>
          <h2 className="font-display text-3xl font-bold text-ink md:text-4xl">
            Affordable AI Legal Software Pricing for Lawyers &amp; Law Firms
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-sm text-graphite">
            Choose the best legal practice management software plan for solo advocates, law firms, litigants and law students. Currently in private beta — join now to lock in early-adopter pricing.
          </p>
          {/* Lawyer / Nagrik toggle */}
          <div className="mt-8 inline-flex gap-1 rounded-xl border border-slate-200 bg-white p-1">
            <button
              onClick={() => setActiveTab('lawyer')}
              className={`rounded-lg px-5 py-2 text-sm font-bold transition-all ${
                activeTab === 'lawyer' ? 'bg-primary text-white shadow-sm' : 'text-slate-600 hover:text-ink'
              }`}
            >
              <span className="material-symbols-outlined mr-1.5 align-middle text-base">balance</span>
              For Lawyers &amp; Firms
            </button>
            <button
              onClick={() => setActiveTab('nagrik')}
              className={`rounded-lg px-5 py-2 text-sm font-bold transition-all ${
                activeTab === 'nagrik' ? 'bg-primary text-white shadow-sm' : 'text-slate-600 hover:text-ink'
              }`}
            >
              <span className="material-symbols-outlined mr-1.5 align-middle text-base">person</span>
              For Citizens (Nagrik)
            </button>
          </div>
        </div>

        {activeTab === 'nagrik' && (
          <p className="mx-auto mt-4 max-w-xl rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-center text-xs text-slate-500">
            <span className="material-symbols-outlined mr-1 align-middle text-sm text-amber-500">info</span>
            Nagrik plans give citizens access to legal information, document understanding, and eCourts tracking.
            Drafting, Case Companion, and AI Suggestions are professional tools reserved for lawyers.
          </p>
        )}

        <div className={`mt-12 grid items-stretch gap-6 ${cols}`}>
          {plans.map((plan) => <PlanCard key={plan.name} plan={plan} />)}
        </div>

        {/* Custom solution banner */}
        <div className="mx-auto mt-16 max-w-6xl">
          <div className="flex flex-col items-center justify-between gap-6 rounded-3xl border-2 border-primary/20 bg-background-dark p-8 text-center shadow-2xl md:flex-row md:p-12 md:text-left">
            <div>
              <h3 className="mb-3 font-display text-2xl font-bold text-primary-soft md:text-3xl">
                Running a law firm?
              </h3>
              <p className="max-w-2xl text-base leading-7 text-white/80">
                Firm Basic (₹2,049) and Firm Pro (₹4,549) plans add multi-lawyer support, a client lifecycle dashboard and firm-wide calendar coordination. Get in touch for a tailored quote.
              </p>
            </div>
            <a
              href="mailto:neveon.ai@gmail.com"
              className="whitespace-nowrap rounded-2xl bg-white px-8 py-4 text-base font-bold text-primary-dark shadow-lg transition-transform hover:scale-105"
            >
              Contact Sales
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
