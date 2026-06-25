import React from 'react';
import { PERSONAS } from '../data/personas';
import SectionHeading from '../shared/SectionHeading';

export default function SolutionsSection() {
  return (
    <section id="solutions" className="bg-background-light py-24">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHeading eyebrow="Solutions" title="Legal Software Solutions for Lawyers, Law Firms, Litigants & Law Students" />
        <div className="grid gap-6 md:grid-cols-3">
          {PERSONAS.map((p) => (
            <div
              key={p.title}
              className="rounded-[20px] border border-slate-200 bg-white p-7 transition-all hover:-translate-y-1 hover:shadow-elevated"
            >
              <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-[14px] bg-primary/8">
                <span className="material-symbols-outlined text-2xl text-primary">{p.icon}</span>
              </div>
              <h3 className="mb-4 font-display text-xl font-bold text-ink">{p.title}</h3>
              <ul className="flex flex-col gap-3">
                {p.points.map((pt) => (
                  <li key={pt} className="flex items-start gap-2.5 text-sm text-graphite">
                    <span className="material-symbols-outlined mt-0.5 flex-shrink-0 text-base text-primary/50">check_circle</span>
                    {pt}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
