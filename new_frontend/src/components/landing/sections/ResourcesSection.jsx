import React from 'react';
import SectionHeading from '../shared/SectionHeading';

const RESOURCES = [
  { icon: 'flash_on',     title: 'Live Law',          highlight: true,  desc: 'Latest Supreme Court and High Court legal updates — real-time legal news, breaking orders and judicial developments as they happen.', href: 'https://www.livelaw.in' },
  { icon: 'search',       title: 'Citation Search',   highlight: false, desc: 'AI-powered legal research across Indian judgments and precedents. Search citations, trace reasoning and find relevant sections across courts.', href: '#live-data' },
  { icon: 'list_alt',     title: 'Cause List Search', highlight: false, desc: "Search daily cause lists across Indian courts. Know what's scheduled before stepping into court — District Courts and High Courts.", href: '#live-data' },
  { icon: 'auto_awesome', title: 'AI in Law',         highlight: false, desc: 'Insights on artificial intelligence in legal practice — written for Indian lawyers, not technologists. How AI is reshaping advocacy in India.', href: '#' },
];

export default function ResourcesSection() {
  return (
    <section id="resources" className="border-t border-slate-200 bg-white py-24">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHeading eyebrow="Resources" title="Legal Research Resources & AI Legal Insights" />
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          {RESOURCES.map((r) => (
            <a
              key={r.title}
              href={r.href}
              target={r.href.startsWith('http') ? '_blank' : undefined}
              rel={r.href.startsWith('http') ? 'noopener noreferrer' : undefined}
              className={`group flex flex-col rounded-[18px] border p-7 transition-all hover:-translate-y-1 ${
                r.highlight
                  ? 'border-emerald-500/20 bg-emerald-500/5 hover:border-emerald-500/35 hover:shadow-elevated'
                  : 'border-slate-200 bg-background-light hover:border-primary/25 hover:shadow-elevated'
              }`}
            >
              {r.highlight && (
                <span className="mb-4 inline-flex w-fit items-center gap-1.5 rounded border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[9px] font-black uppercase tracking-wider text-emerald-600">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                  Live Updates
                </span>
              )}
              <span className={`material-symbols-outlined mb-4 text-2xl ${r.highlight ? 'text-emerald-500' : 'text-primary/60'}`}>
                {r.icon}
              </span>
              <h3 className="mb-2.5 text-base font-bold text-ink">{r.title}</h3>
              <p className="mb-5 flex-grow text-[13px] leading-6 text-graphite">{r.desc}</p>
              <span className={`flex items-center gap-1.5 text-xs font-semibold ${r.highlight ? 'text-emerald-600' : 'text-primary'}`}>
                Explore
                <span className="material-symbols-outlined text-sm">arrow_forward</span>
              </span>
            </a>
          ))}
        </div>
      </div>
    </section>
  );
}
