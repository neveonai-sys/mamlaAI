import React from 'react';

// Traditional practice vs Mamla.ai comparison. Light theme, primary accent.
const ROWS = [
  { traditional: 'Manual drafting from scratch', mamla: 'AI drafting in minutes, court-formatted' },
  { traditional: 'Juggling multiple court portals', mamla: 'One dashboard for all your cases' },
  { traditional: 'Missed hearing dates & deadlines', mamla: 'Automated reminders & cause-list tracking' },
  { traditional: 'Hours of manual legal research', mamla: 'AI legal research & citation search' },
  { traditional: 'Files scattered across systems', mamla: 'Centralised, secure case management' },
];

export default function ComparisonSection() {
  return (
    <section className="bg-gray-50 py-20">
      <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
        <div className="mb-12 text-center">
          <p className="mb-2 text-sm font-semibold uppercase tracking-widest text-primary">The Difference</p>
          <h2 className="font-display text-3xl font-bold text-ink lg:text-4xl">Traditional practice vs Mamla.ai</h2>
        </div>

        <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-card">
          {/* header */}
          <div className="grid grid-cols-2">
            <div className="border-b border-r border-slate-200 bg-slate-50 px-5 py-4 sm:px-8">
              <p className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">Traditional Practice</p>
            </div>
            <div className="border-b border-slate-200 bg-primary px-5 py-4 sm:px-8">
              <p className="text-xs font-black uppercase tracking-[0.14em] text-white/80">With Mamla.ai</p>
            </div>
          </div>

          {ROWS.map((row, i) => (
            <div key={row.mamla} className={`grid grid-cols-2 ${i < ROWS.length - 1 ? 'border-b border-slate-100' : ''}`}>
              <div className="flex items-start gap-3 border-r border-slate-200 px-5 py-5 sm:px-8">
                <span className="material-symbols-outlined mt-0.5 flex-shrink-0 text-xl text-slate-300">close</span>
                <span className="text-sm leading-6 text-slate-500">{row.traditional}</span>
              </div>
              <div className="flex items-start gap-3 px-5 py-5 sm:px-8">
                <span className="material-symbols-outlined mt-0.5 flex-shrink-0 text-xl text-emerald-500">check_circle</span>
                <span className="text-sm font-medium leading-6 text-ink">{row.mamla}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
