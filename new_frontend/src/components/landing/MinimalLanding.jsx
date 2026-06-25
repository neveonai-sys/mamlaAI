import React from 'react';
import { Link } from 'react-router-dom';
import PublicNavbar from './shared/PublicNavbar';
import Seo from './shared/Seo';
import MamlaLogoIcon from '../common/MamlaLogoIcon';

function IconDraft() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="h-8 w-8">
      <path d="M12 20h9M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z" />
    </svg>
  );
}
function IconCourt() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="h-8 w-8">
      <path d="M3 21h18M6 18V9m4 9V9m4 9V9m4 9V9M3 9l9-6 9 6" />
    </svg>
  );
}
function IconUsers() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="h-8 w-8">
      <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
    </svg>
  );
}
function IconTag() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="h-8 w-8">
      <path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z" />
      <line x1="7" y1="7" x2="7.01" y2="7" />
    </svg>
  );
}

// Exploration Hub cards — each routes to a dedicated page so the whole product
// is discoverable straight from the landing page.
const HUB_CARDS = [
  { Icon: IconDraft, title: 'AI Legal Drafting',  desc: 'Generate court-ready petitions, affidavits & notices in seconds.', to: '/features' },
  { Icon: IconCourt, title: 'AI Case Tracking',   desc: 'Live eCourts case status across all 25 High Courts & District Courts.', to: '/case-tracking' },
  { Icon: IconUsers, title: 'Solutions',          desc: 'For lawyers, litigants, law students & law firms.', to: '/solutions' },
  { Icon: IconTag,   title: 'Pricing & Plans',    desc: 'Affordable plans for advocates, firms & citizens.', to: '/pricing' },
];

const WHY_POINTS = [
  'AI legal drafting trained on Indian court formats',
  'Real-time eCourts case status, hearings & cause lists',
  'Secure & private — AES-256, DPDP-aligned, India-hosted',
  'One platform for lawyers, firms, litigants & students',
];

const TRUST_BADGES = ['District Courts', 'High Courts', 'Supreme Court'];

