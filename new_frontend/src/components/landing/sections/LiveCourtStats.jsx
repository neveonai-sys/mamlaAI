import React from 'react';
import { STAT_CARDS, NEWS_ITEMS } from '../data/liveData';

export default function LiveCourtStats() {
  return (
    <section id="live-data" className="border-y border-slate-200 bg-background-light py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">Live Court Intelligence</div>
        <div className="mb-10 flex flex-wrap items-end justify-between gap-5">
          <h2 className="font-display text-3xl font-bold leading-tight text-ink md:text-4xl">
            Real-Time eCourts Case Tracking<br />&amp; Court Intelligence
          </h2>
          <p className="max-w-xs text-sm leading-7 text-graphite">
            Monitor case status, hearing dates, Supreme Court updates, High Court orders and legal news through a single legal intelligence dashboard — powered by live NJDG and eCourts data.
          </p>
        </div>
        <div className="grid gap-7 lg:grid-cols-[1fr_320px]">
          <div>
            <div className="grid gap-5 sm:grid-cols-2">
              {STAT_CARDS.map((card) => (
                <div
                  key={card.icon + card.value}
                  className="relative overflow-hidden rounded-[20px] border border-slate-200 bg-white p-6 transition-all hover:-translate-y-1 hover:shadow-card"
                >
                  <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(22,52,95,0.07),transparent_55%)]" />
                  <div className="relative">
                    <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10">
                      <span className="material-symbols-outlined text-primary">{card.icon}</span>
                    </div>
                    <p className="font-display text-4xl font-bold leading-none text-background-dark">
                      {card.value}<span className="text-xl font-semibold">{card.unit}</span>
                    </p>
                    <p className="mt-2 text-sm leading-6 text-graphite">{card.desc}</p>
                    <p className="mt-3 flex items-center gap-1.5 text-[10px] font-black uppercase tracking-[0.12em] text-primary">
                      <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
                      {card.source}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-5 flex flex-wrap items-center gap-3 rounded-[14px] border border-primary/10 bg-primary/5 px-4 py-3">
              <span className="text-[11px] font-black uppercase tracking-[0.14em] text-primary">Data sources</span>
              {['NJDG (njdg.ecourts.gov.in)', 'Supreme Court of India (main.sci.gov.in)', 'eCourts Services'].map((src, i, arr) => (
                <React.Fragment key={src}>
                  <span className="text-xs text-graphite">{src}</span>
                  {i < arr.length - 1 && <span className="text-slate-300">·</span>}
                </React.Fragment>
              ))}
            </div>
          </div>
          <div className="flex flex-col gap-3 rounded-[20px] bg-background-dark p-6">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-[11px] font-black uppercase tracking-[0.2em] text-primary-soft/70">Legal Headlines</span>
              <span className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-400">
                <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" /> Live feed
              </span>
            </div>
            {NEWS_ITEMS.map((item, i) => (
              <div
                key={i}
                className="flex cursor-pointer gap-3 rounded-[14px] p-3 transition-colors"
                style={{ border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.05)' }}
              >
                <span className={`mt-0.5 flex-shrink-0 self-start rounded-md px-2 py-0.5 text-[9px] font-black uppercase tracking-[0.12em] ${item.tone}`}>
                  {item.source}
                </span>
                <div>
                  <p className="text-xs font-medium leading-5 text-slate-100">{item.text}</p>
                  <p className="mt-1 text-[11px] text-slate-400">{item.time}</p>
                </div>
              </div>
            ))}
            <a
              href="https://www.livelaw.in"
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 block text-center text-xs font-semibold text-slate-400 transition-colors hover:text-primary-soft"
            >
              View all legal news →
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
