import React from 'react';

// Centered section heading used across the marketing sections — eyebrow label
// + title + optional subtitle. Keeps the repeated pattern consistent.
export default function SectionHeading({ eyebrow, title, subtitle, className = '' }) {
  return (
    <div className={`mx-auto mb-14 max-w-3xl text-center ${className}`}>
      {eyebrow && (
        <p className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-primary">{eyebrow}</p>
      )}
      <h2 className="font-display text-3xl font-bold text-ink md:text-4xl">{title}</h2>
      {subtitle && <p className="mt-4 text-base leading-7 text-graphite">{subtitle}</p>}
    </div>
  );
}
