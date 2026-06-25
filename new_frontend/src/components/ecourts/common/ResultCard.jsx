import React from 'react';
import { Link } from 'react-router-dom';

/**
 * Shared search result card used by LawyerSearch, LitigantSearch, and CaseSearch.
 * Renders as a clickable Link when detailPath has a valid CNR, otherwise a static card.
 */
export default function ResultCard({ item, detailPath }) {
  const cnr = item.cnr || item.cnr_number || '';
  const hasValidLink = cnr && detailPath && !detailPath.includes('/case/?') && !detailPath.endsWith('/case/');
  const statusText = (item.status || item.case_status || '').toString().toUpperCase();
  const isDisposed = statusText === 'DISPOSED' || statusText === 'CASE DISPOSED';

  const content = (
    <>
      {/* Top row: status badge + case identifier */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          {/* Badge row */}
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${
                isDisposed
                  ? 'bg-slate-100 text-slate-500'
                  : 'bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20'
              }`}
            >
              {item.status || item.case_status || 'Pending'}
            </span>
            {item.case_number ? (
              <span className="text-xs font-semibold text-primary/80">{item.case_number}</span>
            ) : null}
          </div>

          {/* Case title */}
          <p className="text-sm font-semibold leading-snug text-ink">
            {item.case_title || 'Untitled Case'}
          </p>

          {/* Parties */}
          {(item.petitioner || item.respondent) ? (
            <p className="mt-1.5 text-xs leading-relaxed text-slate-500">
              <span className="font-medium text-slate-600">{item.petitioner || '—'}</span>
              <span className="mx-1.5 text-slate-300">vs</span>
              <span className="font-medium text-slate-600">{item.respondent || '—'}</span>
            </p>
          ) : null}

          {/* Meta row: court, advocate, next hearing */}
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-400">
            {item.court_name ? (
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">balance</span>
                {item.court_name}
              </span>
            ) : null}
            {item.advocate ? (
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">person</span>
                {item.advocate}
              </span>
            ) : null}
            {item.next_hearing_date ? (
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-[14px]">event</span>
                {item.next_hearing_date}
              </span>
            ) : null}
            {cnr ? (
              <span className="font-mono text-slate-300">{cnr}</span>
            ) : null}
          </div>
        </div>

        {/* Right arrow (only if clickable) */}
        {hasValidLink ? (
          <span className="material-symbols-outlined mt-1 shrink-0 text-slate-300 transition-colors group-hover:text-primary">
            chevron_right
          </span>
        ) : null}
      </div>
    </>
  );

  if (hasValidLink) {
    return (
      <Link
        to={detailPath}
        className="card group block rounded-lg border border-slate-200 bg-white p-4 transition-all hover:border-primary/30 hover:shadow-md sm:p-5"
      >
        {content}
      </Link>
    );
  }

  return (
    <div className="card block rounded-lg border border-slate-200 bg-white p-4 sm:p-5">
      {content}
    </div>
  );
}
