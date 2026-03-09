import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Box, Typography, TextField, InputAdornment, IconButton, Paper,
  Grid, Pagination, CircularProgress, Alert, Breadcrumbs, Link, Chip,
} from '@mui/material';
import { Search as SearchIcon, InfoOutlined } from '@mui/icons-material';
import CaseCard from './common/CaseCard';
import FacetSidebar from './common/FacetSidebar';
import RecentSearches from './common/RecentSearches';
import useRecentSearches from './common/useRecentSearches';
import { searchCases, getEcourtsDefaults } from './ecourtsApi';
import { saveSearchCache, loadSearchCache, loadLastSearchCache } from './common/useSearchCache';

export default function CaseSearch() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const initialQuery = searchParams.get('q') || '';
  const initialType = searchParams.get('type') || 'general';
  const initialPage = parseInt(searchParams.get('page') || '1', 10);

  const [query, setQuery] = useState(initialQuery);
  const [searchType] = useState(initialType);
  const [page, setPage] = useState(initialPage);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeFilters, setActiveFilters] = useState({});
  const { recent, addSearch, clearSection } = useRecentSearches('cases');
  const [isDefault, setIsDefault] = useState(false);
  const [defaultRefreshedAt, setDefaultRefreshedAt] = useState(null);

  const doSearch = useCallback(async (q, p, filters) => {
    if (!q || q.trim().length < 2) return;
    // Instant restore from session cache — no API call on back-navigation
    const cached = loadSearchCache('cases', q, p, filters);
    if (cached) { setResults(cached); return; }
    setLoading(true);
    setError(null);
    try {
      const resp = await searchCases({
        searchType,
        query: q,
        page: p,
        pageSize: 20,
        ...(filters.caseStatuses ? { caseStatuses: [filters.caseStatuses] } : {}),
        ...(filters.caseType ? { caseTypes: [filters.caseType] } : {}),
      });
      const data = resp.data?.data || null;
      setResults(data);
      saveSearchCache('cases', q, p, filters, data);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  }, [searchType]);

  const fetchDefaults = useCallback(async () => {
    try {
      const resp = await getEcourtsDefaults('cases');
      if (resp.data?.status === 'success') {
        setResults(resp.data.data);
        setIsDefault(true);
        setDefaultRefreshedAt(resp.data.refreshed_at || null);
      }
    } catch {
      // Silently ignore — blank page is acceptable if defaults unavailable
    }
  }, []);

  useEffect(() => {
    if (initialQuery) {
      doSearch(initialQuery, initialPage, activeFilters);
    } else {
      const last = loadLastSearchCache('cases');
      if (last) {
        setQuery(last.query);
        setPage(last.page);
        setResults(last.results);
        setSearchParams({ q: last.query, type: searchType, page: String(last.page) }, { replace: true });
      } else {
        fetchDefaults();
      }
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = (q = query) => {
    if (!q.trim()) return;
    setIsDefault(false);
    setQuery(q);
    setPage(1);
    setSearchParams({ q, type: searchType, page: '1' });
    addSearch(q);
    doSearch(q, 1, activeFilters);
  };

  const handlePageChange = (_, newPage) => {
    setPage(newPage);
    setSearchParams({ q: query, type: searchType, page: String(newPage) });
    doSearch(query, newPage, activeFilters);
  };

  const handleFilterChange = (key, value) => {
    const next = { ...activeFilters };
    if (value === null) {
      delete next[key];
    } else {
      next[key] = value;
    }
    setActiveFilters(next);
    setPage(1);
    doSearch(query, 1, next);
  };

  const caseList = results?.case_list || [];
  const totalPages = results?.total_pages || 0;
  const totalHits = results?.total || 0;
  const facets = results?.facets || {};

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', px: { xs: 2, md: 3 }, py: 3 }}>
      {/* Breadcrumb */}
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link underline="hover" color="inherit" onClick={() => navigate('/ecourts')} sx={{ cursor: 'pointer' }}>
          Home
        </Link>
        <Typography color="text.primary">Cases</Typography>
      </Breadcrumbs>

      {/* Search bar */}
      <Paper
        elevation={0}
        sx={{ display: 'flex', alignItems: 'center', borderRadius: 2, border: '1px solid', borderColor: 'divider', mb: 3, overflow: 'hidden' }}
      >
        <TextField
          fullWidth
          placeholder="Search cases, orders, judgments, CNR numbers..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          variant="outlined"
          size="small"
          sx={{ '& .MuiOutlinedInput-root': { '& fieldset': { border: 'none' } } }}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton onClick={handleSearch} sx={{ bgcolor: 'primary.main', color: 'white', borderRadius: 1, '&:hover': { bgcolor: 'primary.dark' } }}>
                  <SearchIcon />
                </IconButton>
              </InputAdornment>
            ),
          }}
        />
      </Paper>

      <RecentSearches recent={recent} onSelect={(q) => handleSearch(q)} onClear={clearSection} />

      {isDefault && (
        <Chip
          icon={<InfoOutlined sx={{ fontSize: 16 }} />}
          label={`Today's latest cases${defaultRefreshedAt ? ` · Updated ${new Date(defaultRefreshedAt).toLocaleDateString('en-IN')}` : ''} · Search above to explore`}
          size="small"
          variant="outlined"
          color="primary"
          sx={{ mb: 2 }}
        />
      )}

      {!isDefault && totalHits > 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {totalHits.toLocaleString()} results found
        </Typography>
      )}

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Grid container spacing={3}>
        {/* Facet sidebar */}
        <Grid item xs={12} md={3}>
          <FacetSidebar
            facets={facets}
            activeFilters={activeFilters}
            onFilterChange={handleFilterChange}
            totalHits={totalHits}
          />
        </Grid>

        {/* Results */}
        <Grid item xs={12} md={9}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
              <CircularProgress />
            </Box>
          ) : caseList.length === 0 && !isDefault && initialQuery ? (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <Typography variant="h6" color="text.secondary">No results found</Typography>
              <Typography variant="body2" color="text.secondary">
                Try a different search term or adjust your filters.
              </Typography>
            </Box>
          ) : (
            <>
              {caseList.map((c, idx) => (
                <CaseCard key={c.cnr || idx} caseData={c} />
              ))}
              {!isDefault && totalPages > 1 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                  <Pagination
                    count={totalPages}
                    page={page}
                    onChange={handlePageChange}
                    color="primary"
                  />
                </Box>
              )}
            </>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}
