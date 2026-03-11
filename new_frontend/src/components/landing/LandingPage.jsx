import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const FEATURES = [
  {
    icon: 'edit_note',
    title: 'AI Drafting',
    desc: 'Generate complex legal documents with unmatched accuracy using domain-specific LLMs trained on sovereign legal corpora.',
  },
  {
    icon: 'forum',
    title: 'Document Chat',
    desc: 'Interrogate thousands of discovery documents using natural language. Instant citation provided for every answer.',
  },
  {
    icon: 'dynamic_feed',
    title: 'Live Court Updates',
    desc: 'Automatically monitor eCourts for case status changes, order uploads, and hearing schedules in real time.',
  },
  {
    icon: 'calendar_month',
    title: 'Hearing Calendar',
    desc: 'Never miss a date. Unified calendar integrating court deadlines, hearing schedules, and client meetings.',
  },
  {
    icon: 'people',
    title: 'Client Portal',
    desc: 'Secure, role-based access for clients and paralegals. Share documents and updates instantly.',
  },
  {
    icon: 'search',
    title: 'eCourts Search',
    desc: 'Search case details, cause lists, and lawyer information directly from the eCourts national database.',
  },
];

const TESTIMONIALS = [
  {
    text: 'Mamla.AI cut our document review time by 60%. The AI drafting feature alone has transformed our practice.',
    author: 'Adv. Priya Sharma',
    role: 'Senior Partner, Sharma & Associates',
  },
  {
    text: "Our team handles 3x more cases with the same headcount. The court updates feature alone saves us hours every day.",
    author: 'Adv. Rahul Mehta',
    role: 'Managing Partner, Mehta Law Firm',
  },
  {
    text: 'The document intelligence is extraordinary. I can interrogate a 500-page contract in seconds.',
    author: 'Adv. Ananya Kapoor',
    role: 'Corporate Counsel, TechVenture Ltd.',
  },
];

