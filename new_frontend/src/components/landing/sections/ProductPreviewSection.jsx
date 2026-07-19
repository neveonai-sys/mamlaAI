import React, { useState } from 'react';

// Product-preview band: shows real app screenshots in a light browser-chrome
// frame. Images are user-supplied files served from /screenshots/*.png (copied
// into dist via the CopyWebpackPlugin pattern in webpack.common.js). Each frame
// degrades gracefully to a labelled placeholder if the file is missing, so a
// not-yet-uploaded screenshot never breaks the layout.
const SHOTS = [
  { key: 'dashboard', src: '/screenshots/dashboard.png', label: 'Practice Dashboard', caption: 'Every case, hearing and deadline in one view.' },
  { key: 'drafting',  src: '/screenshots/drafting.png',  label: 'AI Legal Drafting',  caption: 'Draft petitions, replies and contracts with AI in minutes.' },
  { key: 'ecourt',    src: '/screenshots/ecourt.png',    label: 'Live eCourts Search', caption: 'Track case status & orders across Indian courts in real time.' },
];

function ShotFrame({ src, label, caption }) {
  const [failed, setFailed] = useState(false);

  return (
    <figure className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card transition-transform hover:-translate-y-1 hover:shadow-elevated">
      {/* browser chrome */}
      <div className="flex items-center gap-1.5 border-b border-slate-100 bg-slate-50 px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-red-300" />
        <span className="h-2.5 w-2.5 rounded-full bg-amber-300" />
        <span className="h-2.5 w-2.5 rounded-full bg-emerald-300" />
        <span className="ml-3 truncate text-[11px] font-medium text-slate-400">app.mamla.ai</span>
      </div>
      {failed ? (
        <div className="flex aspect-[16/10] w-full flex-col items-center justify-center gap-2 bg-gradient-to-br from-slate-50 to-slate-100 text-center">
          <span className="material-symbols-outlined text-3xl text-primary/50">image</span>
          <span className="text-xs font-semibold text-slate-400">{label}</span>
        </div>
      ) : (
        <img
          src={src}
          alt={`Mamla.ai — ${label}`}
          loading="lazy"
          onError={() => setFailed(true)}
          className="aspect-[16/10] w-full bg-white object-cover object-top"
        />
      )}
      <figcaption className="border-t border-slate-100 px-4 py-3">
        <p className="text-sm font-bold text-ink">{label}</p>
        <p className="mt-0.5 text-xs leading-5 text-slate-500">{caption}</p>
      </figcaption>
    </figure>
  );
}

export default function ProductPreviewSection() {
  return (
    <section className="border-y border-slate-100 bg-white py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-14 text-center">
          <p className="mb-2 text-sm font-semibold uppercase tracking-widest text-primary">Product Tour</p>
          <h2 className="font-display text-3xl font-bold text-ink lg:text-4xl">See Mamla.ai in action</h2>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-7 text-slate-600">
            A single workspace for drafting, case tracking and research — purpose-built for Indian legal practice.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
          {SHOTS.map((s) => (
            <ShotFrame key={s.key} {...s} />
          ))}
        </div>
      </div>
    </section>
  );
}
