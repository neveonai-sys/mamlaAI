import React, { useEffect, useState } from 'react';
import { searchCaseLaw, searchCaseLawPage, resolveCaseSearchPdf, unwrapCitationPayload } from './citationsApi';
import { loadSearchCache, saveSearchCache } from '../ecourts/common/useSearchCache';

const EMPTY_FILTERS = {
  keyword: '',
  search_opt: 'ANY',
  pet_res: '',
  pet_res1: '',
  from_date: '',
  to_date: '',
  judge_name: '',
  act: '',
  section_txt: '',
  case_no: '',
  case_year: '',
  citation_yr: '',
  citation_vol: '',
  citation_supl: '',
  citation_page: '',
  neu_cit_year: '',
  neu_no: '',
};

const PAGE_SIZE = 10;

export default function CaseLawSearch() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [results, setResults] = useState([]);
  const [page, setPage] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);
  const [resolvingKey, setResolvingKey] = useState(null);

  const totalPages = Math.max(Math.ceil(totalRecords / PAGE_SIZE), 0);

  async function handleOpenPdf(result, key) {
    if (!result.pdf_ref_path || !result.pdf_ref_year || result.pdf_ref_val === null || result.pdf_ref_val === undefined) return;
    if (!sessionId) {
      setError('Search session expired — please re-run the search to open judgments.');
      return;
    }
    setResolvingKey(key);
    setError('');
    try {
      const response = await resolveCaseSearchPdf(sessionId, {
        path: result.pdf_ref_path,
        year: result.pdf_ref_year,
        val: result.pdf_ref_val,
        ncDisplay: result.nc_display,
      });
      const payload = unwrapCitationPayload(response) || {};
      if (payload.pdf_url) {
        window.open(payload.pdf_url, '_blank', 'noopener,noreferrer');
      } else {
        setError('PDF link unavailable for this judgment.');
      }
    } catch (err) {
      if (err.response?.status === 410) {
        setError('Search session expired — please re-run the search to open judgments.');
        setSessionId(null);
      } else {
        setError(err.response?.data?.error || 'Failed to resolve the PDF link. Please try again.');
      }
    } finally {
      setResolvingKey(null);
    }
  }

  function handleFilterChange(e) {
    const { name, value } = e.target;
    setFilters((f) => ({ ...f, [name]: value }));
  }

  useEffect(() => {
    // sessionId belongs to one applied filter set; discard it if the user
    // edits filters before re-running the search, so a stale session is
    // never reused for a different query.
    setSessionId(null);
  }, [filters]);

  async function runSearch(activeFilters, nextPage) {
    const cached = loadSearchCache('case_search', JSON.stringify(activeFilters), nextPage, {});
    if (cached) {
      setResults(cached.results || []);
      setTotalRecords(cached.total_records || 0);
      setSessionId(cached.session_id || null);
      setError('');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const response = await searchCaseLaw(activeFilters, nextPage, PAGE_SIZE);
      const payload = unwrapCitationPayload(response) || {};
      setResults(payload.results || []);
      setTotalRecords(payload.total_records || 0);
      setSessionId(payload.session_id || null);
      saveSearchCache('case_search', JSON.stringify(activeFilters), nextPage, {}, payload);
    } catch (err) {
      setError(err.response?.data?.error || 'Case search failed. Please try again.');
      setResults([]);
      setTotalRecords(0);
      setSessionId(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch(e) {
    e?.preventDefault();
    setSearched(true);
    setPage(1);
    setAppliedFilters(filters);
    await runSearch(filters, 1);
  }

  async function handlePageChange(nextPage) {
    if (!appliedFilters || nextPage < 1 || (totalPages && nextPage > totalPages)) return;
    setPage(nextPage);

    const cached = loadSearchCache('case_search', JSON.stringify(appliedFilters), nextPage, {});
    if (cached) {
      setResults(cached.results || []);
      setTotalRecords(cached.total_records || 0);
      setSessionId(cached.session_id || null);
      return;
    }

    if (!sessionId) {
      // Session expired or never opened (e.g. deep link) — fall back to a
      // fresh search at the requested page.
      await runSearch(appliedFilters, nextPage);
      return;
    }

    setLoading(true);
    setError('');
    try {
      const response = await searchCaseLawPage(sessionId, nextPage, PAGE_SIZE);
      const payload = unwrapCitationPayload(response) || {};
      setResults(payload.results || []);
      setTotalRecords(payload.total_records || 0);
      saveSearchCache('case_search', JSON.stringify(appliedFilters), nextPage, {}, payload);
    } catch (err) {
      if (err.response?.status === 410) {
        // Session expired server-side — retry as a fresh search.
        await runSearch(appliedFilters, nextPage);
        return;
      }
      setError(err.response?.data?.error || 'Case search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="card p-6 mb-6">
        <form onSubmit={handleSearch} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold mb-1 text-slate-700">Keyword</label>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                name="keyword"
                value={filters.keyword}
                onChange={handleFilterChange}
                className="input-base flex-1"
                placeholder="e.g., land dispute"
              />
              <select name="search_opt" value={filters.search_opt} onChange={handleFilterChange} className="input-base sm:w-40">
                <option value="ANY">Any Words</option>
                <option value="ALL">All Words</option>
                <option value="PHRASE">Exact Phrase</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold mb-1 text-slate-700">Petitioner</label>
              <input name="pet_res" value={filters.pet_res} onChange={handleFilterChange} className="input-base" placeholder="Petitioner name" />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1 text-slate-700">Respondent</label>
              <input name="pet_res1" value={filters.pet_res1} onChange={handleFilterChange} className="input-base" placeholder="Respondent name" />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1 text-slate-700">Judge Name</label>
              <input name="judge_name" value={filters.judge_name} onChange={handleFilterChange} className="input-base" placeholder="e.g., D.Y. Chandrachud" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-semibold mb-1 text-slate-700">From Date</label>
                <input type="date" name="from_date" value={filters.from_date} onChange={handleFilterChange} className="input-base" />
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1 text-slate-700">To Date</label>
                <input type="date" name="to_date" value={filters.to_date} onChange={handleFilterChange} className="input-base" />
              </div>
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1 text-slate-700">Act</label>
              <input name="act" value={filters.act} onChange={handleFilterChange} className="input-base" placeholder="e.g., Indian Penal Code" />
            </div>
            <div>
              <label className="block text-xs font-semibold mb-1 text-slate-700">Section</label>
              <input name="section_txt" value={filters.section_txt} onChange={handleFilterChange} className="input-base" placeholder="e.g., 302" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs font-semibold mb-1 text-slate-700">Case No.</label>
                <input name="case_no" value={filters.case_no} onChange={handleFilterChange} className="input-base" />
              </div>
              <div>
                <label className="block text-xs font-semibold mb-1 text-slate-700">Case Year</label>
                <input name="case_year" value={filters.case_year} onChange={handleFilterChange} className="input-base" placeholder="e.g., 2024" />
              </div>
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold mb-1 text-slate-700">SCR Citation</p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <input name="citation_yr" value={filters.citation_yr} onChange={handleFilterChange} className="input-base" placeholder="Year" />
              <input name="citation_vol" value={filters.citation_vol} onChange={handleFilterChange} className="input-base" placeholder="Vol" />
              <input name="citation_supl" value={filters.citation_supl} onChange={handleFilterChange} className="input-base" placeholder="OR Supl" />
              <input name="citation_page" value={filters.citation_page} onChange={handleFilterChange} className="input-base" placeholder="Page" />
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold mb-1 text-slate-700">Neutral Citation</p>
            <div className="grid grid-cols-2 gap-2 max-w-xs">
              <input name="neu_cit_year" value={filters.neu_cit_year} onChange={handleFilterChange} className="input-base" placeholder="Year" />
              <input name="neu_no" value={filters.neu_no} onChange={handleFilterChange} className="input-base" placeholder="INSC Number" />
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              <span className="material-symbols-outlined text-base">error</span>
              {error}
            </div>
          )}

          <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2">
            {loading ? (
              <><span className="material-symbols-outlined animate-spin text-base">progress_activity</span> Searching e-SCR…</>
            ) : (
              <><span className="material-symbols-outlined text-base">search</span> Search Case Law</>
            )}
          </button>
          {loading && (
            <p className="text-[11px] text-slate-400">
              A new search solves a live captcha against the Supreme Court's portal and can take up to a minute; paging through results afterward is fast.
            </p>
          )}
        </form>
      </div>

      {searched && !loading && (
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-3">
            {totalRecords > 0 ? `${totalRecords.toLocaleString('en-IN')} results` : 'No results'}
          </p>
          <div className="space-y-3">
            {results.map((r, index) => {
              const key = r.cnr || `${r.nc_display}-${index}`;
              const canOpen = Boolean(r.pdf_ref_path && r.pdf_ref_year && r.pdf_ref_val !== null && r.pdf_ref_val !== undefined);
              const resolving = resolvingKey === key;
              return (
                <div
                  key={key}
                  role={canOpen ? 'button' : undefined}
                  tabIndex={canOpen ? 0 : undefined}
                  onClick={canOpen ? () => handleOpenPdf(r, key) : undefined}
                  className={`card p-5 ${canOpen ? 'cursor-pointer hover:border-primary/30 hover:shadow-md transition-all' : ''}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="font-semibold text-ink">{r.case_title || 'Case'}</p>
                    {canOpen ? (
                      <span className="shrink-0 inline-flex items-center gap-1 text-xs font-semibold text-primary">
                        {resolving ? (
                          <><span className="material-symbols-outlined animate-spin text-base">progress_activity</span> Opening…</>
                        ) : (
                          <><span className="material-symbols-outlined text-base">picture_as_pdf</span> View PDF</>
                        )}
                      </span>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-600 mt-1">
                    {r.nc_display ? (
                      <span><span className="text-slate-400">Neutral Citation:</span> {r.nc_display}</span>
                    ) : null}
                    {r.scr_citation ? (
                      <span><span className="text-slate-400">SCR:</span> {r.scr_citation}</span>
                    ) : null}
                    {r.cnr ? (
                      <span className="font-mono"><span className="text-slate-400 font-sans">CNR:</span> {r.cnr}</span>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
          {totalPages > 1 ? (
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
