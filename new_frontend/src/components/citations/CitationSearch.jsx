import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { lookupCitation, unwrapCitationPayload } from './citationsApi';
import { loadLastSearchCache, loadSearchCache, saveSearchCache } from '../ecourts/common/useSearchCache';
import CaseLawSearch from './CaseLawSearch';

const EXAMPLES = ['2024 INSC 45', '[1951] 1 SCR 525', '(2022) 4 SCC 12', 'State of UP v. Ram Prakash Singh'];

export default function CitationSearch() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialCitation = searchParams.get('q') || '';
  const [mode, setMode] = useState(searchParams.get('mode') === 'search' ? 'search' : 'verify');

  const [query, setQuery] = useState(initialCitation);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(Boolean(initialCitation));

  async function runLookup(citation) {
    const trimmed = (citation || '').trim();
    if (!trimmed) return;

    const cached = loadSearchCache('citations', trimmed, 1, {});
    if (cached) {
      setResult(cached);
      setError('');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const response = await lookupCitation(trimmed);
      const payload = unwrapCitationPayload(response);
      setResult(payload);
      saveSearchCache('citations', trimmed, 1, {}, payload);
    } catch (err) {
      const status = err.response?.status;
      if (status === 404) {
        setError(`No Supreme Court judgment found for "${trimmed}".`);
      } else if (status === 429) {
        setError(err.response?.data?.error || 'Citation lookup quota exhausted for your plan.');
      } else if (status === 502) {
        setError('The e-SCR portal lookup failed — it may be temporarily unavailable. Please try again.');
      } else {
        setError(err.response?.data?.error || 'Citation lookup failed. Please try again.');
      }
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (initialCitation) {
      runLookup(initialCitation);
      return;
    }
    const last = loadLastSearchCache('citations');
    if (last?.query) {
      setQuery(last.query);
      setResult(last.results || null);
      setSearched(true);
      setSearchParams({ q: last.query }, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSearch(e) {
    e?.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    setSearched(true);
    setSearchParams({ q: trimmed });
    await runLookup(trimmed);
  }

  return (
    <div className="p-8 max-w-3xl">
      <div className="mb-6">
        <h2 className="text-2xl font-black text-ink tracking-tight">Citation Search</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          Verify a known Supreme Court citation, or search case law by keyword, party, judge, date range, and more — against the official e-SCR portal.
        </p>
      </div>

      <div className="flex gap-1 bg-background-light rounded-lg p-1 w-fit mb-6">
        {[
          { key: 'verify', label: 'Verify Citation' },
          { key: 'search', label: 'Search Case Law' },
        ].map((m) => (
          <button
            key={m.key}
            type="button"
            onClick={() => {
              setMode(m.key);
              setSearchParams((prev) => {
                const next = new URLSearchParams(prev);
                next.set('mode', m.key);
                return next;
              }, { replace: true });
            }}
            className={`px-3 py-1.5 text-xs font-semibold rounded transition-all ${
              mode === m.key ? 'bg-primary text-ivory shadow-sm' : 'text-slate-500 hover:text-primary'
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {mode === 'search' ? <CaseLawSearch /> : null}

      {mode === 'verify' ? (
      <>
      <div className="card p-6 mb-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold mb-1 text-slate-700">Citation or Case Name *</label>
            <input
              name="query"
              required
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="input-base"
              placeholder="e.g., 2024 INSC 45, (2022) 4 SCC 12, or State of UP v. Ram Prakash Singh"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Try: {EXAMPLES.map((ex, i) => (
                <React.Fragment key={ex}>
                  {i > 0 && ', '}
                  <button
                    type="button"
                    className="underline hover:text-primary"
                    onClick={() => setQuery(ex)}
                  >
                    {ex}
                  </button>
                </React.Fragment>
              ))}
            </p>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              <span className="material-symbols-outlined text-base">error</span>
              {error}
            </div>
          )}

          <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2">
            {loading ? (
              <><span className="material-symbols-outlined animate-spin text-base">progress_activity</span> Verifying against e-SCR…</>
            ) : (
              <><span className="material-symbols-outlined text-base">gavel</span> Verify Citation</>
            )}
          </button>
          {loading && (
            <p className="text-[11px] text-slate-400">
              This solves a live captcha against the Supreme Court's portal and can take up to a minute.
            </p>
          )}
        </form>
      </div>

      {searched && !loading && result && (
        <div className="card p-6 space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase bg-emerald-100 text-emerald-600">
              Verified
            </span>
            {result.cached ? (
              <span className="text-[10px] px-2 py-0.5 rounded font-bold uppercase bg-slate-100 text-slate-500">
                Cached
              </span>
            ) : null}
          </div>
          <p className="font-semibold text-ink text-lg">{result.case_title || 'Case'}</p>
          <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-600">
            {result.nc_display ? (
              <span><span className="text-slate-400">Neutral Citation:</span> {result.nc_display}</span>
            ) : null}
            {result.scr_citation ? (
              <span><span className="text-slate-400">SCR:</span> {result.scr_citation}</span>
            ) : null}
            {result.cnr ? (
              <span className="font-mono"><span className="text-slate-400 font-sans">CNR:</span> {result.cnr}</span>
            ) : null}
          </div>
          {result.pdf_url ? (
            <a
              href={result.pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:underline mt-2"
            >
              <span className="material-symbols-outlined text-base">picture_as_pdf</span>
              View Full Judgment (PDF)
            </a>
          ) : (
            <p className="text-xs text-slate-400 mt-2">PDF link unavailable for this judgment.</p>
          )}
        </div>
      )}
      </>
      ) : null}
    </div>
  );
}
