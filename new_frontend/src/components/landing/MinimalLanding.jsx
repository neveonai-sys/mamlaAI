import React from 'react';
import { Link } from 'react-router-dom';
import MamlaLogoIcon from '../common/MamlaLogoIcon';

function IconDraft() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="w-5 h-5">
      <path d="M12 20h9M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z" />
    </svg>
  );
}
function IconCourt() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="w-5 h-5">
      <path d="M3 21h18M6 18V9m4 9V9m4 9V9m4 9V9M3 9l9-6 9 6" />
    </svg>
  );
}
function IconCalendar() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="w-5 h-5">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
    </svg>
  );
}

const VALUE_PROPS = [
  { Icon: IconDraft,    title: 'AI Drafting',     desc: 'Court-ready petitions in seconds — trained on Indian legal formats.' },
  { Icon: IconCourt,    title: 'Live eCourt Data', desc: 'Real-time case status from all 25 High Courts and District Courts.' },
  { Icon: IconCalendar, title: 'Hearing Calendar', desc: 'Smart deadline tracking and automated hearing reminders.' },
];

const TRUST_BADGES = ['District Courts', 'High Courts', 'Supreme Court'];

export default function MinimalLanding() {
  return (
    <div className="relative h-dvh min-h-[580px] flex flex-col bg-[#08111f] text-white overflow-hidden">

      {/* Ambient glow */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0"
        style={{ background: 'radial-gradient(ellipse 80% 60% at 30% -5%, rgba(22,52,95,0.65) 0%, transparent 65%)' }} />
      {/* Dot grid */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 opacity-[0.03]"
        style={{ backgroundImage: 'radial-gradient(circle, #ffffff 1px, transparent 1px)', backgroundSize: '28px 28px' }} />

      {/* ── Nav ── */}
      <header className="relative z-10 flex-shrink-0 flex items-center justify-between px-5 py-3 sm:px-10 sm:py-3.5 border-b border-white/8">
        <Link to="/" className="flex items-center gap-2" aria-label="Mamla.AI home">
          <MamlaLogoIcon className="h-6 w-6 sm:h-7 sm:w-7" />
          <span className="font-semibold text-base sm:text-lg tracking-tight">Mamla.AI</span>
        </Link>
        <nav className="flex items-center gap-1.5 sm:gap-2">
          <Link to="/login"
            className="px-3 py-1.5 sm:px-4 sm:py-2 rounded-lg text-sm font-medium text-white/65 hover:text-white hover:bg-white/8 transition-colors">
            Log In
          </Link>
          <Link to="/signup"
            className="px-3 py-1.5 sm:px-4 sm:py-2 rounded-lg text-sm font-semibold bg-primary text-white hover:bg-primary-dark transition-colors">
            Sign Up Free
          </Link>
        </nav>
      </header>

      {/* ── Main: single column on mobile, two columns on sm+ ── */}
      <main className="relative z-10 flex-1 flex flex-col sm:flex-row items-center justify-center overflow-hidden
                       px-5 py-6 sm:px-10 lg:px-20 sm:py-0 gap-6 sm:gap-10 lg:gap-16
                       max-w-6xl mx-auto w-full">

        {/* Left — hero text, CTAs, explore */}
        <div className="flex flex-col items-center sm:items-start text-center sm:text-left
                        flex-shrink-0 w-full sm:max-w-[480px] lg:max-w-[520px]">

          {/* Beta badge */}
          <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/40 bg-primary/10
                           px-3 py-1 text-[10px] sm:text-[11px] font-medium text-primary-soft mb-4 tracking-wide uppercase">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Now in Beta &mdash; Lock beta pricing
          </span>

          <h1 className="text-[2.1rem] sm:text-[2.6rem] lg:text-[3.2rem] font-bold leading-[1.15] mb-3 tracking-tight">
            India&rsquo;s AI platform for{' '}
            <span className="text-primary-soft">legal work</span>
          </h1>

          <p className="text-sm sm:text-base lg:text-lg text-white/55 mb-3 sm:mb-4 leading-relaxed max-w-sm sm:max-w-none">
            AI drafting, live eCourt case tracking, and smart calendar
            management &mdash; built for Indian advocates and law firms.
          </p>

          {/* Trust badges */}
          <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 mb-5">
            {TRUST_BADGES.map((b) => (
              <span key={b} className="inline-flex items-center gap-1.5 rounded-full border border-white/10
                                       bg-white/5 px-2.5 py-0.5 text-[10px] sm:text-[11px] font-medium
                                       text-white/45 tracking-wide">
                <svg viewBox="0 0 6 6" className="w-1.5 h-1.5 fill-emerald-400" aria-hidden="true">
                  <circle cx="3" cy="3" r="3" />
                </svg>
                {b}
              </span>
            ))}
          </div>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center sm:items-stretch gap-2.5 sm:gap-3 mb-4 w-full sm:w-auto">
            <Link to="/signup"
              className="w-full sm:w-auto px-6 py-3 rounded-xl text-sm sm:text-[15px] font-semibold
                         bg-primary text-white hover:bg-primary-dark transition-colors shadow-card text-center">
              Start Free &mdash; No card needed
            </Link>
            <Link to="/login"
              className="w-full sm:w-auto px-6 py-3 rounded-xl text-sm sm:text-[15px] font-medium
                         border border-white/15 text-white/70 hover:bg-white/6 hover:text-white
                         transition-colors text-center">
              Log In
            </Link>
          </div>

          {/* Explore link — below CTAs, always visible */}
          <Link to="/website"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-white/15
                       bg-white/[0.04] text-sm font-medium text-white/60 hover:text-white
                       hover:bg-white/10 hover:border-white/25 transition-colors">
            Explore all features, pricing &amp; plans
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.75"
              strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="w-3.5 h-3.5">
              <path d="M3 8h10M9 4l4 4-4 4" />
            </svg>
          </Link>
        </div>

        {/* Right — feature cards (hidden on mobile) */}
        <div className="hidden sm:flex flex-col justify-center gap-3 flex-1 min-w-0">
          {VALUE_PROPS.map(({ Icon, title, desc }) => (
            <div key={title}
              className="flex items-start gap-4 rounded-2xl border border-white/8 bg-white/[0.03]
                         p-4 lg:p-5 backdrop-blur-sm hover:border-white/15 hover:bg-white/[0.05]
                         transition-colors">
              <span className="flex-shrink-0 flex h-9 w-9 items-center justify-center rounded-lg
                               bg-primary/25 text-primary-soft border border-primary/20">
                <Icon />
              </span>
              <div className="text-left">
                <p className="text-sm font-semibold text-white/90 mb-0.5">{title}</p>
                <p className="text-[12.5px] text-white/45 leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>

      </main>

      {/* ── Footer ── */}
      <footer className="relative z-10 flex-shrink-0 border-t border-white/8 px-5 py-2.5 sm:px-6 sm:py-3
                         flex flex-col sm:flex-row items-center justify-between gap-1.5 text-xs text-white/25">
        <span>&copy; {new Date().getFullYear()} Neveon AI Technologies Pvt. Ltd.</span>
        <nav className="flex items-center gap-4">
          <Link to="/website#pricing" className="hover:text-white/50 transition-colors">Pricing</Link>
          <Link to="/login" className="hover:text-white/50 transition-colors">Log In</Link>
          <Link to="/signup" className="hover:text-white/50 transition-colors">Sign Up</Link>
        </nav>
      </footer>
    </div>
  );
}
