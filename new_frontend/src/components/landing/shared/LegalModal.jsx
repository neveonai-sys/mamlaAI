import React from 'react';
import { LEGAL_DOCS } from '../data/legalDocs';

// Modal rendering a legal document (terms / privacy / refund / disclaimer).
export default function LegalModal({ docKey, onClose }) {
  const doc = LEGAL_DOCS[docKey];
  if (!doc) return null;
  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-ink/80 px-4 py-6 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative max-h-[85vh] w-full max-w-2xl overflow-hidden rounded-[28px] bg-white shadow-elevated"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white px-8 py-6">
          <h2 className="font-display text-xl font-bold text-background-dark">{doc.title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-background-light transition-colors hover:bg-slate-200"
          >
            <span className="material-symbols-outlined text-lg">close</span>
          </button>
        </div>
        <div className="max-h-[calc(85vh-80px)] overflow-y-auto px-8 py-7 custom-scrollbar">
          {doc.date && <p className="mb-5 text-[11px] italic text-slate-400">{doc.date}</p>}
          {doc.sections.map((section) => (
            <div key={section.heading} className="mb-5">
              <h3 className="mb-2 text-sm font-bold text-background-dark">{section.heading}</h3>
              <p className="text-sm leading-7 text-graphite">{section.body}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
