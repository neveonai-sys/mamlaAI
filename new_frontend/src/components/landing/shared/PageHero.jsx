import React from 'react';
import { Link } from 'react-router-dom';

// Light hero band for hub pages — eyebrow + H1 + intro + optional CTA on a
// white background with a subtle dot decoration. Sits directly below the
// sticky white navbar.
export default function PageHero({ eyebrow, title, subtitle, cta }) {
  return (
    <header className="relative overflow-hidden border-b border-slate-100 bg-white py-16 md:py-20">
      {/* dotted decoration */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-10 -top-10 h-48 w-48 opacity-[0.18]"
        style={{ backgroundImage: 'radial-gradient(#94a3b8 1px, transparent 1px)', backgroundSize: '20px 20px' }}
      />
      <div className="relative mx-auto max-w-3xl px-6 text-center">
        {eyebrow && (
          <p className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">{eyebrow}</p>
        )}
        <h1 className="font-display text-4xl font-extrabold leading-[1.1] tracking-tight text-ink md:text-5xl">
          {title}
        </h1>
        {subtitle && (
          <p className="mx-auto mt-5 max-w-xl text-base font-medium leading-8 text-slate-600">{subtitle}</p>
        )}
        {cta && (
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              to="/signup"
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-8 py-3.5 text-[15px] font-bold text-white shadow-sm transition-all hover:-translate-y-0.5 hover:bg-primary-dark"
            >
              {cta}
              <span className="material-symbols-outlined text-lg">arrow_forward</span>
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}
