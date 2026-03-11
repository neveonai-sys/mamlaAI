import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { getEcourtsDefaults, searchEcourts, unwrapEcourtsPayload } from './common/ecourtsApi';
import { loadLastSearchCache, loadSearchCache, saveSearchCache } from './common/useSearchCache';

export default function LitigantSearch() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  const initialPage = Number.parseInt(searchParams.get('page') || '1', 10);

  const [form, setForm] = useState({ query: initialQuery });
  const [results, setResults] = useState(null);
  const [page, setPage] = useState(initialPage);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(Boolean(initialQuery));
  const [isDefault, setIsDefault] = useState(false);
  const [defaultRefreshedAt, setDefaultRefreshedAt] = useState(null);

  function handleChange(e) {
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  }

  const caseList = useMemo(() => results?.case_list || [], [results]);
  const totalHits = results?.total || 0;
  const totalPages = results?.total_pages || 0;

  const runSearch = useCallback(async (query, nextPage = 1) => {
    const trimmedQuery = (query || '').trim();
    if (!trimmedQuery) return;

    const cacheFilters = { searchType: 'litigant' };
    const cached = loadSearchCache('litigants', trimmedQuery, nextPage, cacheFilters);
    if (cached) {
      setResults(cached);
      setIsDefault(false);
      setError('');
      return;
    }

    setError('');
    setLoading(true);
    try {
      const response = await searchEcourts({
        searchType: 'litigant',
        query: trimmedQuery,
        page: nextPage,
        pageSize: 20,
      });
      const payload = unwrapEcourtsPayload(response) || {};
      setResults(payload);
      setIsDefault(false);
      saveSearchCache('litigants', trimmedQuery, nextPage, cacheFilters, payload);
    } catch (err) {
      setError(err.response?.data?.error || 'Search failed. Please check your inputs.');
      setResults(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchDefaults = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await getEcourtsDefaults('litigants');
      const payload = response.data?.data || unwrapEcourtsPayload(response) || {};
      if (payload) {
        setResults(payload);
        setIsDefault(true);
        setSearched(true);
        setDefaultRefreshedAt(response.data?.refreshed_at || null);
      }
    } catch {
      setResults(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (initialQuery) {
      runSearch(initialQuery, initialPage);
      return;
    }

    const last = loadLastSearchCache('litigants');
    if (last?.query) {
      setForm({ query: last.query });
      setPage(last.page || 1);
      setResults(last.results || null);
      setSearched(true);
      setSearchParams({ q: last.query, page: String(last.page || 1) }, { replace: true });
      return;
    }

    fetchDefaults();
  }, [fetchDefaults, initialPage, initialQuery, runSearch, setSearchParams]);

  async function handleSearch(e) {
    e?.preventDefault();
    const trimmedQuery = form.query.trim();
    if (!trimmedQuery) {
      setError('Please enter a party / litigant name.');
      return;
    }

    setSearched(true);
    setPage(1);
    setSearchParams({ q: trimmedQuery, page: '1' });
    await runSearch(trimmedQuery, 1);
  }

  async function handlePageChange(nextPage) {
    setPage(nextPage);
    setSearchParams({ q: form.query.trim(), page: String(nextPage) });
    await runSearch(form.query, nextPage);
  }

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6">
        <h2 className="text-2xl font-black text-ink tracking-tight">Litigant Search</h2>
        <p className="text-sm text-slate-500 mt-0.5">Search cases by party or litigant name</p>
        <button type="button" onClick={() => navigate('/ecourts')} className="mt-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-400 transition-colors hover:text-primary">
          Back to eCourts Home
        </button>
      </div>

      <div className="card p-6 mb-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold mb-1 text-slate-700">
              Party / Litigant Name *
            </label>
            <input
              name="query"
              value={form.query}
              onChange={handleChange}
              className="input-base"
              placeholder="e.g., Suresh Kumar or ABC Pvt. Ltd."
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              <span className="material-symbols-outlined text-base">error</span>
              {error}
            </div>
          )}

          <button type="submit" disabled={loading || !form.query.trim()} className="btn-primary flex items-center gap-2">
            {loading ? (
              <><span className="material-symbols-outlined animate-spin text-base">progress_activity</span> Searching…</>
            ) : (
              <><span className="material-symbols-outlined text-base">groups</span> Search Litigants</>
            )}
          </button>
        </form>
      </div>

      {/* Results */}
      {isDefault && results ? (
        <div className="mb-4 rounded-xl border border-primary/15 bg-primary/5 px-4 py-3 text-sm text-primary">
          Showing cached backend litigant matches{defaultRefreshedAt ? ` · updated ${new Date(defaultRefreshedAt).toLocaleDateString('en-IN')}` : ''}.
        </div>
      ) : null}

      {(searched || isDefault) && !loading && (
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-3">
            {caseList.length > 0
              ? `${totalHits || caseList.length} result${(totalHits || caseList.length) > 1 ? 's' : ''}`
              : 'No results found'}
          </p>
          <div className="space-y-3">
            {caseList.map((c, index) => (
              <Link
                key={c.cnr || c.cnr_number || c.id || index}
                to={`/ecourts/case/${encodeURIComponent(c.cnr || c.cnr_number || c.id || '')}`}
                className="card p-5 hover:border-primary/30 hover:shadow-md transition-all flex items-center justify-between group"
              >
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                      c.status === 'Disposed' || c.case_status === 'Disposed'
                        ? 'bg-slate-100 text-slate-500'
                        : 'bg-emerald-100 text-emerald-600'
                    }`}>
                      {c.status || c.case_status || 'Active'}
                    </span>
                    <span className="text-xs font-mono text-slate-400">{c.cnr || c.cnr_number || '—'}</span>
                  </div>
                  <p className="font-semibold text-ink">{c.case_title || c.title || 'Litigant-linked case'}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {[c.case_type, c.case_number && c.year ? `${c.case_number}/${c.year}` : c.case_number, c.court || c.court_name].filter(Boolean).join(' — ') || 'Court data unavailable'}
                  </p>
                  {c.petitioner || c.respondent ? (
                    <p className="text-xs text-slate-500 mt-1">
                      {[c.petitioner, c.respondent].filter(Boolean).join(' vs ')}
                    </p>
                  ) : null}
                </div>
                <span className="material-symbols-outlined text-slate-300 group-hover:text-primary transition-colors">
                  chevron_right
                </span>
              </Link>
            ))}
          </div>
          {!isDefault && totalPages > 1 ? (
            <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
              <button
                type="button"
                onClick={() => handlePageChange(page - 1)}
                disabled={page <= 1 || loading}
                className="rounded-full border border-primary/10 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-primary/5 hover:text-primary disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-sm font-semibold text-slate-500">Page {page} of {totalPages}</span>
              <button
                type="button"
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= totalPages || loading}
                className="rounded-full border border-primary/10 px-4 py-2 text-sm font-semibold text-slate-600 transition-colors hover:bg-primary/5 hover:text-primary disabled:opacity-40"
              >
                Next
              </button>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
