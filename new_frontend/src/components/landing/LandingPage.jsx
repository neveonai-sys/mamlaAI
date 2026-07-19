import React from 'react';
import { Link } from 'react-router-dom';
import PublicNavbar from './shared/PublicNavbar';
import PublicFooter from './shared/PublicFooter';
import Seo from './shared/Seo';
import FeaturesSection from './sections/FeaturesSection';
import SolutionsSection from './sections/SolutionsSection';
import PricingSection from './sections/PricingSection';
import LiveCourtStats from './sections/LiveCourtStats';
import ResourcesSection from './sections/ResourcesSection';
import SecuritySection from './sections/SecuritySection';
import AboutSection from './sections/AboutSection';
import FAQSection from './sections/FAQSection';
import ContactSection from './sections/ContactSection';

// /website — the full single-scroll overview. Kept for inbound links and as a
// "see everything" page; the dedicated /features, /solutions, /pricing,
// /resources and /about pages are the primary, explorable entry points and now
// share the same navbar, footer and section components as this page.
export default function LandingPage() {
  return (
    <div className="bg-background-light text-ink antialiased">
      <Seo
        path="/website"
        title="AI Legal Software for Lawyers, Law Firms & Litigants | Mamla AI"
        description="Mamla AI is AI-powered legal practice management software for Indian lawyers, law firms, litigants and law students. AI drafting, eCourts tracking, legal research, case management and more."
      />
      <PublicNavbar />

      {/* ── HERO ── */}
      <header className="relative overflow-hidden border-b border-slate-100 bg-white py-16 md:py-24">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-10 -top-10 h-56 w-56 opacity-[0.18]"
          style={{ backgroundImage: 'radial-gradient(#94a3b8 1px, transparent 1px)', backgroundSize: '20px 20px' }}
        />
        <div className="relative mx-auto max-w-3xl px-6 text-center">
          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5">
            <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
            <span className="text-xs font-bold uppercase tracking-widest text-primary">Trusted by 200+ legal professionals</span>
          </div>

          <h1 className="mb-6 font-display text-4xl font-extrabold leading-[1.08] tracking-tight text-ink md:text-6xl">
            AI Legal Software for{' '}
            <span className="block text-primary">Lawyers, Law Firms &amp; Litigants</span>
          </h1>

          <p className="mx-auto mb-10 max-w-xl text-lg font-medium leading-8 text-slate-600">
            Draft legal documents, manage cases, track court hearings, conduct legal research, automate client management and monitor eCourts &mdash; all from one AI-powered legal platform.
          </p>

          <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              to="/signup"
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-8 py-4 text-[15px] font-bold text-white shadow-sm transition-all hover:-translate-y-0.5 hover:bg-primary-dark"
            >
              Get Started Free
              <span className="material-symbols-outlined text-lg">arrow_forward</span>
            </Link>
            <a
              href="#features"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-8 py-4 text-[15px] font-bold text-ink transition-all hover:border-primary hover:text-primary"
            >
              See How It Works
            </a>
          </div>

          <div className="mx-auto mt-16 grid max-w-xl grid-cols-3 gap-6 border-t border-slate-200 pt-10">
            {[
              { value: '24/7',  label: 'Chamber Continuity' },
              { value: '10x',   label: 'Faster Review Cycles' },
              { value: 'RBAC',  label: 'Matter Security' },
            ].map((stat) => (
              <div key={stat.label} className="flex flex-col items-center gap-1">
                <span className="font-display text-2xl font-bold text-primary">{stat.value}</span>
                <span className="text-[11px] font-semibold uppercase tracking-[0.15em] text-slate-500">{stat.label}</span>
              </div>
            ))}
          </div>
        </div>
      </header>

      {/* ── CONTENT SECTIONS ── */}
      <FeaturesSection />
      <SolutionsSection />
      <PricingSection />
      <LiveCourtStats />
      <ResourcesSection />
      <SecuritySection />
      <AboutSection />
      <FAQSection />
      <ContactSection />

      {/* ── BOTTOM CTA ── */}
      <section className="bg-background-dark py-24 text-ivory">
        <div className="mx-auto max-w-2xl px-6 text-center">
          <h2 className="mb-5 font-display text-4xl font-bold text-white md:text-5xl">
            Ready to Transform Your{' '}
            <span className="italic text-primary-soft">Legal Practice with AI?</span>
          </h2>
          <p className="mb-10 text-base font-medium leading-8 text-white/65">
            Join lawyers, law firms, litigants and law students already using Mamla AI — India&apos;s AI-powered legal practice management software — to work smarter, draft faster and never miss a hearing.
          </p>
          <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              to="/signup"
              className="inline-flex items-center gap-2 rounded-[12px] bg-white px-8 py-4 text-[15px] font-bold text-primary-dark shadow-elevated transition-all hover:-translate-y-0.5 hover:bg-primary-soft"
            >
              Try Mamla AI — It&apos;s Free
              <span className="material-symbols-outlined text-lg">arrow_forward</span>
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-[12px] border border-white/15 bg-white/8 px-8 py-4 text-[15px] font-medium text-white/80 transition-all hover:bg-white/14"
            >
              Sign In
            </Link>
          </div>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}
