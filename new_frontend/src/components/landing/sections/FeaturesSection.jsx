import React from 'react';
import { FEATURES } from '../data/features';
import SectionHeading from '../shared/SectionHeading';

export default function FeaturesSection() {
  return (
    <section id="features" className="border-y border-slate-200 bg-white py-24">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHeading eyebrow="Product" title="AI Legal Practice Management Software Features" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="group relative overflow-hidden rounded-[18px] border border-slate-200 bg-background-light p-6 transition-all hover:-translate-y-1 hover:border-primary/30 hover:shadow-elevated"
            >
              <div className="mb-5 flex items-start justify-between">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/8 transition-transform group-hover:scale-110">
                  <span className="material-symbols-outlined text-primary">{f.icon}</span>
                </div>
                {f.tag && (
                  <span className={`rounded px-2 py-0.5 text-[9px] font-black uppercase tracking-wider ${
                    f.tag === 'Live'
                      ? 'border border-emerald-500/20 bg-emerald-500/10 text-emerald-600'
                      : 'border border-slate-200 bg-white text-slate-400'
                  }`}>
                    {f.tag}
                  </span>
                )}
              </div>
              <h3 className="mb-2.5 text-sm font-bold text-ink">{f.title}</h3>
              <p className="text-[13px] leading-6 text-graphite">{f.desc}</p>
            </div>
          ))}
        </div>
        <p className="mt-6 text-center text-xs italic text-slate-400">
          Supreme Court &amp; Tribunal support — coming soon
        </p>
      </div>
    </section>
  );
}
