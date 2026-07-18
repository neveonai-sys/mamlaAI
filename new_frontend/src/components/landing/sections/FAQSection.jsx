import React, { useState } from 'react';
import { FAQS } from '../data/faqs';

export default function FAQSection() {
  const [openIdx, setOpenIdx] = useState(null);
  return (
    <section id="faq" className="border-t border-slate-200 bg-background-light py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid gap-12 lg:grid-cols-[1fr_2fr] lg:items-start">
          <div>
            <p className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">FAQ</p>
            <h2 className="mb-5 font-display text-4xl font-bold leading-tight text-ink">Frequently Asked Questions about AI Legal Software</h2>
            <p className="mb-7 text-sm leading-7 text-graphite">
              Everything lawyers, law firms, litigants and law students need to know about AI legal practice management software before signing up.
            </p>
            <div className="rounded-[16px] border border-primary/12 bg-primary/5 p-5">
              <div className="mb-2 text-[11px] font-black uppercase tracking-[0.14em] text-primary">Still have questions?</div>
              <a href="mailto:neveon.ai@gmail.com" className="text-sm font-semibold text-primary hover:underline">
                neveon.ai@gmail.com
              </a>
            </div>
          </div>
          <div className="flex flex-col gap-1">
            {FAQS.map((faq, i) => (
              <div
                key={i}
                className={`overflow-hidden rounded-[16px] border transition-colors ${openIdx === i ? 'border-primary/15 bg-white' : 'border-transparent'}`}
              >
                <button
                  type="button"
                  onClick={() => setOpenIdx(openIdx === i ? null : i)}
                  className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left"
                >
                  <span className="text-sm font-semibold text-ink">{faq.q}</span>
                  <span className={`material-symbols-outlined flex-shrink-0 text-primary transition-transform duration-300 ${openIdx === i ? 'rotate-180' : ''}`}>
                    expand_more
                  </span>
                </button>
                {openIdx === i && (
                  <div className="px-5 pb-5 text-sm leading-7 text-graphite">{faq.a}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