export default function MinimalLanding() {
  return (
    <div className="bg-gray-50 text-slate-800 antialiased">
      <Seo
        path="/"
        title="AI Legal Software for Lawyers, Law Firms & Litigants | Legal Practice Management Software | Mamla AI"
        description="Mamla AI is AI-powered legal practice management software for lawyers, law firms, litigants and law students in India. Automate legal drafting, eCourts tracking, case management, legal research and document analysis."
      />

      <PublicNavbar />

      {/* ── HERO ── */}
      <section className="relative overflow-hidden bg-white py-16 lg:py-24">
        <div className="relative z-10 mx-auto grid max-w-7xl items-center gap-12 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
          {/* Hero text */}
          <div>
            <h1 className="mb-6 font-display text-4xl font-extrabold leading-tight text-ink lg:text-5xl">
              Your Gateway to Indian <br className="hidden lg:block" /> Legal Solutions
            </h1>
            <p className="mb-8 max-w-lg text-lg leading-relaxed text-slate-600">
              Navigate the complexities of Indian law with clarity and ease. AI legal drafting, eCourts case tracking,
              legal research and case management — all from one comprehensive platform.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link to="/signup" className="rounded-lg bg-primary px-8 py-4 text-lg font-bold text-white transition-all hover:-translate-y-0.5 hover:bg-primary-dark hover:shadow-lg">
                Start Free
              </Link>
              <Link to="/website" className="rounded-lg border border-slate-300 px-8 py-4 text-lg font-bold text-ink transition-all hover:border-primary hover:text-primary">
                Explore Platform
              </Link>
            </div>
          </div>

          {/* Hero visual (decorative, no external image) */}
          <div className="relative">
            <div aria-hidden="true" className="absolute -right-6 -top-6 h-40 w-40 opacity-20" style={{ backgroundImage: 'radial-gradient(#94a3b8 1px, transparent 1px)', backgroundSize: '20px 20px' }} />
            <div className="court-grid relative overflow-hidden rounded-3xl border border-slate-200 bg-gradient-to-br from-background-dark to-primary p-10 shadow-elevated">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-white/10 bg-white/10">
                  <MamlaLogoIcon dark size={34} />
                </div>
                <span className="font-display text-xl font-bold text-white">Mamla.ai</span>
              </div>
              <p className="mt-6 font-display text-2xl font-bold leading-snug text-white">
                AI legal software, built for <span className="text-primary-soft">Indian courts.</span>
              </p>
              <div className="mt-8 grid grid-cols-3 gap-3">
                {[{ v: '25', l: 'High Courts' }, { v: '4.8Cr', l: 'Cases tracked' }, { v: '24/7', l: 'Chamber continuity' }].map((s) => (
                  <div key={s.l} className="rounded-xl border border-white/10 bg-white/5 p-3 text-center">
                    <p className="font-display text-lg font-bold text-white">{s.v}</p>
                    <p className="mt-0.5 text-[10px] uppercase tracking-wide text-white/50">{s.l}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── EXPLORATION HUB ── */}
      <section className="bg-gray-50 py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-16 text-center">
            <p className="mb-2 text-sm font-semibold uppercase tracking-widest text-primary">Feature Grid</p>
            <h2 className="font-display text-3xl font-bold text-ink lg:text-4xl">Exploration Hub</h2>
          </div>
          <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-4">
            {HUB_CARDS.map(({ Icon, title, desc, to }) => (
              <Link
                key={title}
                to={to}
                className="group flex flex-col items-center rounded-2xl border border-gray-100 bg-gradient-to-br from-white to-slate-50 p-8 text-center shadow-sm transition-transform hover:-translate-y-1.5 hover:shadow-elevated"
              >
                <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-white text-primary shadow-inner ring-1 ring-slate-100">
                  <Icon />
                </div>
                <h3 className="mb-3 text-xl font-bold text-ink">{title}</h3>
                <p className="text-sm leading-relaxed text-slate-500">{desc}</p>
              </Link>
            ))}
          </div>
          <div className="mt-12 text-center">
            <Link to="/website" className="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:text-primary-dark">
              See everything on one page
              <span className="material-symbols-outlined text-base">arrow_forward</span>
            </Link>
          </div>
        </div>
      </section>

      {/* ── WHY CHOOSE / TRUST ── */}
      <section className="bg-white py-16">
        <div className="mx-auto grid max-w-7xl gap-16 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
          <div>
            <h2 className="mb-6 font-display text-3xl font-bold text-ink">Why Choose Mamla.ai</h2>
            <p className="mb-6 leading-relaxed text-slate-600">
              Mamla.ai is a comprehensive platform for legal teams and individuals, streamlining the entire legal
              lifecycle with cutting-edge AI and a deep understanding of the Indian legal system.
            </p>
            <ul className="space-y-4">
              {WHY_POINTS.map((p) => (
                <li key={p} className="flex items-start gap-3">
                  <span className="material-symbols-outlined mt-0.5 flex-shrink-0 text-xl text-emerald-500">check_circle</span>
                  <span className="text-slate-700">{p}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h2 className="mb-10 font-display text-3xl font-bold text-ink">Trusted across Indian courts</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {TRUST_BADGES.map((b) => (
                <div key={b} className="flex flex-col items-center justify-center rounded-2xl border border-slate-200 bg-background-light p-6 text-center">
                  <span className="material-symbols-outlined mb-2 text-3xl text-primary">account_balance</span>
                  <span className="text-sm font-semibold text-ink">{b}</span>
                </div>
              ))}
            </div>
            <p className="mt-6 text-sm text-slate-500">
              Live integration with eCourts for case status, hearing dates, orders and cause lists across all 25 High
              Courts and District Courts.
            </p>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="bg-slate-900 py-12 text-center text-sm text-slate-400">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <p className="mb-3">© {new Date().getFullYear()} Neveon AI Technologies Pvt. Ltd. — Your trusted partner for Indian legal solutions.</p>
          <nav className="flex flex-wrap items-center justify-center gap-5">
            <Link to="/pricing" className="hover:text-white">Pricing</Link>
            <Link to="/about" className="hover:text-white">About</Link>
            <Link to="/case-tracking" className="hover:text-white">Case Tracking</Link>
            <Link to="/login" className="hover:text-white">Log In</Link>
            <Link to="/signup" className="hover:text-white">Sign Up</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
