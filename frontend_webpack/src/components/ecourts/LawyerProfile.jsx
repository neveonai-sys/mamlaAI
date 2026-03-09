import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Typography, Paper, Grid, Chip, Stack, Pagination,
  CircularProgress, Alert, Breadcrumbs, Link, Divider,
} from '@mui/material';
import CaseCard from './common/CaseCard';
import FacetSidebar from './common/FacetSidebar';
import { searchCases } from './ecourtsApi';

export default function LawyerProfile() {
  const { name } = useParams();
  const navigate = useNavigate();
  const decodedName = decodeURIComponent(name || '');

  const [page, setPage] = useState(1);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeFilters, setActiveFilters] = useState({});

  const doSearch = useCallback(async (p, filters) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await searchCases({
        searchType: 'advocate',
        query: decodedName,
        page: p,
        pageSize: 20,
        ...(filters.caseStatuses ? { caseStatuses: [filters.caseStatuses] } : {}),
        ...(filters.caseType ? { caseTypes: [filters.caseType] } : {}),
      });
      setResults(resp.data?.data || null);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  }, [decodedName]);

  useEffect(() => { doSearch(1, {}); }, [doSearch]);

  const handlePageChange = (_, newPage) => {
    setPage(newPage);
    doSearch(newPage, activeFilters);
  };

  const handleFilterChange = (key, value) => {
    const next = { ...activeFilters };
    if (value === null) delete next[key];
    else next[key] = value;
    setActiveFilters(next);
    setPage(1);
    doSearch(1, next);
  };

  const caseList = results?.case_list || [];
  const totalPages = results?.total_pages || 0;
  const totalHits = results?.total || 0;
  const facets = results?.facets || {};

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', px: { xs: 2, md: 3 }, py: 3 }}>
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link underline="hover" color="inherit" onClick={() => navigate('/ecourts')} sx={{ cursor: 'pointer' }}>Home</Link>
        <Link underline="hover" color="inherit" onClick={() => navigate('/ecourts/lawyers')} sx={{ cursor: 'pointer' }}>Lawyers</Link>
        <Typography color="text.primary">{decodedName}</Typography>
      </Breadcrumbs>

      <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
        Advocate {decodedName}
      </Typography>
      {totalHits > 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          {totalHits.toLocaleString()} cases found
        </Typography>
      )}

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <FacetSidebar facets={facets} activeFilters={activeFilters} onFilterChange={handleFilterChange} totalHits={totalHits} />

          <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2.5, mt: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
              Are you {decodedName}?
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Verify your profile to manage your information.
            </Typography>
          </Paper>
        </Grid>

        <Grid item xs={12} md={9}>
          <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
            Cases represented by {decodedName}
          </Typography>

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}><CircularProgress /></Box>
          ) : caseList.length === 0 ? (
            <Typography color="text.secondary">No cases found.</Typography>
          ) : (
            <>
              {caseList.map((c, idx) => <CaseCard key={c.cnr || idx} caseData={c} />)}
              {totalPages > 1 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                  <Pagination count={totalPages} page={page} onChange={handlePageChange} color="primary" />
                </Box>
              )}
            </>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}