export default function LandingPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');

  function handleRequestAccess(e) {
    e.preventDefault();
    navigate('/signup');
  }

  return (
    <div className="bg-background-light text-ink font-display antialiased">
      {/* ── Sticky Navigation ─────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 w-full border-b border-primary/10 bg-background-light/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <div className="size-8 bg-ink flex items-center justify-center rounded-lg">
              <span className="material-symbols-outlined text-primary text-xl">account_balance</span>
            </div>
            <span className="text-xl font-bold tracking-tight">Mamla.AI</span>
          </div>

          {/* Desktop Nav links */}
          <div className="hidden md:flex items-center gap-10">
            <a className="text-sm font-medium hover:text-primary transition-colors" href="#features">Platform</a>
            <a className="text-sm font-medium hover:text-primary transition-colors" href="#features">Solutions</a>
            <a className="text-sm font-medium hover:text-primary transition-colors" href="#security">Security</a>
            <a className="text-sm font-medium hover:text-primary transition-colors" href="#testimonials">Testimonials</a>
          </div>

          {/* CTA buttons */}
          <div className="flex items-center gap-4">
            <Link
              to="/login"
              className="text-sm font-semibold px-4 py-2 hover:text-primary transition-colors"
            >
              Log In
            </Link>
            <Link
              to="/signup"
              className="bg-primary text-ivory text-sm font-bold px-6 py-2.5 rounded-lg hover:bg-primary/90 transition-all shadow-sm"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero Section ───────────────────────────────────────────── */}
      <header className="gradient-mesh relative overflow-hidden pt-20 pb-32">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            {/* Left: Copy */}
            <div className="flex flex-col gap-8">
              {/* Beta badge */}
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 w-fit">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-primary" />
                </span>
                <span className="text-xs font-bold uppercase tracking-widest text-primary">Now in Private Beta</span>
              </div>

              <h1 className="text-6xl md:text-7xl font-black leading-[1.1] tracking-tight">
                Manage High-Value Legal Work{' '}
                <span className="text-primary">in One Place.</span>
              </h1>

              <p className="text-lg text-ink/70 leading-relaxed max-w-xl">
                Experience the future of legal operations. A sophisticated workflow platform
                engineered for precision, speed, and absolute security for top-tier law firms.
              </p>

              {/* Email capture */}
              <form onSubmit={handleRequestAccess} className="flex flex-col sm:flex-row gap-4">
                <div className="flex-1 flex border border-ink/10 rounded-xl overflow-hidden bg-white focus-within:ring-2 ring-primary/20">
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter professional email"
                    className="flex-1 px-5 py-4 border-none focus:ring-0 text-ink bg-transparent text-sm"
                  />
                  <button
                    type="submit"
                    className="bg-ink text-ivory font-bold px-8 py-4 hover:bg-ink/90 transition-all text-sm"
                  >
                    Request Access
                  </button>
                </div>
              </form>

              {/* Stats */}
              <div className="flex items-center gap-8 pt-4">
                <div className="flex flex-col">
                  <span className="text-2xl font-bold">99.9%</span>
                  <span className="text-xs font-semibold text-ink/50 uppercase tracking-tighter">Success Rate</span>
                </div>
                <div className="w-px h-10 bg-ink/10" />
                <div className="flex flex-col">
                  <span className="text-2xl font-bold">40%</span>
                  <span className="text-xs font-semibold text-ink/50 uppercase tracking-tighter">Efficiency Gain</span>
                </div>
                <div className="w-px h-10 bg-ink/10" />
                <div className="flex flex-col">
                  <span className="text-2xl font-bold">SOC2</span>
                  <span className="text-xs font-semibold text-ink/50 uppercase tracking-tighter">Compliance</span>
                </div>
              </div>
            </div>

            {/* Right: Hero visual */}
            <div className="relative group">
              <div className="absolute -inset-4 bg-primary/5 rounded-[2rem] blur-3xl group-hover:bg-primary/10 transition-all duration-500" />
              <div className="relative aspect-[4/5] bg-ink rounded-2xl overflow-hidden shadow-2xl flex items-center justify-center">
                <div className="z-10 text-center p-12">
                  <div className="size-20 bg-primary/20 border border-primary/30 rounded-full flex items-center justify-center mx-auto mb-6">
                    <span className="material-symbols-outlined text-primary text-4xl icon-filled">gavel</span>
                  </div>
                  <h3 className="text-ivory text-2xl font-bold mb-2">Automated Litigation</h3>
                  <p className="text-ivory/60 text-sm max-w-xs mx-auto leading-relaxed">
                    Systematic intelligence applied to every discovery and drafting phase.
                  </p>
                  {/* Feature pills */}
                  <div className="mt-8 flex flex-wrap gap-2 justify-center">
                    {['AI Drafting', 'Document Chat', 'Court Monitor', 'eCourts', 'Calendar', 'Clients'].map((pill) => (
                      <span key={pill} className="px-3 py-1 bg-primary/20 border border-primary/30 rounded-full text-xs text-ivory font-semibold">
                        {pill}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* ── Core Features ──────────────────────────────────────────── */}
      <section id="features" className="py-24 bg-white border-y border-ink/5">
        <div className="max-w-7xl mx-auto px-6">
          <div className="mb-16">
            <h2 className="text-sm font-bold text-primary uppercase tracking-widest mb-4">Core Intelligence</h2>
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
              <h3 className="text-4xl md:text-5xl font-black max-w-2xl">
                Precision-Engineered Tools for Modern Counsel.
              </h3>
              <p className="text-ink/60 max-w-xs">
                Designed to handle the complexities of high-stakes litigation and transactional law.
              </p>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="group p-8 rounded-2xl border border-ink/5 bg-background-light hover:border-primary/30 transition-all duration-300"
              >
                <div className="size-12 bg-white rounded-xl shadow-sm flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <span className="material-symbols-outlined text-primary">{f.icon}</span>
                </div>
                <h4 className="text-xl font-bold mb-4">{f.title}</h4>
                <p className="text-ink/60 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Security Section ────────────────────────────────────────── */}
      <section id="security" className="py-24 bg-background-light">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-sm font-bold text-primary uppercase tracking-widest mb-4">Enterprise Security</h2>
              <h3 className="text-4xl font-black mb-6">Built for the Most Sensitive Legal Work.</h3>
              <p className="text-ink/60 mb-8 leading-relaxed">
                Your clients' data is encrypted at rest and in transit. We comply with the highest
                standards of data protection so you can focus on winning cases, not worrying about breaches.
              </p>
              <div className="space-y-4">
                {[
                  { icon: 'shield', text: 'End-to-end encryption for all documents' },
                  { icon: 'verified_user', text: 'SOC2 Type II certified infrastructure' },
                  { icon: 'lock', text: 'Role-based access control (RBAC)' },
                  { icon: 'policy', text: 'DPDP Act & Bar Council compliant' },
                ].map((item) => (
                  <div key={item.text} className="flex items-center gap-3">
                    <div className="size-8 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
                      <span className="material-symbols-outlined text-primary text-base">{item.icon}</span>
                    </div>
                    <span className="text-sm font-medium text-ink/80">{item.text}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-ink rounded-2xl p-8 text-ivory">
              <div className="grid grid-cols-2 gap-6">
                {[
                  { label: 'Uptime SLA', value: '99.99%' },
                  { label: 'Encryption', value: 'AES-256' },
                  { label: 'Data Centers', value: 'India' },
                  { label: 'Compliance', value: 'SOC2' },
                ].map((stat) => (
                  <div key={stat.label} className="bg-white/5 rounded-xl p-4 border border-white/10">
                    <p className="text-white/50 text-xs uppercase tracking-wider mb-1">{stat.label}</p>
                    <p className="text-2xl font-black text-primary">{stat.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Testimonials ───────────────────────────────────────────── */}
      <section id="testimonials" className="py-24 bg-white border-t border-ink/5">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-sm font-bold text-primary uppercase tracking-widest mb-4">Trusted by Counsel</h2>
          <h3 className="text-4xl font-black mb-12">What Legal Professionals Say.</h3>
          <div className="grid md:grid-cols-3 gap-8">
            {TESTIMONIALS.map((t) => (
              <div key={t.author} className="p-8 rounded-2xl border border-ink/5 bg-background-light">
                <p className="text-ink/70 leading-relaxed mb-6 italic">&ldquo;{t.text}&rdquo;</p>
                <div>
                  <p className="font-bold text-ink">{t.author}</p>
                  <p className="text-sm text-ink/50">{t.role}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Section ────────────────────────────────────────────── */}
      <section className="py-24 bg-ink text-ivory">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-5xl font-black mb-6">
            Ready to Transform Your Practice?
          </h2>
          <p className="text-ivory/60 text-lg mb-10 leading-relaxed">
            Join the growing community of legal professionals using Mamla.AI to handle
            high-value matters with confidence and speed.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/signup"
              className="bg-primary text-ivory font-bold px-8 py-4 rounded-xl hover:bg-primary/90 transition-all shadow-lg text-base"
            >
              Start Free Trial
            </Link>
            <Link
              to="/login"
              className="bg-white/10 text-ivory font-bold px-8 py-4 rounded-xl hover:bg-white/20 transition-all text-base"
            >
              Sign In
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="bg-background-light border-t border-ink/5 py-12">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary icon-filled">gavel</span>
            <span className="font-bold">Mamla.AI</span>
          </div>
          <p className="text-sm text-ink/40">© 2025 Mamla.AI. All rights reserved. Secure & Encrypted.</p>
          <div className="flex gap-6">
            <a href="#" className="text-sm text-ink/50 hover:text-primary transition-colors">Privacy</a>
            <a href="#" className="text-sm text-ink/50 hover:text-primary transition-colors">Terms</a>
            <a href="#" className="text-sm text-ink/50 hover:text-primary transition-colors">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
