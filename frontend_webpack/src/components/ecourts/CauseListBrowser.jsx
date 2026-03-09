import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box, Typography, TextField, InputAdornment, IconButton, Paper, Tabs, Tab,
  Grid, Breadcrumbs, Link, CircularProgress, Alert, Stack, Chip, Divider,
} from '@mui/material';
import { Search as SearchIcon } from '@mui/icons-material';
import CourtSelector from './common/CourtSelector';
import RecentSearches from './common/RecentSearches';
import useRecentSearches from './common/useRecentSearches';
import {
  getStates, getDistricts, getComplexes, getCauseList, getCauseListDates,
} from './ecourtsApi';

const SEARCH_TABS = [
  { key: 'all', label: 'All' },
  { key: 'advocate', label: 'Lawyer' },
  { key: 'litigant', label: 'Litigant' },
  { key: 'judge', label: 'Judge' },
];

export default function CauseListBrowser() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialQ = searchParams.get('q') || '';

  const [searchTab, setSearchTab] = useState(0);
  const [query, setQuery] = useState(initialQ);
  const { recent, addSearch, clearSection } = useRecentSearches('causelist');

  // Navigation state
  const [level, setLevel] = useState('states'); // states | districts | complexes | results
  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [complexes, setComplexes] = useState([]);

  const [selectedState, setSelectedState] = useState(null);
  const [selectedDistrict, setSelectedDistrict] = useState(null);
  const [selectedComplex, setSelectedComplex] = useState(null);

  const [causeListResults, setCauseListResults] = useState(null);
  const [availableDates, setAvailableDates] = useState([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load states on mount
  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const resp = await getStates();
        const data = resp.data?.data || [];
        setStates(data.map((s) => ({ code: s.state_code, name: s.name })));
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleSelectState = useCallback(async (item) => {
    setSelectedState(item);
    setLevel('districts');
    setLoading(true);
    setError(null);
    try {
      const resp = await getDistricts(item.code);
      const data = resp.data?.data || [];
      setDistricts(data.map((d) => ({ code: d.district_code, name: d.name })));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSelectDistrict = useCallback(async (item) => {
    setSelectedDistrict(item);
    setLevel('complexes');
    setLoading(true);
    setError(null);
    try {
      const resp = await getComplexes(selectedState.code, item.code);
      const data = resp.data?.data || [];
      setComplexes(data.map((c) => ({ code: c.complex_code, name: c.name })));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedState]);

  const handleSelectComplex = useCallback(async (item) => {
    setSelectedComplex(item);
    setLevel('results');
    setLoading(true);
    setError(null);
    try {
      const datesResp = await getCauseListDates({
        state: selectedState.code,
        districtCode: selectedDistrict.code,
        courtComplexCode: item.code,
      });
      setAvailableDates(datesResp.data?.dates || []);
    } catch {
      // dates may fail if no data
    } finally {
      setLoading(false);
    }
  }, [selectedState, selectedDistrict]);

  const handleSearch = useCallback(async (q = query) => {
    if (!q.trim()) return;
    setQuery(q);
    addSearch(q);
    setLevel('results');
    setLoading(true);
    setError(null);
    setCauseListResults(null);
    try {
      const tabKey = SEARCH_TABS[searchTab].key;
      const params = {};

      if (tabKey === 'advocate') params.advocate = q;
      else if (tabKey === 'litigant') params.litigant = q;
      else if (tabKey === 'judge') params.judge = q;
      else params.q = q;

      if (selectedState) params.state = selectedState.code;
      if (selectedDistrict) params.districtCode = selectedDistrict.code;
      if (selectedComplex) params.courtComplexCode = selectedComplex.code;

      params.limit = 50;

      const resp = await getCauseList(params);
      setCauseListResults(resp.data?.data || null);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  }, [query, searchTab, selectedState, selectedDistrict, selectedComplex, addSearch]);

  const handleSearchByDate = useCallback(async (date) => {
    setLoading(true);
    setError(null);
    try {
      const params = { date, limit: 100 };
      if (selectedState) params.state = selectedState.code;
      if (selectedDistrict) params.districtCode = selectedDistrict.code;
      if (selectedComplex) params.courtComplexCode = selectedComplex.code;

      const resp = await getCauseList(params);
      setCauseListResults(resp.data?.data || null);
    } catch (err) {
      setError(err.response?.data?.error || err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedState, selectedDistrict, selectedComplex]);

  const resetTo = (targetLevel) => {
    if (targetLevel === 'states') {
      setSelectedState(null);
      setSelectedDistrict(null);
      setSelectedComplex(null);
      setDistricts([]);
      setComplexes([]);
      setCauseListResults(null);
    } else if (targetLevel === 'districts') {
      setSelectedDistrict(null);
      setSelectedComplex(null);
      setComplexes([]);
      setCauseListResults(null);
    } else if (targetLevel === 'complexes') {
      setSelectedComplex(null);
      setCauseListResults(null);
    }
    setLevel(targetLevel);
  };

  const entries = causeListResults?.entries || [];

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', px: { xs: 2, md: 3 }, py: 3 }}>
      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link underline="hover" color="inherit" onClick={() => navigate('/ecourts')} sx={{ cursor: 'pointer' }}>
          Home
        </Link>
        <Link underline="hover" color="inherit" onClick={() => resetTo('states')} sx={{ cursor: 'pointer' }}>
          Cause List
        </Link>
        {selectedState && (
          <Link underline="hover" color="inherit" onClick={() => resetTo('districts')} sx={{ cursor: 'pointer' }}>
            {selectedState.name}
          </Link>
        )}
        {selectedDistrict && (
          <Link underline="hover" color="inherit" onClick={() => resetTo('complexes')} sx={{ cursor: 'pointer' }}>
            {selectedDistrict.name}
          </Link>
        )}
        {selectedComplex && (
          <Typography color="text.primary">{selectedComplex.name}</Typography>
        )}
      </Breadcrumbs>

      {/* Title */}
      <Typography variant="h5" sx={{ fontWeight: 700, mb: 1 }}>
        {level === 'states' && 'Court Cause Lists Across India'}
        {level === 'districts' && `Districts in ${selectedState?.name}`}
        {level === 'complexes' && `Court Complexes in ${selectedDistrict?.name}`}
        {level === 'results' && (selectedComplex?.name || 'Cause List Results')}
      </Typography>
      {level === 'states' && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Select your state, district, and court complex to view the cause list. Or search directly below.
        </Typography>
      )}

      {/* Search tabs + bar */}
      <Box sx={{ mb: 3 }}>
        <Tabs value={searchTab} onChange={(_, v) => setSearchTab(v)}
          sx={{ mb: 1, '& .MuiTab-root': { textTransform: 'none', fontWeight: 500, minWidth: 80 } }}
        >
          {SEARCH_TABS.map((t) => <Tab key={t.key} label={t.label} />)}
        </Tabs>

        <Paper
          elevation={0}
          sx={{ display: 'flex', alignItems: 'center', borderRadius: 2, border: '1px solid', borderColor: 'divider', overflow: 'hidden' }}
        >
          <TextField
            fullWidth
            placeholder={`Search your Tarik...`}
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
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Navigation levels */}
      {level === 'states' && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={9}>
            <CourtSelector items={states} loading={loading} onSelect={handleSelectState} label="states" />
          </Grid>
          <Grid item xs={12} md={3}>
            <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>States Available</Typography>
              <Typography variant="h5" sx={{ fontWeight: 700, color: 'primary.main' }}>
                {states.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Select a state to view districts and courts
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      )}

      {level === 'districts' && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={9}>
            <CourtSelector items={districts} loading={loading} onSelect={handleSelectDistrict} label="districts" />
          </Grid>
          <Grid item xs={12} md={3}>
            <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>Districts</Typography>
              <Typography variant="body2" color="text.secondary">State: {selectedState?.name}</Typography>
              <Typography variant="h5" sx={{ fontWeight: 700, color: 'primary.main', mt: 1 }}>
                {districts.length}
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      )}

      {level === 'complexes' && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={9}>
            <CourtSelector items={complexes} loading={loading} onSelect={handleSelectComplex} label="court complexes" />
          </Grid>
          <Grid item xs={12} md={3}>
            <Paper elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>Court Complexes</Typography>
              <Typography variant="body2" color="text.secondary">
                {selectedState?.name} &gt; {selectedDistrict?.name}
              </Typography>
              <Typography variant="h5" sx={{ fontWeight: 700, color: 'primary.main', mt: 1 }}>
                {complexes.length}
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      )}

      {level === 'results' && (
        <Box>
          {/* Available dates */}
          {availableDates.length > 0 && !causeListResults && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                Available Dates
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {availableDates.slice(0, 14).map((d) => (
                  <Chip
                    key={d}
                    label={d}
                    onClick={() => handleSearchByDate(d)}
                    color="primary"
                    variant="outlined"
                    sx={{ cursor: 'pointer' }}
                  />
                ))}
              </Stack>
            </Box>
          )}

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}><CircularProgress /></Box>
          ) : entries.length > 0 ? (
            <Box>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {causeListResults?.returned_count || entries.length} entries found
              </Typography>
              <Stack spacing={1.5}>
                {entries.map((entry, i) => (
                  <Paper key={entry.id || i} elevation={0} sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, p: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                          {entry.party || (entry.case_number || []).join(', ')}
                        </Typography>
                        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 0.5, mb: 0.5 }}>
                          {entry.list_type && <Chip label={entry.list_type} size="small" variant="outlined" />}
                          {entry.status && <Chip label={entry.status} size="small" color="info" variant="outlined" />}
                          {entry.court_type && <Chip label={entry.court_type.replace('_', ' ')} size="small" variant="outlined" />}
                        </Stack>
                        {entry.advocates?.length > 0 && (
                          <Typography variant="body2" color="text.secondary">
                            <strong>Advocate:</strong> {entry.advocates.join(', ')}
                          </Typography>
                        )}
                        {entry.judge?.length > 0 && (
                          <Typography variant="body2" color="text.secondary">
                            <strong>Judge:</strong> {entry.judge.join(', ')}
                          </Typography>
                        )}
                        {entry.court_name && (
                          <Typography variant="body2" color="text.secondary">
                            <strong>Court:</strong> {entry.court_name}
                          </Typography>
                        )}
                      </Box>
                      <Box sx={{ textAlign: 'right', ml: 2, flexShrink: 0 }}>
                        {entry.date && (
                          <Typography variant="caption" color="primary" sx={{ fontWeight: 600 }}>
                            {entry.date}
                          </Typography>
                        )}
                        {entry.court_no && (
                          <Typography variant="caption" color="text.secondary" display="block">
                            Court No: {entry.court_no}
                          </Typography>
                        )}
                      </Box>
                    </Box>
                  </Paper>
                ))}
              </Stack>
            </Box>
          ) : !loading && causeListResults ? (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <Typography variant="h6" color="text.secondary">No cause list entries found</Typography>
              <Typography variant="body2" color="text.secondary">
                Try selecting a different date or adjusting your search.
              </Typography>
            </Box>
          ) : !loading && (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <Typography variant="h6" color="text.secondary">Search Your Cause Lists</Typography>
              <Typography variant="body2" color="text.secondary">
                Enter your name or select a date to find cause lists for your cases.
              </Typography>
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
}
